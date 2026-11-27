"""Native completion evidence from the Studio library response (not acoustic QA)."""
import math


def semantic_frame_count(tokens):
    """Count only a nonempty comma-separated stream of native codec IDs."""
    if not isinstance(tokens,str) or not tokens.strip():
        return None
    parts=tokens.split(",")
    for part in parts:
        value=part.strip()
        if not value or not value.isascii() or not value.isdecimal():
            return None
        # Bound conversion even for malformed giant integer strings.
        digits=value.lstrip("0") or "0"
        if len(digits)>5 or int(digits)>=32768:
            return None
    return len(parts)


def replay_cut_reason(replay):
    """Mirror the pinned Studio classifier on a complete, valid replay record."""
    if not isinstance(replay,dict) or replay.get("truncated") is not True:
        return None
    tokens=replay.get("semantic_tokens")
    duration=replay.get("duration",360)
    sampling=replay.get("semantic_sampling")
    ceiling=sampling.get("max_tokens",9000) if isinstance(sampling,dict) else 9000
    if (not isinstance(tokens,str) or not tokens.strip() or type(duration) not in (int,float)
            or not math.isfinite(duration) or duration<=0 or type(ceiling) is not int or ceiling<=0):
        return None
    frames=semantic_frame_count(tokens)
    # Avoid overflowing finite but unreasonable duration inputs.
    budget=ceiling if duration>=ceiling/25 else math.floor(duration*25)
    return ("length" if frames>=budget else "memory") if frames and budget>0 else None


def inspect_completion(song, song_id, job_id):
    if (not isinstance(song,dict) or song.get("id")!=song_id
            or not isinstance(song.get("metadata"),dict)
            or song["metadata"].get("job_id")!=job_id):
        raise ValueError("Native completion evidence identity mismatch")
    reason=song.get("cut_short")
    source="library_song_get"
    replay=song.get("replay_request")
    truncated=replay.get("truncated") if isinstance(replay,dict) else None
    if reason is None:
        derived=replay_cut_reason(replay)
        if derived is not None:
            reason=derived
            source="replay_request_pinned_studio_classifier"
    if reason in ("length","memory"):
        status="cut_short"
    elif reason is not None or truncated is True:
        status="truncated_reason_unknown"
    else:
        # The pinned engine omits a false marker. Valid semantic codes with an
        # absent flag are compatible with that format, but malformed evidence
        # must not silently become a provisional pass.
        valid_replay=isinstance(replay,dict)
        malformed_flag=valid_replay and "truncated" in replay and type(truncated) is not bool
        has_codes=valid_replay and "semantic_tokens" in replay
        frames=semantic_frame_count(replay.get("semantic_tokens")) if has_codes else None
        if malformed_flag or (has_codes and frames is None):
            status="unknown"
        else:
            status="not_flagged" if truncated is False or frames is not None else "unknown"
    return {"source":source,"status":status,
            "cut_short":reason if reason in ("length","memory") else None,
            "engine_truncated":truncated if type(truncated) is bool else None,
            "musical_completion_verified":False}


def blocks_provisional(evidence):
    return evidence.get("status")!="not_flagged"
