"""Native completion evidence from the Studio library response (not acoustic QA)."""


def inspect_completion(song, song_id, job_id):
    if (not isinstance(song,dict) or song.get("id")!=song_id
            or not isinstance(song.get("metadata"),dict)
            or song["metadata"].get("job_id")!=job_id):
        raise ValueError("Native completion evidence identity mismatch")
    reason=song.get("cut_short")
    replay=song.get("replay_request")
    truncated=replay.get("truncated") if isinstance(replay,dict) else None
    if reason in ("length","memory"):
        status="cut_short"
    elif reason is not None or truncated is True:
        status="truncated_reason_unknown"
    else:
        # Older engines omit the marker; absence is not proof of a musical ending.
        status="not_flagged" if truncated is False or isinstance(replay,dict) and replay.get("semantic_tokens") else "unknown"
    return {"source":"library_song_get","status":status,
            "cut_short":reason if reason in ("length","memory") else None,
            "engine_truncated":truncated if type(truncated) is bool else None,
            "musical_completion_verified":False}


def blocks_provisional(evidence):
    return evidence.get("status")!="not_flagged"
