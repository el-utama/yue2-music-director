"""Explicit, versioned historical knowledge selection for autonomous jobs."""
import re
from . import creative_knowledge as ck, knowledge_bank as kb, native_draft as nd

SCHEMA = "autonomous-knowledge-selection-v1"


def validate(value):
    if not isinstance(value, dict) or set(value) != {"schema", "snapshot", "sha256"} or value["schema"] != SCHEMA:
        raise ValueError("Invalid retained knowledge selection")
    saved = value["snapshot"]
    if not isinstance(saved, dict) or set(saved) != {"schema", "query", "roles"} or saved["schema"] != ck.VERSION:
        raise ValueError("Invalid knowledge snapshot")
    query = saved["query"]
    if not isinstance(query, str) or len(query) > 500 or not 1 <= len(re.findall(r"[^\W_]+", query)) <= 30:
        raise ValueError("Invalid knowledge query")
    roles = saved["roles"]
    if not isinstance(roles, dict) or set(roles) != set(ck.FIELDS):
        raise ValueError("Invalid knowledge roles")
    if not any(roles.values()):
        raise ValueError("No historical knowledge matches; choose a different query")
    for role, rows in roles.items():
        if not isinstance(rows, list) or len(rows) > 3:
            raise ValueError("Invalid knowledge rows")
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"work_id", "source_revision", "source_asset_hashes", "features"}:
                raise ValueError("Invalid knowledge row")
            key = row["work_id"]
            hashes = row["source_asset_hashes"]
            if (not isinstance(key, str) or not re.fullmatch(r"[a-z0-9-]{1,100}", key)
                    or key in seen or row["source_revision"] != kb.SOURCE_REV
                    or not isinstance(hashes, dict) or set(hashes) != {"lyrics", "score", "harmony"}
                    or any(not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{40}", x) for x in hashes.values())
                    or not isinstance(row["features"], dict)):
                raise ValueError("Invalid historical knowledge provenance")
            seen.add(key)
        ck.payload(saved, role)
    if value["sha256"] != nd.digest(nd._canonical({"schema": SCHEMA, "snapshot": saved})):
        raise ValueError("Retained knowledge checksum differs")
    return value


def select(repo, query):
    saved = ck.snapshot(repo / "local/knowledge-bank.sqlite", query)
    body = {"schema": SCHEMA, "snapshot": saved}
    return validate({**body, "sha256": nd.digest(nd._canonical(body))})


def resolve(repo, root, query, *, confirmed, consent):
    if root.exists():
        previous = nd.read(root / "job.json")
        selected = previous.get("knowledge_context")
        if selected is None:
            if query is not None or consent:
                raise ValueError("Cannot add knowledge to an existing job; use a new job")
            return None
        selected = validate(selected)
        if query is not None and query != selected["snapshot"]["query"]:
            raise ValueError("Retained knowledge query differs; use a new job")
        if confirmed and not consent:
            raise ValueError("Resuming knowledge job requires --confirm-knowledge-context")
        return selected
    if confirmed and (query is not None) != consent:
        raise ValueError("New knowledge job needs --knowledge-query and --confirm-knowledge-context together")
    return select(repo, query) if query is not None else None


def retained_snapshot(identity):
    selected = identity.get("knowledge_context")
    return validate(selected)["snapshot"] if selected is not None else None
