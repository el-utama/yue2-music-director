"""Local-only capability inventory. A snapshot is not permission or a compatibility certificate."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

from .mcp import Client, MCPError, configured_endpoint, unpack
from .native_recognition import _write

# Audited GET/composite-read handlers at Studio ca37d2d. Do not call tools
# merely because their name sounds read-only. No settings_get (credentials),
# catalog search, dataset preparation, downloads, UI actions or inference.
READS = (
    ("studio_status", {}),
    ("studio_capabilities", {}),
    ("song_defaults", {}),
    ("models_status", {}),
    ("music_pair_status", {}),
    ("engine_options_get", {}),
    ("models_own_list", {}),
    ("studio_system", {}),
    ("system_gpus", {}),
    ("lora_list", {"response_format": "detailed"}),
    ("karaoke_settings_get", {"response_format": "concise"}),
    ("separator_status", {}),
    ("training_status", {"response_format": "concise"}),
)


def capture_profile(out, url=None):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Fresh private Studio profile report required")
    client = Client(configured_endpoint(url), timeout=10).connect()
    advertised = client.tools()
    schemas = {}
    for item in advertised:
        if (not isinstance(item, dict) or not isinstance(item.get("name"), str)
                or not item["name"] or item["name"] in schemas
                or not isinstance(item.get("inputSchema"), dict)):
            raise ValueError("Unrecognized or duplicate advertised tool schema")
        schemas[item["name"]] = item["inputSchema"]
    if "studio_status" not in schemas:
        raise ValueError("Connected MCP server does not advertise studio_status")
    observations, errors, missing = {}, {}, []
    for name, args in READS:
        if name not in schemas:
            missing.append(name)
            continue
        try:
            # Do not retry, silently switch provider, or adapt to an unknown schema.
            data = unpack(client.call(name, args))
            if not isinstance(data, (dict, list)) or (isinstance(data, dict) and
                    ("content" in data or "structuredContent" in data or data.get("error") is not None)):
                raise ValueError("Unrecognized native result")
            observations[name] = data
        except (MCPError, OSError, ValueError, TypeError, KeyError) as exc:
            errors[name] = type(exc).__name__
            if name == "studio_status":
                raise ValueError("Studio status unavailable; inventory aborted") from exc
    schema_hash = hashlib.sha256(json.dumps(schemas, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    summary = {
        "schema": "studio-profile-v1",
        "status": "reads_complete_unverified" if not errors and not missing else "partial_inventory",
        "protocol": client.version,
        "advertised_tool_count": len(schemas),
        "tool_schema_sha256": schema_hash,
        "successful_reads": sorted(observations),
        "missing_reads": missing,
        "failed_reads": errors,
        "compatibility_verified": False,
        "execution_authorized": False,
        "generation_calls": 0,
        "recognition_calls": 0,
        "training_calls": 0,
        "downloads_requested": 0,
        "settings_writes": 0,
        "library_mutations": 0,
    }
    report = {**summary, "captured_utc": datetime.now(timezone.utc).isoformat(),
              "private": True, "tool_input_schemas": schemas, "observations": observations,
              "warnings": [
                  "Keep this report local; status and catalog responses may contain private IDs, paths, names and other metadata.",
                  "Read completeness does not establish model/adapter compatibility, availability for a specific task, licensing or idle state.",
                  "Snapshot is non-atomic; recheck actual active model, schemas, options and resource status before any operation.",
                  "Configured and effective engine/model settings may differ. Do not infer an active model from a downloaded catalog entry.",
                  "This does not inspect every engine or download model weights. A missing tool is unknown/unavailable, not permission to substitute another provider.",
              ]}
    out.parent.mkdir(parents=True, exist_ok=True)
    _write(out, report)
    # Console summary deliberately excludes native values, endpoint and file paths.
    return summary
