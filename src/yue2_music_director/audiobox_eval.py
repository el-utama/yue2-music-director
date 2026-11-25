"""Optional AudioBox inference using the upstream model and predictor, never Studio generation."""
import importlib.metadata
import json
import math
from pathlib import Path

from .native_recognition import _sha, _write

MODEL_REVISION = "ce393651a6c9d61f62f8c3c68676229863a8a200"
WEIGHTS_SHA256 = "a5a3c2412649cc2384ec525ffd5180ce6c4778f43bed6108e0a1303de04d014e"
AXES = ("CE", "CU", "PC", "PQ")
# Verified public model card config (not arbitrary remote code).
CONFIG = {
    "normalize_embed": True, "nth_layer": 13, "output_dim": 1,
    "precision": "32", "proj_act_fn": "gelu", "proj_dropout": 0.0,
    "proj_ln": True, "proj_num_layer": 5, "use_weighted_layer_sum": True,
    "target_transform": {
        "CE": {"mean": 5.06865, "std": 1.93029},
        "CU": {"mean": 5.73633, "std": 1.75669},
        "PC": {"mean": 3.18591, "std": 1.86637},
        "PQ": {"mean": 6.57505, "std": 1.51466},
    },
}


def _predictor(weights):
    try:
        import torch
        import torchaudio
        from safetensors.torch import load_file
        from audiobox_aesthetics.infer import AesPredictor
        from audiobox_aesthetics.model.aes import AesMultiOutput, Normalize
    except ImportError as exc:
        raise ValueError(f"AudioBox import failed: {type(exc).__name__}: {exc}; see docs/QUALITY_EVALUATION.md") from exc
    version = importlib.metadata.version("audiobox-aesthetics")
    if version != "0.0.4":
        raise ValueError("Expected audited AudioBox 0.0.4 API")
    # Use official architecture and inference methods; bypass only automatic
    # device selection/download/pickle loading in setup_model.
    class LocalPredictor(AesPredictor):
        def setup_model(self):
            self.device = torch.device("cpu")
            self.model = AesMultiOutput(**CONFIG)
            self.model.load_state_dict(load_file(str(weights), device="cpu"), strict=True)
            self.model.eval()
            self.target_transform = {
                axis: Normalize(**CONFIG["target_transform"][axis]) for axis in AXES}
    predictor = LocalPredictor(checkpoint_pth=None, data_col="path")
    return predictor, {"audiobox":version,"torch":torch.__version__,
                       "torchaudio":torchaudio.__version__}


def evaluate(audio, weights, out, *, confirm=False):
    if not confirm:
        raise ValueError("Explicit --confirm-evaluation required (local CPU inference)")
    paths = [Path(p).resolve(strict=True) for p in audio]
    weights, out = Path(weights).resolve(strict=True), Path(out).resolve()
    if not 1 <= len(paths) <= 4 or len(set(paths)) != len(paths):
        raise ValueError("Choose one to four distinct existing audio files")
    if any(not p.is_file() or p.suffix.lower() not in (".wav", ".flac") for p in paths):
        raise ValueError("Expected local WAV/FLAC")
    if out.exists():
        raise ValueError("Fresh output required")
    if weights.suffix.lower() != ".safetensors" or _sha(weights) != WEIGHTS_SHA256:
        raise ValueError("Expected the published AudioBox safetensors checkpoint")
    # Check duration using existing ffprobe path before loading a full song.
    import shutil
    from .acoustic import _run
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise ValueError("ffprobe required")
    durations = []
    for p in paths:
        raw = _run([ffprobe,"-v","error","-f",p.suffix.lower()[1:],
                    "-protocol_whitelist","file","-select_streams","a",
                    "-show_entries","stream=duration,channels,sample_rate",
                    "-of","json",str(p)],30)
        info = json.loads(raw.stdout)
        streams = info["streams"]
        if len(streams) != 1:
            raise ValueError("Exactly one audio stream required")
        s = streams[0]
        duration = float(s["duration"])
        if not math.isfinite(duration) or not 1 <= duration <= 360 or int(s["channels"]) not in (1,2) or not 8000 <= int(s["sample_rate"]) <= 96000:
            raise ValueError("Audio outside bounded evaluation format/duration")
        durations.append(duration)
    hashes = [_sha(p) for p in paths]
    try:
        predictor, versions = _predictor(weights)
    except (RuntimeError, OSError) as exc:
        raise ValueError("Local AudioBox checkpoint/runtime could not be loaded") from exc
    rows = []
    for p, digest, seconds in zip(paths, hashes, durations):
        # One song per forward; upstream uses weighted 10 s mono windows.
        try:
            scores = predictor.forward([{"path":str(p)}])
        except (RuntimeError, OSError) as exc:
            raise ValueError("Local AudioBox inference failed; no score recorded") from exc
        if not isinstance(scores,list) or len(scores)!=1 or not isinstance(scores[0],dict) or set(scores[0])!=set(AXES):
            raise ValueError("Unexpected evaluator output")
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in scores[0].values()):
            raise ValueError("Nonfinite evaluator output")
        rows.append({"arm":len(rows)+1,"audio_sha256":digest,"duration_seconds":seconds,
                     "scores":scores[0]})
    if [_sha(p) for p in paths] != hashes or _sha(weights) != WEIGHTS_SHA256:
        raise ValueError("Evaluation input changed")
    result = {"schema":"audiobox-evaluation-v1","model":"facebook/audiobox-aesthetics",
              "model_revision":MODEL_REVISION,"weights_sha256":WEIGHTS_SHA256,
              "device":"cpu","versions":versions,"rows":rows,
              "generation_calls":0,"recognition_calls":0,"training_calls":0,
              "library_mutations":0,"automatic_acceptance":False,
              "warnings":["Predicted aesthetics, not verified phonetic or musical correctness.",
                          "Full song scores aggregate mono 10 second windows; not a stereo or long-range structure assessment.",
                          "No automatic winner or calibrated acceptance threshold."]}
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,result)
    return result
