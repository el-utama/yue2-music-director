"""Inspect local hardware and get read-only YuE2 Studio configuration advice."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys

from . import advisor_discovery as discovery
from .audio_critic import inventory_media
from .experiments import model_download_idle
from .native_recognition import BUSY_KEYS, _busy_keys, _write

GIB = discovery.GIB
TIERS = {
    "native": ("Full BF16", 12 * GIB),
    "quality-q8": ("Quality Q8_0", 8 * GIB),
    "balanced": ("Balanced Q6_K", 7 * GIB),
    "light": ("Light Q5_K_M", int(5.5 * GIB)),
}
# Pinned upstream prefers Q8_0 over BF16 even on a card with the BF16 tier.
PREFERENCE = ("quality-q8", "balanced", "light", "native")
BACKENDS = ("auto", "cuda", "vulkan", "cpu", "hip", "metal")
MODEL_ENGINE = "yue2-cpp"


def _flag(value):
    return value if type(value) is bool else None


def _activity(status):
    for key in BUSY_KEYS:
        value = status.get(key)
        expected = list if key in ("song_jobs", "covers_and_karaoke") else dict
        if value is not None and not isinstance(value, expected):
            return "unknown"
    try:
        return "busy" if _busy_keys(status) else "idle"
    except ValueError:
        return "unknown"


def _whisper_evidence(native):
    state = native.get("karaoke_settings_get", {})
    models = state.get("models")
    if (not isinstance(models, list) or not isinstance(state.get("provider"), str)
            or type(state.get("enabled")) is not bool or type(state.get("ready")) is not bool
            or "download" not in state
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                   or type(item.get("installed")) is not bool for item in models)):
        return "unknown"
    installed = any(item["id"] == "crisperwhisper-turbo" and item["installed"] for item in models)
    if (state["provider"] == "whisper" and state["enabled"] and state["ready"]
            and installed and state["download"] is None):
        return "local_assets_reported"
    return "reference_requirements_missing"


def _engine(native):
    reply = native.get("engine_options_get", {})
    options = discovery.object_value(reply.get("options"))
    effect = discovery.object_value(reply.get("in_effect"))
    cache = discovery.object_value(reply.get("kv_cache_now"))
    configured = {
        "backend": discovery.selected_value(options.get("backend"), BACKENDS),
        "kv_cache": discovery.selected_value(options.get("kv_cache"), ("auto", "f16", "q8")),
        "keep_loaded": discovery.selected_value(options.get("keep_loaded"), ("auto", "yes", "no")),
    }
    q8 = _flag(cache.get("q8"))
    launched_q8 = _flag(effect.get("kv_q8"))
    effective = {
        "backend": "cpu" if native.get("models_status", {}).get("engine_on_processor") is True else None,
        "kv_cache": ("q8" if q8 else "f16") if q8 is not None and (launched_q8 in (None, q8)) else None,
        "flash_attention": _flag(effect.get("flash_attention")),
        "keep_loaded": _flag(effect.get("keep_loaded")),
    }
    changes = [
        configured["kv_cache"] in ("f16", "q8") and effective["kv_cache"] is not None
        and configured["kv_cache"] != effective["kv_cache"],
        configured["keep_loaded"] in ("yes", "no") and effective["keep_loaded"] is not None
        and (configured["keep_loaded"] == "yes") != effective["keep_loaded"],
        effective["backend"] == "cpu" and configured["backend"] not in (None, "auto", "cpu"),
        q8 is not None and launched_q8 is not None and q8 != launched_q8,
    ]
    source = discovery.selected_value(reply.get("executable_source"), ("bundled", "environment", "settings", "managed_hip"))
    if source is None or "extra_args" not in options or "engine_bin" not in options:
        executable = "unknown"
    else:
        executable = "stock" if source == "bundled" and options["extra_args"] in ("", None, []) and options["engine_bin"] in ("", None) else "custom"
    return {"configured": configured, "effective": effective, "configuration_drift": any(changes),
            "starting": _flag(reply.get("engine_starting")), "executable": executable,
            "batch_limit": discovery.size(reply.get("effective_max_batch"), positive=True)}


def _models(native):
    status = native.get("models_status", {})
    own = native.get("models_own_list", {})
    pair = native.get("music_pair_status", {})
    stage = discovery.selected_value(pair.get("stage"), ("idle", "waiting_for_generation", "checking_files",
                                    "needs_install", "unloading", "starting_engine", "loading_model", "ready", "error"))
    active_kind = discovery.selected_value(discovery.object_value(pair.get("active")).get("kind"),
                                          ("local", "native", "signed"))
    selected = own.get("selected")
    if "selected" not in own or (selected is not None and not isinstance(selected, str)):
        backbone = "unknown"
    elif any("own_model" in summary and summary["own_model"] != selected
             for summary in (status, native.get("studio_status", {}))):
        backbone = "conflicting"
    elif selected and type(own.get("missing")) is bool:
        backbone = "own_missing" if own["missing"] else "own_selected"
    else:
        backbone = "stock" if selected is None and own.get("missing") is False else "unknown"
    noncommercial = False
    community = own.get("community")
    if selected and isinstance(community, list):
        for item in community:
            item = discovery.object_value(item)
            files = item.get("files")
            license_name = item.get("license")
            if (isinstance(files, list) and any(discovery.object_value(f).get("file") == selected for f in files)
                    and isinstance(license_name, str) and re.search(r"by[- ]nc|non[- ]?commercial", license_name, re.I)):
                noncommercial = True
    installed = status.get("installed_components")
    if not isinstance(installed, list) or any(not isinstance(i, str) or not i for i in installed):
        installed = None
    adapters = native.get("lora_list", {}).get("installed")
    return {
        "profile": discovery.selected_value(status.get("selected_profile_id"), TIERS),
        "backbone": backbone, "noncommercial_model": noncommercial,
        "owns_model_download": ("active" if own["download"] is not None else "idle") if "download" in own else "unknown",
        "custom_components": (status["selected_component_ids"] not in (None, [])
                              if "selected_component_ids" in status else None),
        "preset": (status["preset"] is not None) if "preset" in status else None,
        "installed_components": installed, "download_idle": model_download_idle(status) if "active" in status else None,
        "engine_ready": _flag(status.get("engine_ready")), "models_ready": _flag(status.get("ready")),
        "selection_matches_engine": _flag(status.get("selection_matches_engine")),
        "pair_stage": stage, "pair_active_kind": active_kind,
        "pair_load_on_create": _flag(pair.get("load_on_create")),
        "installed_adapter_count": (len(adapters) if isinstance(adapters, list)
                                    and all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in adapters)
                                    else None),
    }


def _catalog(native):
    reply = native.get("models_catalog", {})
    if reply.get("engine_id") != MODEL_ENGINE:
        return {}, "pinned_guide"
    profiles, components = reply.get("profiles"), reply.get("components")
    if not isinstance(profiles, list) or not isinstance(components, list):
        return {}, "pinned_guide"
    assets, rows = {}, {}
    for item in components:
        item = discovery.object_value(item)
        key = item.get("id")
        if not isinstance(key, str) or not key or key in assets:
            return {}, "pinned_guide"
        assets[key] = item
    for item in profiles:
        item = discovery.object_value(item)
        key = discovery.selected_value(item.get("id"), TIERS)
        if key is None:
            continue
        ids = item.get("components")
        if (key in rows or not isinstance(ids, list) or not ids
                or any(not isinstance(i, str) or i not in assets for i in ids)
                or len(set(ids)) != len(ids)):
            return {}, "pinned_guide"
        rows[key] = {"installable": item.get("installable") is True and item.get("backend") == MODEL_ENGINE,
                     "ram_bytes": discovery.gib_bytes(item.get("ram_needed_gb")),
                     "components": {i: assets[i] for i in ids}}
    return (rows, "studio_catalog") if rows else ({}, "pinned_guide")


def _estimate(profile, installed):
    if profile is None or installed is None:
        return None, None
    totals, partials = [], []
    for key, asset in profile["components"].items():
        if key in installed:
            continue
        total = discovery.size(asset.get("bytes"), positive=True)
        partial = discovery.size(asset.get("partial_bytes"))
        if total is None:
            return None, None
        totals.append(total)
        partials.append(total - partial if partial is not None and partial <= total else None)
    return sum(totals), sum(partials) if None not in partials else None


def _recommend(report, native):
    host, studio = report["host"], report["studio"]
    gpu, ram = host["gpu"], host["ram"]
    models, engine = studio["models"], studio["engine"]
    catalog, catalog_source = _catalog(native)
    # The catalog's RAM estimate is host-specific. Use it only when Studio's
    # cached GPU estimate agrees with the selected card and dedicated VRAM.
    hardware = discovery.object_value(native.get("models_status", {}).get("hardware"))
    total = gpu["memory"]["total_bytes"]
    available = gpu["memory"]["available_bytes"]
    catalog_matches_gpu = (total is not None and hardware.get("nvidia") is True
                           and isinstance(gpu.get("name"), str) and gpu["name"] == hardware.get("gpu_name")
                           and total == discovery.gib_bytes(hardware.get("total_vram_gb")))
    candidates = []
    for key in PREFERENCE:
        label, tier = TIERS[key]
        row = catalog.get(key)
        if (gpu["kind"] != "nvidia" or total is None or total < tier
                or (catalog_source == "studio_catalog" and (row is None or not row["installable"]))):
            continue
        required_ram = row["ram_bytes"] if row and catalog_matches_gpu else None
        disk_bytes, remaining = _estimate(row, models["installed_components"])
        model_free = host["model_volume"]["available_bytes"]
        insufficient_ram = (required_ram is not None and ram["total_bytes"] is not None
                            and ram["total_bytes"] < required_ram)
        insufficient_disk = disk_bytes is not None and model_free is not None and model_free < disk_bytes
        candidates.append({"profile": label, "tier_bytes": tier,
                           "studio_ram_estimate_bytes": required_ram,
                           "missing_full_set_file_bytes": disk_bytes,
                           "estimated_remaining_download_bytes": remaining,
                           "status": "blocked" if insufficient_disk or insufficient_ram else "supported_by_source",
                           "ram_below_estimate": insufficient_ram, "model_disk_below_estimate": insufficient_disk,
                           "free_vram_below_tier": available < tier if available is not None else None})
    candidate = next((c for c in candidates if c["status"] == "supported_by_source"), None)
    running_matches = (models["models_ready"] is True and models["engine_ready"] is True
                       and models["selection_matches_engine"] is True and engine["executable"] == "stock"
                       and engine["starting"] is False and not engine["configuration_drift"]
                       and models["pair_active_kind"] in (None, "local")
                       and models["pair_stage"] in ("idle", "ready")
                       and models["download_idle"] is True and models["owns_model_download"] == "idle"
                       and studio["activity"] == "idle" and gpu["state"] != "ambiguous")
    existing_stock = (running_matches and models["backbone"] == "stock"
                      and models["custom_components"] is False and models["preset"] is False
                      and any(c["profile"] == TIERS.get(models["profile"], (None,))[0]
                              and c["status"] == "supported_by_source" for c in candidates))
    if studio["activity"] == "busy" or models["pair_stage"] in (
            "waiting_for_generation", "checking_files", "unloading", "starting_engine", "loading_model"
    ) or engine["starting"] is True or models["download_idle"] is False or models["owns_model_download"] == "active":
        state, action = "blocked", "Let current Studio activity finish, then rerun the Advisor."
    elif gpu["state"] == "ambiguous" or engine["configuration_drift"] or models["backbone"] == "conflicting" or models["selection_matches_engine"] is False:
        state, action = "unknown", "Compare the configured and running GPU, model and engine options in Studio, then rerun the Advisor."
    elif existing_stock:
        state, action = "candidate_unverified", "Keep the current stock configuration for inspection. Use --ready for the existing Director production gate."
    elif models["backbone"] == "own_selected":
        state, action = "candidate_unverified", "Keep the selected model while you verify its base, decoder, adapter slots and rights. The Director reference gate requires the stock backbone."
    elif models["backbone"] == "own_missing":
        state, action = "blocked", "Inspect the missing selected own-model file in Studio before evaluating a replacement."
    elif models["pair_active_kind"] in ("native", "signed") or engine["executable"] == "custom" or models["custom_components"] is True or models["preset"] is True:
        state, action = "candidate_unverified", "Inspect the current custom model/runtime and its rights before considering a stock tier."
    elif gpu["kind"] == "nvidia" and total is not None and total < TIERS["light"][1]:
        state, action = "blocked", "The GPU is below the 5.5 GiB stock tier. Continue offline or export existing audio. Evaluate a separate experimental CPU profile only after target-host validation."
    elif candidate:
        state, action = "supported_by_source", f"{candidate['profile']} meets its documented total VRAM tier. Compare installed files, disk and available memory in Studio before considering any change."
    elif candidates:
        state, action = "blocked", "The modeled stock tiers exceed reported RAM or model-volume space. Review the resource estimates and existing installation."
    elif gpu["kind"] in ("vulkan", "cpu"):
        state, action = "candidate_unverified", "The observed platform is a candidate for separate native runtime validation. Continue with offline or existing-audio export in the meantime."
    else:
        state, action = "unknown", "Open Studio locally and check its Local engine GPU and model status, then rerun the Advisor."
    checks = []
    if host["platform"] not in ("win32", "simulation"):
        checks.append("Full Director production uses the Windows Studio host.")
    if host["ffmpeg"] is False:
        checks.append("FFmpeg and ffprobe are required for the Director production gate.")
    if models["models_ready"] is False or models["pair_stage"] == "needs_install":
        checks.append("Studio reports missing model assets or an unprepared pair.")
    if models["engine_ready"] is False or models["pair_stage"] == "error":
        checks.append("Studio reports the engine or active model pair is unavailable.")
    if models["noncommercial_model"]:
        checks.append("The selected model has a noncommercial license in the native catalog. Review its terms before use.")
    if models["installed_adapter_count"]:
        checks.append("Installed adapters do not establish usage or compatibility. Verify the exact base and AR/NAR slots before selecting an adapter.")
    if candidate and candidate["free_vram_below_tier"]:
        checks.append("Current free VRAM is below the suggested total-capacity tier. Recheck while Studio is idle.")
    if ram["available_bytes"] is not None and ram["available_bytes"] < 2 * GIB:
        checks.append("Reported free RAM is below the pinned Studio loading reserve of 2 GiB. Recheck before any load.")
    if catalog_matches_gpu and hardware.get("cuda") is None:
        checks.append("Studio has not reported a supported bundled CUDA build for this observation.")
    if studio["whisper"] == "reference_requirements_missing":
        checks.append("Studio has not reported the required enabled and installed local CrisperWhisper Turbo setup.")
    checks.append("Use a single track for any separately approved evaluation. Provider, managed MOSS and actual synthesis fit require separate checks.")
    return {"status": state, "action": action, "catalog_source": catalog_source, "stock_tiers": candidates,
            "preserve_current_stock": existing_stock, "checks": checks}


def _goal_advice(report, native):
    goal, host, studio = report["goal"], report["host"], report["studio"]
    if goal == "production":
        return _recommend(report, native)
    if goal == "training":
        gpu = host["gpu"]
        total = gpu["memory"]["total_bytes"]
        status, action = "unknown", "Check NVIDIA CUDA availability, dedicated VRAM and Studio training assets."
        if studio["activity"] == "busy":
            status, action = "blocked", "Let current Studio activity finish before evaluating training."
        elif (gpu["kind"] in ("cpu", "vulkan") or (gpu["kind"] == "nvidia" and total is not None and total < 11 * GIB)):
            status, action = "blocked", "Pinned Studio training guidance requires NVIDIA CUDA and at least 11 GiB dedicated VRAM."
        elif gpu["kind"] == "nvidia" and total is not None:
            hardware = discovery.object_value(native.get("models_status", {}).get("hardware"))
            cuda = discovery.selected_value(hardware.get("card_cuda"), ("cuda12", "cuda13"))
            same_card = (isinstance(gpu.get("name"), str) and gpu["name"] == hardware.get("gpu_name")
                         and total == discovery.gib_bytes(hardware.get("total_vram_gb")))
            if same_card and cuda:
                status, action = "supported_by_source", "CUDA and dedicated capacity meet source guidance. Verify the trainer, exact base, free resources and dataset rights separately."
            else:
                status, action = "candidate_unverified", "Dedicated capacity meets the training threshold. Confirm CUDA support and trainer availability in Studio."
        return {"status": status, "action": action}
    if goal == "listening":
        return {"status": "candidate_unverified", "action":
                "Use the retained audio for human listening. Check local Whisper and managed MOSS files separately for automated evidence."}
    if goal == "export":
        return {"status": "independent_workflow", "action":
                "Use music.cmd --export --list-songs to inspect playable Studio audio, or use a retained take. Check the source and export volume before copying."}
    return {"status": "independent_workflow", "action":
            "Use music.cmd --styles, --references or --knowledge for offline indexes. Model, Studio and provider setup are unnecessary for these indexes."}


def inspect(repo, url, goal, *, simulation=None, no_studio=False,
            media_dir=None, export_dir=None):
    if simulation is not None:
        kind, vram, ram = simulation
        gpu = {"state": "simulated", "kind": kind, "memory": discovery.memory(vram, None, "simulated")}
        host_ram = discovery.memory(ram, None, "simulated")
        native, states, connection = {}, {}, "not_requested"
        host = {"platform": "simulation", "logical_cpus": None, "ffmpeg": None}
        volumes = (None, None, None)
        moss = "not_checked"
    else:
        if no_studio:
            native, states, connection = {}, {}, "not_requested"
        else:
            native, states, connection = discovery.read_studio(url, goal)
        host_ram = discovery.resource_memory(native, discovery.host_memory())
        local_cards = discovery.host_nvidia() if goal in ("production", "training") else None
        gpu = discovery.gpu_evidence(native, local_cards)
        host = {"platform": sys.platform, "logical_cpus": os.cpu_count(), "ffmpeg":
                all(shutil.which(tool) is not None for tool in ("ffmpeg", "ffprobe"))}
        models_status = native.get("models_status", {})
        # Native-reported paths are inspected only on Windows fixed volumes.
        explicit_media = media_dir is not None
        data_root = models_status.get("data_directory") if sys.platform == "win32" else None
        model_root = models_status.get("model_root") if sys.platform == "win32" else None
        if media_dir is None and isinstance(data_root, str) and Path(data_root).is_absolute():
            media_dir = Path(data_root) / "media"
        if not isinstance(model_root, str) or not Path(model_root).is_absolute():
            model_root = None
        volumes = (model_root, media_dir, export_dir or repo / "results" / "exports")
        moss = "not_checked"
        if explicit_media and goal in ("listening", "production") and sys.platform == "win32":
            try:
                local_media = discovery.local_path(media_dir)
                if local_media is not None:
                    moss = "managed_files_found" if inventory_media(local_media)["ready"] else "managed_files_incomplete"
            except (OSError, ValueError, RuntimeError):
                moss = "unknown"
    host.update(ram=host_ram, gpu=gpu)
    for key, path in zip(("model", "media", "export"), volumes):
        host[key + "_volume"] = discovery.local_disk(path, key + "_volume")
    report = {
        "schema": "hardware-advisor-v1", "captured_utc": datetime.now(timezone.utc).isoformat(),
        "goal": goal, "input": "simulated" if simulation is not None else "observed",
        "host": host, "studio": {"connection": connection, "reads": states,
                                 "activity": _activity(native.get("studio_status", {})),
                                 "engine": _engine(native), "models": _models(native),
                                 "whisper": _whisper_evidence(native), "moss": moss,
                                 "trainer_installed": _flag(native.get("training_status", {}).get("trainer_installed"))},
        "execution_authorized": False, "synthesis_fit_verified": False,
    }
    report["advice"] = _goal_advice(report, native)
    return report


def shareable(report):
    host, studio = report["host"], report["studio"]
    models = studio["models"]
    return {**report, "host": {**host, "gpu": {key: host["gpu"][key] for key in ("state", "kind", "memory")}},
            "studio": {**studio, "models": {key: value for key, value in models.items() if key != "installed_components"}}}


def _gib_text(data):
    value = data["total_bytes"]
    available = data["available_bytes"]
    if value is None:
        return "unknown"
    capacity = f"{value / GIB:.2f} GiB"
    return capacity if available is None else f"{capacity} total, {available / GIB:.2f} GiB currently available"


def summary(report):
    host, studio, advice = report["host"], report["studio"], report["advice"]
    details = []
    if report["goal"] == "production":
        configured = studio["engine"]["configured"]
        effective = studio["engine"]["effective"]
        profile = TIERS.get(studio["models"]["profile"], ("unknown",))[0]
        details = [
            f"Selected stock profile: {profile} | backbone: {studio['models']['backbone']}",
            f"Configured backend: {configured['backend'] or 'unknown'} | KV cache configured: "
            f"{configured['kv_cache'] or 'unknown'}, effective: {effective['kv_cache'] or 'unknown'}",
        ]
    elif report["goal"] == "listening":
        details = [f"Whisper: {studio['whisper']} | MOSS: {studio['moss']}"]
    return "\n".join([
        f"Hardware Advisor | {report['goal']} | {report['input']}",
        f"Studio: {studio['connection']} | activity: {studio['activity']}",
        f"Dedicated VRAM ({host['gpu']['kind']}): " + _gib_text(host["gpu"]["memory"]),
        "System RAM: " + _gib_text(host["ram"]),
        *details,
        f"{advice['status'].replace('_', ' ').capitalize()}. {advice['action']}",
        *advice.get("checks", []),
        "Advice only. Actual load and synthesis fit have not been tested.",
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help=argparse.SUPPRESS)
    parser.add_argument("--advisor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--url", help="Explicit Studio loopback MCP URL")
    parser.add_argument("--goal", choices=tuple(discovery.GOAL_READS), default="production")
    parser.add_argument("--no-studio", action="store_true", help="Use local observations only")
    parser.add_argument("--media-dir", type=Path, help="Existing Studio managed media directory")
    parser.add_argument("--export-dir", type=Path, help="Local volume to evaluate for export")
    parser.add_argument("--simulate", choices=("nvidia", "vulkan", "cpu", "unknown"),
                        help="Use only hypothetical hardware inputs")
    parser.add_argument("--vram-gib", type=float, help="Simulated dedicated VRAM for NVIDIA")
    parser.add_argument("--ram-gib", type=float, help="Simulated system RAM")
    parser.add_argument("--json", action="store_true", help="Print the shareable JSON summary")
    parser.add_argument("--report", metavar="NAME.json", help="Save a new private report under results/advisor")
    args = parser.parse_args(argv)
    simulation = None
    vram, ram = discovery.gib_bytes(args.vram_gib), discovery.gib_bytes(args.ram_gib)
    if args.simulate:
        if args.media_dir or args.export_dir or args.url:
            parser.error("Simulation uses only the specified hypothetical hardware")
        if ((args.vram_gib is not None and (args.simulate != "nvidia" or vram is None))
                or (args.ram_gib is not None and ram is None)):
            parser.error("Simulation sizes must be positive and finite. VRAM requires --simulate nvidia.")
        simulation = (args.simulate, vram, ram)
    elif args.vram_gib is not None or args.ram_gib is not None:
        parser.error("Use --simulate before supplying hypothetical memory")
    out = None
    if args.report:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json", args.report):
            parser.error("Use a report name like first-run.json")
        # Preserve the project's local-only results convention and never
        # overwrite an existing snapshot or allow a caller-selected path.
        out = args.repo / "results" / "advisor" / ("advisor-" + args.report)
        if os.path.lexists(out):
            parser.error("Private report already exists. Choose a different name.")
    reply = inspect(args.repo, args.url, args.goal, simulation=simulation, no_studio=args.no_studio,
                    media_dir=args.media_dir, export_dir=args.export_dir)
    if out:
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            _write(out, {**reply, "private": True})
        except OSError:
            parser.error("Could not create the new private report in results/advisor")
    public = shareable(reply)
    print(json.dumps(public, indent=2, allow_nan=False) if args.json else summary(public))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
