"""Explicit, versioned historical knowledge selection for autonomous jobs."""
import re
import unicodedata
from . import creative_knowledge as ck, knowledge_bank as kb, native_draft as nd

SCHEMA = "autonomous-knowledge-selection-v1"
AUTO_SCHEMA = "autonomous-knowledge-auto-v1"

# Conservative lexical filtering, not semantic translation or genre inference.
STOP = frozenset(("a an the and or of to in for with on by at from as is be are it its "
                  "this that about into song music write create make original lyrics lyric "
                  "style genre please i me my you your we our he she they his her their "
                  "was were been has have had does did can could will would should "
                  "when where which who what how there than no not never without "
                  "yang dan atau di ke dari untuk dengan tentang buat buatkan lagu musik "
                  "lirik saya aku kamu ini itu sebuah dalam agar ingin bisa "
                  "tidak tak bukan jangan tanpa belum").split())


def brief_query(request):
    normalized = unicodedata.normalize("NFC", request).casefold()
    terms = dict.fromkeys(
        term for term in re.findall(r"[^\W_]+", normalized)
        if 3 <= len(term) <= 40 and term.isalpha() and term not in STOP
    )
    return " ".join(list(terms)[:12])


def validate(value):
    if isinstance(value, dict) and value.get("schema") == AUTO_SCHEMA:
        return validate_auto(value)
    if not isinstance(value, dict) or set(value) != {"schema", "snapshot", "sha256"} or value["schema"] != SCHEMA:
        raise ValueError("Invalid retained knowledge selection")
    saved = value["snapshot"]
    if not isinstance(saved, dict) or set(saved) != {"schema", "query", "roles"} or saved["schema"] not in (ck.LEGACY_VERSION, ck.VERSION):
        raise ValueError("Invalid knowledge snapshot")
    query = saved["query"]
    if not isinstance(query, str) or len(query) > 500 or not 1 <= len(re.findall(r"[^\W_]+", query)) <= 30:
        raise ValueError("Invalid knowledge query")
    roles = saved["roles"]
    if not isinstance(roles, dict) or set(roles) != set(ck.fields_for(saved["schema"])):
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


def validate_auto(value):
    if set(value) != {"schema", "query", "selection", "status", "sha256"}:
        raise ValueError("Invalid automatic knowledge selection")
    query = value["query"]
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("Invalid automatic knowledge query")
    if value["status"] == "matched":
        selected = value["selection"]
        if not isinstance(selected, dict) or selected.get("schema") != SCHEMA:
            raise ValueError("Invalid automatic knowledge match")
        validate(selected)
        if selected["snapshot"]["query"] != query:
            raise ValueError("Automatic knowledge query differs")
    elif value["status"] in ("no_terms", "no_matches"):
        if value["selection"] is not None or (not query) != (value["status"] == "no_terms"):
            raise ValueError("Invalid automatic knowledge abstention")
    else:
        raise ValueError("Invalid automatic knowledge status")
    body = {k: value[k] for k in ("schema", "query", "selection", "status")}
    if value["sha256"] != nd.digest(nd._canonical(body)):
        raise ValueError("Retained automatic knowledge checksum differs")
    return value


def select_auto(repo, request):
    query = brief_query(request)
    selected = None
    status = "no_terms"
    if query:
        saved = ck.snapshot(repo / "local/knowledge-bank.sqlite", query)
        status = "no_matches"
        if any(saved["roles"].values()):
            body = {"schema": SCHEMA, "snapshot": saved}
            selected = validate({**body, "sha256": nd.digest(nd._canonical(body))})
            status = "matched"
    body = {"schema": AUTO_SCHEMA, "query": query, "selection": selected, "status": status}
    return validate_auto({**body, "sha256": nd.digest(nd._canonical(body))})


def select(repo, query):
    saved = ck.snapshot(repo / "local/knowledge-bank.sqlite", query)
    body = {"schema": SCHEMA, "snapshot": saved}
    return validate({**body, "sha256": nd.digest(nd._canonical(body))})


def resolve(repo, root, query, *, confirmed, consent, auto=False, request=None):
    if auto and query is not None:
        raise ValueError("Choose automatic knowledge or a manual query, not both")
    if root.exists():
        previous = nd.read(root / "job.json")
        selected = previous.get("knowledge_context")
        if selected is None:
            if query is not None or auto or consent:
                raise ValueError("Cannot add knowledge to an existing job; use a new job")
            return None
        selected = validate(selected)
        if selected["schema"] == AUTO_SCHEMA:
            if query is not None:
                raise ValueError("Retained automatic knowledge mode differs; use a new job")
        elif auto or (query is not None and query != selected["snapshot"]["query"]):
            raise ValueError("Retained knowledge query differs; use a new job")
        if confirmed and not consent:
            raise ValueError("Resuming knowledge job requires --confirm-knowledge-context")
        return selected
    if confirmed and (query is not None or auto) != consent:
        raise ValueError("New knowledge job needs --knowledge-query or --knowledge-auto and --confirm-knowledge-context together")
    if auto:
        return select_auto(repo, request)
    return select(repo, query) if query is not None else None


def retained_snapshot(identity):
    selected = identity.get("knowledge_context")
    if selected is None:
        return None
    selected = validate(selected)
    if selected["schema"] == AUTO_SCHEMA:
        selected = selected["selection"]
    return selected["snapshot"] if selected is not None else None
