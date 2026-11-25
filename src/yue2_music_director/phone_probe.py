"""Independent CTC phoneme hypotheses; not forced alignment or a correction gate."""
import argparse
import json
from pathlib import Path
import wave

from .native_recognition import _sha, _write
from .multilingual_fidelity import distance

MODEL="onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX"
REVISION="c69750f5043e5e1f8a71ab95dd3b98338c280c92"
WEIGHTS_SHA256="93265694093f5f91497181ed9d7791f43bc818d2e23c46caf988fd9b8b1a1fba"
VOCAB_SIZE=392
SAMPLE_RATE=16000


def vocabulary(path):
    if path.stat().st_size>32768:
        raise ValueError("Oversized vocabulary")
    raw=json.loads(path.read_text(encoding="utf-8-sig"))
    if (not isinstance(raw,dict) or len(raw)!=VOCAB_SIZE
            or any(type(i) is not int for i in raw.values())
            or set(raw.values())!=set(range(VOCAB_SIZE))
            or any(raw.get(k)!=v for k,v in
                   {"<pad>":0,"<s>":1,"</s>":2,"<unk>":3,"n":4,"s":5,"t":6,"ə":7}.items())):
        raise ValueError("Unexpected IPA vocabulary")
    return {i:p for p,i in raw.items()}


def collapse(ids, vocab):
    """Collapse adjacent repeated CTC IDs before removing blank; preserve unknowns."""
    previous=None
    result=[]
    for i in ids:
        if i not in vocab:
            raise ValueError("Predicted ID outside vocabulary")
        if i!=previous and i!=0:
            result.append(vocab[i])
        previous=i
    return result


def compare_phones(reference,hypothesis,vocab):
    """Descriptive token edit rate, no mapping or silent deletion of unknowns."""
    if (not reference or len(reference)>2000
            or any(p not in vocab.values() or p in ("<pad>","<s>","</s>","<unk>") for p in reference)):
        raise ValueError("Reference requires independently annotated tokens in exact model inventory")
    edits=distance(reference,hypothesis)["edits"] if hypothesis else len(reference)
    return {"reference_tokens":len(reference),"hypothesis_tokens":len(hypothesis),
            "edits":edits,"token_disagreement_rate":edits/len(reference),
            "reference_independence_verified":False,"pronunciation_verified":False}


def read_pcm(path):
    with wave.open(str(path),"rb") as f:
        if (f.getnchannels()!=1 or f.getframerate()!=SAMPLE_RATE
                or f.getsampwidth()!=2 or f.getcomptype()!="NONE"
                or not SAMPLE_RATE<=f.getnframes()<=30*SAMPLE_RATE):
            raise ValueError("Expected 1-30 second 16 kHz mono PCM16 WAV excerpt")
        frames=f.getnframes()
        raw=f.readframes(frames)
        if len(raw)!=frames*2:
            raise ValueError("Truncated PCM")
    return raw,frames


def recognize(raw, weights):
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        raise ValueError("Optional CPU ONNX runtime unavailable: "+type(exc).__name__) from exc
    x=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768.0
    if not np.isfinite(x).all() or float(x.var())<1e-10:
        raise ValueError("Silent or constant audio is not a phoneme reference")
    x=((x-x.mean())/np.sqrt(x.var()+1e-7)).astype(np.float32)[None,:]
    options=ort.SessionOptions()
    options.intra_op_num_threads=4
    options.inter_op_num_threads=1
    session=ort.InferenceSession(str(weights),sess_options=options,providers=["CPUExecutionProvider"])
    names={i.name:i.type for i in session.get_inputs()}
    if names.get("input_values")!="tensor(float)" or set(names)-{"input_values","attention_mask"}:
        raise ValueError("Unexpected ONNX inputs")
    feed={"input_values":x}
    if "attention_mask" in names:
        dtype={"tensor(int64)":np.int64,"tensor(int32)":np.int32}.get(names["attention_mask"])
        if dtype is None:
            raise ValueError("Unexpected attention mask type")
        feed["attention_mask"]=np.ones(x.shape,dtype=dtype)
    if "logits" not in {o.name for o in session.get_outputs()}:
        raise ValueError("Missing ONNX logits output")
    logits=session.run(["logits"],feed)[0]
    if (logits.ndim!=3 or logits.shape[0]!=1 or logits.shape[2]!=VOCAB_SIZE
            or not 0<logits.shape[1]<=1500 or not np.isfinite(logits).all()):
        raise ValueError("Unexpected or nonfinite phoneme logits")
    return np.argmax(logits[0],axis=-1).tolist(),ort.__version__


def probe(audio,weights,vocab_path,out,reference=None,*,confirm=False):
    if not confirm:
        raise ValueError("Explicit --confirm-probe required")
    audio,weights,vocab_path=[Path(p).resolve(strict=True) for p in (audio,weights,vocab_path)]
    out=Path(out).resolve()
    if out.exists() or len({audio,weights,vocab_path})!=3:
        raise ValueError("Distinct local inputs and fresh output required")
    if weights.suffix.lower()!=".onnx":
        raise ValueError("Pinned FP32 ONNX checksum mismatch")
    inputs=[audio,weights,vocab_path]
    if reference is not None:
        reference=Path(reference).resolve(strict=True)
        if reference in inputs or reference.stat().st_size>65536:
            raise ValueError("Distinct bounded reference required")
        inputs.append(reference)
    digests=[_sha(p) for p in inputs]
    if digests[1]!=WEIGHTS_SHA256:
        raise ValueError("Pinned FP32 ONNX checksum mismatch")
    vocab=vocabulary(vocab_path)
    raw,frames=read_pcm(audio)
    expected=None
    if reference is not None:
        expected=reference.read_text(encoding="utf-8-sig").split()
        compare_phones(expected,[],vocab)
    ids,version=recognize(raw,weights)
    hypothesis=collapse(ids,vocab)
    if [_sha(p) for p in inputs]!=digests:
        raise ValueError("Probe inputs changed")
    result={"schema":"independent-phone-probe-v1","model":MODEL,"revision":REVISION,
            "weights_sha256":digests[1],"vocab_sha256":digests[2],
            "vocabulary_provenance_verified":False,"audio_sha256":digests[0],
            "runtime_version":version,"device":"cpu","duration_seconds":frames/SAMPLE_RATE,
            "hypothesis":hypothesis,"status":"unvalidated_phone_hypothesis" if hypothesis else "no_phone_hypothesis",
            "comparison":compare_phones(expected,hypothesis,vocab) if expected is not None else None,
            "reference_sha256":digests[3] if expected is not None else None,
            "phonetic_alignment_verified":False,"pronunciation_verified":False,
            "correction_allowed":False,"automatic_acceptance":False,
            "phone_inference_calls":1,"audio_jobs_created":0,"library_mutations":0,
            "warnings":["Speech-trained acoustic model, not calibrated on this singing material.",
                        "Greedy CTC hypotheses have no verified phoneme boundaries.",
                        "Exact model vocabulary and independent annotation provenance must be verified separately.",
                        "Do not infer a correction, score ranking or a pronunciation verdict."]}
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("audio","weights","vocab","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--reference",type=Path)
    p.add_argument("--confirm-probe",action="store_true")
    a=p.parse_args()
    try:
        report=probe(a.audio,a.weights,a.vocab,a.out,a.reference,confirm=a.confirm_probe)
        print("Status:",report["status"])
        print("Predicted tokens:",len(report["hypothesis"]))
        if report["comparison"] is not None:
            print("Reference token disagreement:",report["comparison"]["token_disagreement_rate"])
        print("Pronunciation verified: no")
        return 0
    except Exception as exc:
        print("ERROR:",type(exc).__name__,str(exc))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
