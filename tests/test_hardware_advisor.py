"""Offline observations and policy regressions for the read-only Advisor."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from yue2_music_director import advisor_discovery as discovery
from yue2_music_director import hardware_advisor as advisor
from yue2_music_director.mcp import MCPError
from yue2_music_director.native_recognition import BUSY_KEYS

GIB = advisor.GIB
GPU_A = "GPU-10000000-0000-0000-0000-000000000001"
GPU_B = "GPU-10000000-0000-0000-0000-000000000002"
PRIVATE = "private-player-example"


def gpu_row(uuid, index, total=8):
    return {"index": index, "uuid": uuid, "name": PRIVATE, "memory_gb": total}


def observations():
    return {
        "studio_status": {**dict.fromkeys(BUSY_KEYS), "own_model": None},
        "studio_system": {"resources": {"ram_total_mb": 16384, "ram_used_mb": 8192,
                                       "gpus": [{"name": PRIVATE, "vram_total_mb": 8192, "vram_used_mb": 512}]}},
        "system_gpus": {"cards": [gpu_row(GPU_A, 0)], "chosen": 0, "chosen_uuid": GPU_A,
                        "running": 0, "running_uuid": GPU_A, "chosen_missing": False},
        "models_status": {"ready": True, "engine_ready": True, "selection_matches_engine": True,
                          "selected_profile_id": "balanced", "own_model": None, "preset": None,
                          "active": None, "selected_component_ids": None,
                          "installed_components": ["backbone-q6", "vae-f32", PRIVATE],
                          "hardware": {"gpu_name": PRIVATE, "nvidia": True, "cuda": "cuda12",
                                       "card_cuda": "cuda12", "total_vram_gb": 8}},
        "engine_options_get": {"options": {"backend": "cuda", "kv_cache": "q8", "keep_loaded": "auto",
                                           "engine_bin": None, "extra_args": ""},
                               "in_effect": {"kv_q8": True, "flash_attention": True, "keep_loaded": False},
                               "kv_cache_now": {"q8": True}, "executable_source": "bundled", "engine_starting": False},
        "models_own_list": {"selected": None, "missing": False, "download": None,
                            "folder": f"C:/Users/{PRIVATE}"},
        "lora_list": {"installed": [], "catalog": []},
        "music_pair_status": {"active": {"kind": "local"}, "stage": "ready",
                              "load_on_create": False, "error": None},
        "karaoke_settings_get": {"enabled": True, "provider": "whisper", "ready": True, "download": None,
                                 "models": [{"id": "crisperwhisper-turbo", "installed": True}]},
    }


class DiscoveryTests(unittest.TestCase):
    def make_client(self):
        factory = MagicMock()
        client = factory.return_value.connect.return_value
        client.tools.return_value = [
            {"name": name, "inputSchema": {"type": "object", "required": [],
             "properties": {key: {"type": "string", "enum": [value]} for key, value in args.items()}}}
            for name, args in (*discovery.READS, ("models_catalog", {}),
                               ("settings_get", {}), ("song_create", {}), ("models_download", {}))]
        client.call.side_effect = lambda name, args: {"structuredContent": observations().get(name, {"fixture": True})}
        return factory, client

    def test_only_audited_goal_reads_and_schema_mismatch(self):
        factory, client = self.make_client()
        for tool in client.tools.return_value:
            if tool["name"] == "models_own_list":
                tool["inputSchema"]["required"] = ["file"]
        data, states, connected = discovery.read_studio("http://127.0.0.1:8791/mcp", "production",
                                                       client_factory=factory)
        self.assertEqual(connected, "connected")
        self.assertEqual(states["models_own_list"], "schema_mismatch")
        self.assertNotIn("models_own_list", data)
        self.assertEqual([call.args for call in client.call.call_args_list],
                         [(name, args) for name, args in (*discovery.READS, ("models_catalog", {}))
                          if name in discovery.GOAL_READS["production"] - {"models_own_list"}])
        factory.assert_called_once_with("http://127.0.0.1:8791/mcp", timeout=3)

    def test_offline_and_non_loopback_skip_connector(self):
        factory, _ = self.make_client()
        discovery.read_studio("http://127.0.0.1:8791/mcp", "offline", client_factory=factory)
        _, _, state = discovery.read_studio("http://example.test/mcp", "production", client_factory=factory)
        self.assertEqual(state, "unavailable")
        factory.assert_not_called()

    def test_unavailable_partial_and_truncated_outputs(self):
        factory, client = self.make_client()
        def reply(name, args):
            if name == "studio_status":
                raise MCPError("MCP reply larger than 2 MB")
            if name == "models_catalog":
                return {"content": [{"type": "text", "text": '{"profiles": ... (cut)'}]}
            if name == "music_pair_status":
                return {"structuredContent": {"stage": "error", "error": PRIVATE}}
            return {"structuredContent": observations().get(name, {})}
        client.call.side_effect = reply
        data, states, connected = discovery.read_studio("http://127.0.0.1:8791/mcp", "production",
                                                       client_factory=factory)
        self.assertEqual(connected, "partial")
        self.assertEqual(states["studio_status"], "unavailable")
        self.assertEqual(states["models_catalog"], "unavailable")
        self.assertEqual(data["music_pair_status"]["stage"], "error")
        self.assertEqual(client.call.call_count, len(discovery.GOAL_READS["production"]))
        factory.return_value.connect.side_effect = OSError(PRIVATE)
        self.assertEqual(discovery.read_studio("http://127.0.0.1:8791/mcp", "production",
                                              client_factory=factory), ({}, {}, "unavailable"))

    def test_nvidia_csv_and_timeout(self):
        data = f"{GPU_A}, RTX 3050, 4096, 0, 582.10\n".encode()
        row, = discovery.parse_nvidia_csv(data)
        self.assertEqual(row["memory"]["total_bytes"], 4 * GIB)
        self.assertEqual(row["memory"]["available_bytes"], 0)
        self.assertIsNone(discovery.parse_nvidia_csv(data * 1024))
        self.assertIsNone(discovery.parse_nvidia_csv(data + data))
        unknown_free, = discovery.parse_nvidia_csv(data.replace(b", 0,", b", [N/A],"))
        self.assertIsNone(unknown_free["memory"]["available_bytes"])
        with patch.object(discovery, "_nvidia_executables", return_value=iter([Path(__file__)])), \
             patch.object(discovery.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 3)) as run:
            self.assertIsNone(discovery.host_nvidia())
        self.assertEqual(run.call_args.kwargs["timeout"], 3)
        self.assertIn("--query-gpu=uuid,name,memory.total,memory.free,driver_version", run.call_args.args[0])

    def test_gpu_disagreement_and_identity(self):
        native = observations()
        self.assertEqual(discovery.gpu_evidence(native, None)["memory"]["available_bytes"],
                         7680 * discovery.MIB)
        reply = native["system_gpus"]
        reply["cards"].append(gpu_row(GPU_B, 1, 16))
        self.assertIsNone(discovery.gpu_evidence(native, None)["memory"]["available_bytes"])
        self.assertEqual(discovery.gpu_evidence(native, None)["memory"]["total_bytes"], 8 * GIB)
        for running, running_uuid in ((1, GPU_B), (1, GPU_A), (0, GPU_B)):
            reply.update(running=running, running_uuid=running_uuid)
            self.assertEqual(discovery.gpu_evidence(native, None)["state"], "ambiguous")
        reply.update(chosen=None, chosen_uuid=None, running=None, running_uuid=None)
        self.assertIsNone(discovery.gpu_evidence(native, None)["memory"]["total_bytes"])
        self.assertEqual(discovery.gpu_evidence(native, None)["state"], "ambiguous")


class AdvisorTests(unittest.TestCase):
    def inspect_fixture(self, native, goal="production", free_disk=None):
        def disk(path, source):
            return discovery.memory(20 * GIB, free_disk if source == "model_volume" else None, source)
        with patch.object(discovery, "read_studio", return_value=(native, {}, "connected")), \
             patch.object(discovery, "host_nvidia", return_value=None), \
             patch.object(discovery, "host_memory", return_value=discovery.memory(None, None, None)), \
             patch.object(discovery, "local_disk", side_effect=disk):
            return advisor.inspect(Path.cwd(), None, goal)

    def test_simulation_tier_boundaries_and_no_probes(self):
        with patch.object(discovery, "read_studio") as studio, \
             patch.object(discovery, "host_nvidia") as nvidia, \
             patch.object(discovery, "host_memory") as ram, \
             patch.object(advisor.shutil, "which") as which, \
             patch.object(advisor.shutil, "disk_usage") as disk:
            for vram, expected in (
                (4, []), (5.499, []), (5.5, ["Light Q5_K_M"]), (6, ["Light Q5_K_M"]),
                (7, ["Balanced Q6_K", "Light Q5_K_M"]),
                (8, ["Quality Q8_0", "Balanced Q6_K", "Light Q5_K_M"]),
                (12, ["Quality Q8_0", "Balanced Q6_K", "Light Q5_K_M", "Full BF16"]),
            ):
                with self.subTest(vram=vram):
                    report = advisor.inspect(Path.cwd(), None, "production",
                                             simulation=("nvidia", int(vram * GIB), 16 * GIB))
                    self.assertEqual(report["input"], "simulated")
                    self.assertEqual([row["profile"] for row in report["advice"]["stock_tiers"]], expected)
                    self.assertFalse(report["execution_authorized"])
                    self.assertFalse(report["synthesis_fit_verified"])
                    self.assertIsNone(report["host"]["gpu"]["memory"]["available_bytes"])
                    if not expected:
                        self.assertEqual(report["advice"]["status"], "blocked")
            for probe in (studio, nvidia, ram, which, disk):
                probe.assert_not_called()

    def test_low_vram_cpu_candidate_preserves_stock_gate(self):
        for ram, status in ((None, "unknown"), (8 * GIB, "blocked"),
                            (advisor.LIGHT_CPU_RAM_ESTIMATE, "candidate_unverified"),
                            (16 * GIB, "candidate_unverified")):
            with self.subTest(ram=ram):
                report = advisor.inspect(Path.cwd(), None, "production",
                                         simulation=("nvidia", 4 * GIB, ram))
                self.assertEqual(report["advice"]["status"], "blocked")
                self.assertEqual(report["advice"]["stock_tiers"], [])
                alternative = report["advice"]["cpu_candidate"]
                self.assertEqual(alternative["status"], status)
                self.assertEqual(alternative["engine_options"],
                                 {"backend": "cpu", "kv_cache": "f16", "keep_loaded": "no", "max_batch": 1})
                self.assertAlmostEqual(alternative["estimated_system_ram_bytes"] / GIB, 8.94, places=2)
                self.assertIn("Experimental native Studio option", advisor.summary(report))
                self.assertFalse(report["execution_authorized"])
                self.assertFalse(report["synthesis_fit_verified"])
        for kind, vram in (("nvidia", int(5.5 * GIB)), ("vulkan", None), ("unknown", None)):
            report = advisor.inspect(Path.cwd(), None, "production", simulation=(kind, vram, 16 * GIB))
            self.assertNotIn("cpu_candidate", report["advice"])
        report = advisor.inspect(Path.cwd(), None, "production", simulation=("cpu", None, 16 * GIB))
        self.assertEqual(report["advice"]["cpu_candidate"]["status"], "candidate_unverified")

    def test_live_catalog_can_rule_out_pinned_cpu_candidate(self):
        host = {"platform": "win32", "gpu": {"kind": "nvidia", "memory": {"total_bytes": 4 * GIB}},
                "ram": {"total_bytes": 16 * GIB}}
        light = {"installable": True, "components": {
            key: {"bytes": value} for key, value in advisor.LIGHT_CPU_WEIGHTS.items()
        }}
        catalog = {"light": light}
        self.assertIsNotNone(advisor._light_cpu_candidate(host, catalog, "studio_catalog"))
        light["components"]["backbone-q5"]["bytes"] += 1
        self.assertIsNone(advisor._light_cpu_candidate(host, catalog, "studio_catalog"))
        self.assertIsNone(advisor._light_cpu_candidate(host, {}, "studio_catalog"))

    def test_unavailable_disabled_and_independent_goals(self):
        fresh = self.inspect_fixture({})
        self.assertEqual(fresh["advice"]["status"], "unknown")
        self.assertIsNone(fresh["studio"]["models"]["models_ready"])
        malformed = self.inspect_fixture({"studio_status": dict.fromkeys(BUSY_KEYS, False)})
        self.assertEqual(malformed["studio"]["activity"], "unknown")
        for goal in ("offline", "export"):
            report = advisor.inspect(Path.cwd(), None, goal, simulation=("nvidia", 4 * GIB, 16 * GIB))
            self.assertEqual(report["advice"]["status"], "independent_workflow")
        for kind in ("cpu", "vulkan", "unknown"):
            report = advisor.inspect(Path.cwd(), None, "production", simulation=(kind, None, 16 * GIB))
            self.assertEqual(report["advice"]["stock_tiers"], [])
            self.assertEqual(report["advice"]["status"], "unknown" if kind == "unknown" else "candidate_unverified")
        report = advisor.inspect(Path.cwd(), None, "training", simulation=("nvidia", 4 * GIB, 16 * GIB))
        self.assertEqual(report["advice"]["status"], "blocked")
        native = observations()
        native["training_status"] = {"trainer_installed": False, "datasets": [{"name": PRIVATE}]}
        report = self.inspect_fixture(native, "training")
        self.assertFalse(report["studio"]["trainer_installed"])
        self.assertNotIn(PRIVATE, json.dumps(advisor.shareable(report)))

    def test_preserve_current_and_distinguish_drift_and_busy(self):
        native = observations()
        ready = self.inspect_fixture(native)
        self.assertTrue(ready["advice"]["preserve_current_stock"])
        self.assertEqual(ready["studio"]["whisper"], "local_assets_reported")
        self.assertEqual(ready["studio"]["engine"]["effective"]["backend"], None)
        self.assertEqual(ready["advice"]["status"], "candidate_unverified")
        native["engine_options_get"]["options"]["kv_cache"] = "f16"
        drift = self.inspect_fixture(native)
        self.assertFalse(drift["advice"]["preserve_current_stock"])
        self.assertTrue(drift["studio"]["engine"]["configuration_drift"])
        self.assertEqual(drift["studio"]["engine"]["effective"]["kv_cache"], "q8")
        self.assertEqual(drift["advice"]["status"], "unknown")
        native["studio_status"]["song_jobs"] = [{"id": PRIVATE}]
        self.assertEqual(self.inspect_fixture(native)["advice"]["status"], "blocked")

    def test_vram_warning_tracks_preserved_tier_and_unknown_comparisons(self):
        native = observations()
        # 7.5 GiB free is below the highest candidate but above installed Balanced.
        report = self.inspect_fixture(native)
        tier = next(c for c in report["advice"]["stock_tiers"] if c["profile"] == "Balanced Q6_K")
        self.assertIsNone(tier["ram_below_estimate"])
        self.assertIsNone(tier["model_disk_below_estimate"])
        self.assertTrue(report["advice"]["preserve_current_stock"])
        self.assertFalse(any("free VRAM" in check for check in report["advice"]["checks"]))

        # Match the operator case: below 8 GiB total, about 6.3 GiB free
        # while the selected stock configuration is already idle.
        native["system_gpus"]["cards"][0]["memory_gb"] = 8151 / 1024
        native["studio_system"]["resources"]["gpus"] = [
            {"name": PRIVATE, "vram_total_mb": 8151, "vram_used_mb": 1703}]
        report = self.inspect_fixture(native)
        self.assertEqual(report["studio"]["activity"], "idle")
        self.assertEqual(report["advice"]["status"], "candidate_unverified")
        self.assertTrue(report["advice"]["preserve_current_stock"])
        self.assertEqual(report["advice"]["stock_tiers"][0]["profile"], "Balanced Q6_K")
        warning = next(check for check in report["advice"]["checks"] if "free VRAM" in check)
        self.assertIn("Balanced Q6_K", warning)
        self.assertNotIn("while Studio is idle", warning)

    def test_saved_or_stale_cache_is_not_effective_observation(self):
        native = observations()
        native["engine_options_get"]["in_effect"] = None
        report = self.inspect_fixture(native)
        engine = report["studio"]["engine"]
        self.assertEqual(engine["configured"]["kv_cache"], "q8")
        self.assertIsNone(engine["effective"]["kv_cache"])
        self.assertIsNone(engine["configuration_drift"])
        self.assertFalse(report["advice"]["preserve_current_stock"])
        native["engine_options_get"]["in_effect"] = {"kv_q8": False}
        engine = self.inspect_fixture(native)["studio"]["engine"]
        self.assertIsNone(engine["effective"]["kv_cache"])
        self.assertTrue(engine["configuration_drift"])

    def test_own_model_rights_and_adapters_without_private_values(self):
        native = observations()
        native["models_status"]["own_model"] = native["studio_status"]["own_model"] = PRIVATE
        native["models_own_list"].update(selected=PRIVATE, community=[
            {"files": [{"file": PRIVATE}], "license": "CC BY-NC-SA 4.0"}])
        native["lora_list"]["installed"] = [{"id": PRIVATE, "slots": ["ar"], "base": PRIVATE}]
        report = self.inspect_fixture(native)
        public = advisor.shareable(report)
        self.assertTrue(public["studio"]["models"]["noncommercial_model"])
        self.assertEqual(public["studio"]["models"]["installed_adapter_count"], 1)
        self.assertIn("verify its base, decoder, adapter slots and rights", public["advice"]["action"])
        for text in (json.dumps(public), advisor.summary(public)):
            self.assertNotIn(PRIVATE, text)
            self.assertNotIn(GPU_A.lower(), text)
        self.assertIn(PRIVATE, json.dumps(report))

    def test_catalog_disk_ram_headroom_and_installability(self):
        native = observations()
        native["models_status"].update(ready=False, engine_ready=False, selection_matches_engine=None)
        native["studio_system"]["resources"].update(ram_used_mb=15872,
            gpus=[{"name": PRIVATE, "vram_total_mb": 8192, "vram_used_mb": 4096}])
        native["models_catalog"] = {"engine_id": "yue2-cpp", "profiles": [
            {"id": "quality-q8", "installable": True, "backend": "yue2-cpp",
             "ram_needed_gb": 17, "components": ["backbone-q8", "vae-f32"]},
            {"id": "balanced", "installable": True, "backend": "yue2-cpp",
             "ram_needed_gb": 6, "components": ["backbone-q6", "vae-f32"]},
            {"id": "light", "installable": False, "backend": "yue2-cpp", "components": ["vae-f32"]},
        ], "components": [{"id": "backbone-q8", "bytes": 4 * GIB, "partial_bytes": GIB},
                          {"id": "backbone-q6", "bytes": 3 * GIB, "partial_bytes": 0},
                          {"id": "vae-f32", "bytes": GIB // 2, "partial_bytes": 0}]}
        report = self.inspect_fixture(native, free_disk=GIB)
        first, second = report["advice"]["stock_tiers"]
        self.assertTrue(first["ram_below_estimate"])
        self.assertTrue(first["model_disk_below_estimate"])
        self.assertEqual(first["estimated_remaining_download_bytes"], 3 * GIB)
        self.assertEqual(first["missing_full_set_file_bytes"], 4 * GIB)
        self.assertEqual(second["missing_full_set_file_bytes"], 0)
        self.assertIs(second["ram_below_estimate"], False)
        self.assertIs(second["model_disk_below_estimate"], False)
        self.assertTrue(second["free_vram_below_tier"])
        self.assertIn("Reported free RAM", " ".join(report["advice"]["checks"]))
        self.assertIn("Balanced Q6_K", report["advice"]["action"])

    def test_private_report_exclusive_and_shareable_json(self):
        with tempfile.TemporaryDirectory(prefix="advisor folder ") as temp:
            repo = Path(temp)
            args = ["--repo", temp, "--simulate", "nvidia", "--vram-gib", "4", "--json"]
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(advisor.main(args), 0)
            self.assertEqual(list(repo.iterdir()), [])
            self.assertEqual(json.loads(output.getvalue())["advice"]["status"], "blocked")
            args += ["--report", "first-run.json"]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(advisor.main(args), 0)
            path = repo / "results/advisor/advisor-first-run.json"
            original = path.read_bytes()
            self.assertTrue(json.loads(original)["private"])
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    advisor.main(args)
                with self.assertRaises(SystemExit):
                    advisor.main(args[:-1] + ["../private.json"])
            self.assertEqual(path.read_bytes(), original)
