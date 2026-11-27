"""Explicit authored style selection; frozen local evidence, no source corpus transfer."""
import re
from . import style_library as sl, native_draft as nd

SCHEMA = "selected-style-v1"
GUIDANCE = ("Use this original, unrendered style recipe as optional creative inspiration. "
            "The operator's explicit request and typed requirements take precedence. "
            "Do not copy existing recordings or claim native control of tempo, mix, or duration.")

def validate(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {"schema", "id", "genre", "style", "sha256"}:
        raise ValueError("Invalid retained style selection")
    body = {k: snapshot[k] for k in ("schema", "id", "genre", "style")}
    if (body["schema"] != SCHEMA or body["genre"] not in sl.GENRES
            or not isinstance(body["id"], str)
            or not re.fullmatch(re.escape(body["genre"]) + r"-\d{3}", body["id"])
            or not 1 <= int(body["id"].rsplit("-", 1)[1]) <= 100
            or not isinstance(body["style"], str) or not 10 <= len(body["style"]) <= 500
            or snapshot["sha256"] != nd.digest(nd._canonical(body))):
        raise ValueError("Retained style selection differs or is invalid")
    return snapshot

def select(repo, style_id):
    if not isinstance(style_id, str):
        raise ValueError("Invalid style ID")
    match = re.fullmatch(r"([a-z]+)-(\d{3})", style_id)
    if not match or match[1] not in sl.GENRES or not 1 <= int(match[2]) <= 100:
        raise ValueError("Invalid style ID; use music.cmd --styles --genre GENRE to list recipes")
    rows = sl.load(repo / "data/style_library")
    row = next((r for r in rows if r["id"] == style_id), None)
    if row is None:
        raise ValueError("Unknown style ID")
    body = {"schema": SCHEMA, "id": row["id"], "genre": row["genre"], "style": row["style"]}
    return validate({**body, "sha256": nd.digest(nd._canonical(body))})

def resolve(repo, root, style_id):
    if root.exists():
        previous = nd.read(root / "job.json")
        selected = previous.get("style_recipe")
        if selected is None:
            if style_id is not None:
                raise ValueError("Cannot add a style to an existing job; use a new job")
            return None
        selected = validate(selected)
        if style_id is not None and selected["id"] != style_id:
            raise ValueError("Retained style ID differs; use a new job")
        return selected
    return select(repo, style_id) if style_id is not None else None

def payload(snapshot):
    selected = validate(snapshot)
    return {"schema": SCHEMA, "genre": selected["genre"],
            "style": selected["style"], "guidance": GUIDANCE}
