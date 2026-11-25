"""Research-only, unforced phoneme recognition on bounded PCM excerpts."""
import json
import shutil
import subprocess
import wave
from pathlib import Path

from .alignment_benchmark import parse_htk, TICKS_PER_SECOND
from .native_recognition import _sha, _write
from .multilingual_fidelity import distance

MODEL = "onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX"
REVISION = "c69750f5043e5e1f8a71ab95dd3b98338c280c92"
WEIGHTS_SHA = "3d1479b5c70836645a4310902479f7f7e8bbc8c16c58745d918804f4f6f9d120"
VOCAB_SIZE = 392


def vocabulary(path):
    if path.stat().st_size > 64000:
        raise ValueError("Oversized vocabulary")
    vocab = json.loads(path.read_text(encoding="utf-8-sig"))
    if (not isinstance(vocab, dict) or len(vocab) != VOCAB_SIZE
            or any(not k or any(c.isspace() for c in k) or type(v) is not int
                   for k, v in vocab.items())
            or set(vocab.values()) != set(range(VOCAB_SIZE))
            or any(vocab.get(k) != v for k, v in
                   {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3}.items())):
        raise ValueError("Unexpected 392-class phoneme vocabulary")
    return {v: k for k, v in vocab.items()}


def collapse_ctc(ids, tokens):
    """Collapse repetitions before removing blanks; preserve unknown/special tokens."""
    rows = []
    previous = None
    for i, token_id in enumerate(ids):
        if type(token_id) is not int or token_id not in tokens:
            raise ValueError("Invalid CTC class index")
        if token_id != previous and token_id != 0:
            rows.append({"token": tokens[token_id], "class_id": token_id,
                         "first_frame": i, "end_frame_exclusive": i+1})
        elif token_id == previous and token_id != 0:
            rows[-1]["end_frame_exclusive"] = i+1
        previous = token_id
    return rows


def pcm_duration(path):
    with wave.open(str(path), "rb") as f:
        rate, frames = f.getframerate(), f.getnframes()
        if (f.getcomptype() != "NONE" or not 8000 <= rate <= 96000
                or f.getnchannels() not in (1, 2) or f.getsampwidth() not in (2, 3)
                or not rate <= frames <= rate*30):
            raise ValueError("Expected 1–30 s mono/stereo 16/24-bit PCM WAV")
        if len(f.readframes(frames)) != frames*f.getnchannels()*f.getsampwidth():
            raise ValueError("Truncated PCM WAV")
        return frames/rate


def infer(audio, weights, seconds):
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        raise ValueError(f"Optional CPU ONNX runtime missing: {exc}") from exc
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValueError("ffmpeg required")
    result = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-f", "wav",
        "-protocol_whitelist", "file", "-i", str(audio), "-map", "0:a:0",
        "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"],
        capture_output=True, timeout=30, check=True)
    pcm = np.frombuffer(result.stdout, dtype="<f4")
    if (abs(len(pcm)-round(seconds*16000)) > 2 or not np.isfinite(pcm).all()
            or pcm.std() < 1e-6):
        raise ValueError("Unexpected decoded duration, nonfinite or silent input")
    values = ((pcm-pcm.mean())/np.sqrt(pcm.var()+1e-7)).astype(np.float32)[None,:]
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(weights), sess_options=options,
                                   providers=["CPUExecutionProvider"])
    inputs = {i.name: i.type for i in session.get_inputs()}
    if inputs not in ({"input_values":"tensor(float)"},
                      {"input_values":"tensor(float)", "attention_mask":"tensor(int64)"}):
        raise ValueError("Unexpected ONNX input contract")
    if [o.name for o in session.get_outputs()] != ["logits"]:
        raise ValueError("Unexpected ONNX output contract")
    feed = {"input_values": values}
    if "attention_mask" in inputs:
        feed["attention_mask"] = np.ones(values.shape, dtype=np.int64)
    logits = session.run(["logits"], feed)[0]
    expected_frames = (len(pcm)-400)//320+1
    if logits.shape != (1, expected_frames, VOCAB_SIZE) or not np.isfinite(logits).all():
        raise ValueError("Unexpected CTC output shape or nonfinite scores")
    return logits[0].argmax(axis=-1).tolist(), ort.__version__


def observe(audio, weights, vocab, out, *, reference=None, confirm=False):
    if not confirm:
        raise ValueError("Explicit confirmation required for local CPU inference")
    audio, weights, vocab = [Path(p).resolve(strict=True) for p in (audio, weights, vocab)]
    out = Path(out).resolve()
    inputs = [audio, weights, vocab]
    if reference is not None:
        reference = Path(reference).resolve(strict=True)
        inputs.append(reference)
    if len(set(inputs)) != len(inputs) or out.exists() or audio.suffix.lower() != ".wav":
        raise ValueError("Distinct inputs, PCM WAV and fresh output required")
    hashes = [_sha(p) for p in inputs]
    if weights.suffix.lower() != ".onnx" or hashes[1] != WEIGHTS_SHA:
        raise ValueError("Expected pinned published quantized ONNX checkpoint")
    try:
        seconds = pcm_duration(audio)
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid PCM WAV') from exc
    tokens = vocabulary(vocab)
    expected = None
    if reference is not None:
        if reference.stat().st_size > 256000:
            raise ValueError("Oversized reference")
        intervals = parse_htk(reference.read_text(encoding="utf-8-sig"))
        if intervals[-1][1] > round(seconds*TICKS_PER_SECOND)+1:
            raise ValueError("Reference extends beyond excerpt")
        expected = [row[2] for row in intervals]
        if any(p not in tokens.values() or p in ("<pad>","<s>","</s>","<unk>") for p in expected):
            raise ValueError("Reference labels must already match model inventory; no implicit mapping or silence removal")
    # Only audio enters the model. The optional reference is used after inference.
    try:
        ids, version = infer(audio, weights, seconds)
    except (RuntimeError, subprocess.SubprocessError) as exc:
        raise ValueError(f'Local phoneme inference failed: {exc}') from exc
    rows = collapse_ctc(ids, tokens)
    predicted = [row["token"] for row in rows]
    if [_sha(p) for p in inputs] != hashes:
        raise ValueError("Input bytes changed during inference")
    report = {"schema":"phoneme-observation-v1", "model":MODEL, "revision":REVISION,
              "weights_sha256":hashes[1], "vocabulary_sha256":hashes[2],
              "vocabulary_provenance_verified":False, "audio_sha256":hashes[0],
              "audio_duration_seconds":seconds, "device":"cpu", "onnxruntime":version,
              "reference_conditioned":False, "ctc_frames":len(ids),
              "observed_tokens":rows, "reference_comparison":None,
              "phonetic_alignment_verified":False, "correction_allowed":False,
              "automatic_acceptance":False, "audio_jobs_created":0,
              "studio_calls":0, "phoneme_inference_calls":1,
              "warnings":["Speech-trained model and quantized export not validated on singing.",
                          "Vocabulary identity is operator supplied; hash records bytes only.",
                          "CTC emission frames are not observed acoustic phone boundaries.",
                          "No language-specific accuracy claim, diagnosis or correction."]}
    if expected is not None:
        edits = distance(expected, predicted)
        report["reference_comparison"] = {
            "reference_sha256":hashes[3], "reference_tokens":len(expected),
            "observed_tokens":len(predicted), "token_edits":edits,
            "token_disagreement_rate":edits/len(expected),
            "reference_provenance_verified":False,
            "note":"Descriptive token disagreement; not certified pronunciation error rate."}
    out.parent.mkdir(parents=True, exist_ok=True)
    _write(out, report)
    return report
