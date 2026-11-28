"""Bounded host and YuE2 MCP observations used by the Hardware Advisor."""
from __future__ import annotations

import csv
from collections import deque
import ctypes
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

from .mcp import Client, MCPError, configured_endpoint, unpack
from .studio_profile import READS, advertised_schemas

GIB = 1024 ** 3
MIB = 1024 ** 2
READ_ERRORS = (MCPError, OSError, ValueError, TypeError, AttributeError, RecursionError)
MODEL_READS = {
    "studio_status", "studio_system", "system_gpus", "models_status",
    "models_own_list", "music_pair_status", "engine_options_get", "lora_list",
}
GOAL_READS = {
    "offline": set(),
    "export": {"studio_status"},
    "listening": {"studio_status", "karaoke_settings_get"},
    "production": MODEL_READS | {"karaoke_settings_get", "models_catalog"},
    "training": {"studio_status", "studio_system", "system_gpus", "models_status", "training_status"},
}
GPU_UUID = re.compile(r"GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


def size(value, *, positive=False):
    return value if type(value) is int and int(positive) <= value < 2 ** 64 else None


def gib_bytes(value):
    if type(value) in (int, float) and 0 < value < 2 ** 34 and math.isfinite(value):
        return size(round(value * GIB), positive=True)
    return None


def object_value(value):
    return value if isinstance(value, dict) else {}


def selected_value(value, choices):
    return value if isinstance(value, str) and value in choices else None


def memory(total, available, source):
    total = size(total, positive=True)
    available = size(available)
    if total is None or available is None or available > total:
        available = None
    return {"total_bytes": total, "available_bytes": available, "source": source if total else None}


class _MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_uint32), ("memory_load", ctypes.c_uint32)] + [
        (name, ctypes.c_uint64) for name in
        ("total", "available", "page_total", "page_available",
         "virtual_total", "virtual_available", "virtual_extended")
    ]


def host_memory():
    if sys.platform == "win32":
        status = _MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return memory(status.total, status.available, "windows_memory_status")
    if sys.platform.startswith("linux"):
        try:
            with Path("/proc/meminfo").open(encoding="ascii") as source:
                lines = source.read(8192).splitlines()
            values = {}
            for line in lines:
                match = re.fullmatch(r"(MemTotal|MemAvailable):\s+(\d+) kB", line)
                if match:
                    key, value = match.groups()
                    values[key] = int(value) * 1024
            return memory(values.get("MemTotal"), values.get("MemAvailable"), "linux_meminfo")
        except (OSError, ValueError):
            pass
    return memory(None, None, None)


def _nvidia_executables():
    if sys.platform == "win32":
        for variable, relative in (("SystemRoot", "System32/nvidia-smi.exe"),
                                   ("ProgramFiles", "NVIDIA Corporation/NVSMI/nvidia-smi.exe")):
            root = os.environ.get(variable)
            if root and Path(root).is_absolute():
                yield Path(root) / relative
    elif sys.platform.startswith("linux"):
        yield Path("/usr/bin/nvidia-smi")


def parse_nvidia_csv(data):
    if len(data) > 16384:
        return None
    cards = []
    try:
        for row in csv.reader(data.decode("utf-8-sig").splitlines(), strict=True):
            uuid, name, total, free, driver = (field.strip() for field in row)
            total = size(int(total) * MIB, positive=True)
            if not GPU_UUID.fullmatch(uuid) or not name or total is None:
                return None
            available = int(free) * MIB if free.isascii() and free.isdecimal() else None
            cards.append({"uuid": uuid.lower(), "name": name[:128],
                          "memory": memory(total, available, "nvidia_smi"),
                          "driver": driver if re.fullmatch(r"[0-9.]{1,24}", driver) else None})
    except (ValueError, csv.Error):
        return None
    return cards if cards and len({card["uuid"] for card in cards}) == len(cards) else None


def host_nvidia():
    try:
        executable = next((path for path in _nvidia_executables() if path.is_file()), None)
        if executable is not None:
            result = subprocess.run(
                [str(executable), "--query-gpu=uuid,name,memory.total,memory.free,driver_version",
                 "--format=csv,noheader,nounits"], stdout=subprocess.PIPE,
                stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return parse_nvidia_csv(result.stdout)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def local_path(path, *, allow_missing=False):
    if not isinstance(path, (str, Path)) or not path:
        return None
    path = Path(path)
    if sys.platform != "win32":
        return path.resolve()
    return _fixed_windows_path(path, allow_missing)


def _fixed_windows_path(path, allow_missing):
    """Follow local Windows junctions without opening a remote target."""
    if not path.drive:
        path = path.absolute()
    if not path.is_absolute():
        return None
    pending = deque(path.parts[1:])
    folder = Path(path.anchor)
    for _ in range(64):
        if (not re.fullmatch(r"[A-Za-z]:", folder.drive)
                or ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(folder.anchor)) != 3):
            return None
        if not pending:
            return folder
        part = pending.popleft()
        if part == "..":
            folder = folder.parent
            continue
        candidate = folder / part
        try:
            attributes = candidate.lstat().st_file_attributes
        except FileNotFoundError:
            # Remaining path components are under a proven local ancestor.
            # Return the ancestor, which is enough to query its volume.
            return folder if allow_missing and ".." not in pending else None
        if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            target = Path(os.readlink(candidate).removeprefix("\\\\?\\"))
            if not target.is_absolute():
                if target.drive or target.root:
                    return None
                target = folder / target
            folder = Path(target.anchor)
            pending.extendleft(reversed(target.parts[1:]))
        else:
            folder = candidate
    return None


def local_disk(path, source):
    try:
        resolved = local_path(path, allow_missing=True)
        if resolved is not None:
            # Fixed ancestor walk for future model/export directories.
            for folder in (resolved, *resolved.parents)[:32]:
                if folder.is_dir():
                    usage = shutil.disk_usage(folder)
                    return memory(usage.total, usage.free, source)
    except (OSError, RuntimeError, ValueError):
        pass
    return memory(None, None, None)


def _accepts(schema, args):
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if (schema.get("type") != "object" or not isinstance(properties, dict)
            or not isinstance(required, list)
            or any(not isinstance(key, str) for key in required)
            or not set(required) <= args.keys() <= properties.keys()):
        return False
    for key, value in args.items():
        rule = object_value(properties[key])
        if rule.get("type") != "string" or not isinstance(rule.get("enum"), list) or value not in rule["enum"]:
            return False
    return True


def read_studio(url, goal, *, client_factory=Client):
    """Read only the fixed, audited tools for this goal, once per tool."""
    wanted = GOAL_READS[goal]
    if not wanted:
        return {}, {}, "not_requested"
    try:
        target = configured_endpoint(url)
        client = client_factory(target, timeout=3).connect()
        schemas = advertised_schemas(client.tools())
    except READ_ERRORS:
        return {}, {}, "unavailable"
    if "studio_status" not in schemas or not _accepts(schemas["studio_status"], {}):
        return {}, {}, "unrecognized"
    observations, states = {}, {}
    for name, args in (*READS, ("models_catalog", {})):
        if name not in wanted:
            continue
        if name not in schemas:
            states[name] = "not_advertised"
            continue
        if not _accepts(schemas[name], args):
            states[name] = "schema_mismatch"
            continue
        try:
            data = unpack(client.call(name, args))
            if (not isinstance(data, dict) or not data or "content" in data
                    or "structuredContent" in data
                    or (data.get("error") is not None and not
                        (name == "music_pair_status" and data.get("stage") == "error"))):
                raise ValueError("Unrecognized or truncated native observation")
            observations[name] = data
            states[name] = "read"
        except READ_ERRORS:
            states[name] = "unavailable"
    return observations, states, "connected" if "studio_status" in observations else "partial"


def resource_memory(native, local):
    resources = object_value(native.get("studio_system", {}).get("resources"))
    total = size(resources.get("ram_total_mb"), positive=True)
    used = size(resources.get("ram_used_mb"))
    if total and used is not None and used <= total:
        return memory(total * MIB, (total - used) * MIB, "studio_system_unused")
    return local


def _native_cards(rows):
    if not isinstance(rows, list):
        return None
    cards = []
    for row in rows:
        row = object_value(row)
        uuid, index, name = row.get("uuid"), size(row.get("index")), row.get("name")
        total = gib_bytes(row.get("memory_gb"))
        if not isinstance(uuid, str) or not GPU_UUID.fullmatch(uuid) or index is None or not total:
            return None
        cards.append({"uuid": uuid.lower(), "index": index, "name": name[:128] if isinstance(name, str) else None,
                      "memory": memory(total, None, "system_gpus")})
    if len({c["uuid"] for c in cards}) != len(cards) or len({c["index"] for c in cards}) != len(cards):
        return None
    return cards


def _card_ref(reply, key, cards):
    uuid, index = reply.get(key + "_uuid"), reply.get(key)
    if uuid is None and index is None:
        return None, False
    if ((uuid is not None and (not isinstance(uuid, str) or not GPU_UUID.fullmatch(uuid)))
            or (index is not None and size(index) is None)):
        return None, True
    matches = [card for card in cards if (uuid is None or card["uuid"] == uuid.lower())
               and (index is None or card["index"] == index)]
    return (matches[0], False) if len(matches) == 1 else (None, True)


def gpu_evidence(native, local_cards):
    reply = native.get("system_gpus", {})
    cards = _native_cards(reply.get("cards"))
    chosen, bad_chosen = _card_ref(reply, "chosen", cards or [])
    running, bad_running = _card_ref(reply, "running", cards or [])
    mismatch = (bad_chosen or bad_running or reply.get("chosen_missing") is True
                or (chosen is not None and running is not None and chosen != running))
    if cards and local_cards and {c["uuid"] for c in cards} != {c["uuid"] for c in local_cards}:
        mismatch = True
    card = running or chosen
    source = "running" if running else "configured" if chosen else None
    if not card and len(cards or local_cards or []) == 1:
        card = (cards or local_cards)[0]
        source = "single_detected"
    hardware = object_value(native.get("models_status", {}).get("hardware"))
    if mismatch or (not card and len(cards or local_cards or []) > 1):
        return {"state": "ambiguous", "kind": "nvidia", "memory": memory(None, None, None)}
    if card is not None:
        sample = next((row for row in local_cards or [] if row["uuid"] == card["uuid"]), None)
        if sample and sample["memory"]["total_bytes"] != card["memory"]["total_bytes"]:
            return {"state": "ambiguous", "kind": "nvidia", "memory": memory(None, None, None)}
        measured = (sample or card)["memory"]
        if measured["available_bytes"] is None and cards and card["name"]:
            resources = object_value(native.get("studio_system", {}).get("resources"))
            rows = resources.get("gpus")
            same_name = [c for c in cards if c["name"] == card["name"]]
            if len(same_name) == 1 and isinstance(rows, list):
                matches = [row for row in rows if isinstance(row, dict) and row.get("name") == card["name"]]
                if len(matches) == 1:
                    total = size(matches[0].get("vram_total_mb"), positive=True)
                    used = size(matches[0].get("vram_used_mb"))
                    if total and total * MIB == measured["total_bytes"] and used is not None and used <= total:
                        measured = memory(total * MIB, (total - used) * MIB, "studio_system_gpu")
        return {"state": source, "kind": "nvidia", "memory": measured,
                "uuid": card["uuid"], "name": card["name"], "driver": (sample or {}).get("driver")}
    # Studio's general hardware estimate has no per-card ID and may include
    # unified/integrated memory. Keep it out of the dedicated NVIDIA tiers.
    if hardware.get("vulkan") is True:
        kind = "vulkan"
    elif hardware.get("on_processor") is True:
        kind = "cpu"
    else:
        kind = "unknown"
    return {"state": "reported" if kind != "unknown" else "unknown",
            "kind": kind, "memory": memory(None, None, None)}
