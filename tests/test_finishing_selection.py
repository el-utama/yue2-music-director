import tempfile
import unittest
from pathlib import Path
from yue2_music_director.finishing_selection import select
from yue2_music_director.director import direct
from yue2_music_director.native_recognition import _sha,_write
from yue2_music_director.multilingual_fidelity import compare
from yue2_music_director.native_process import effect_request


class SelectionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"source.flac"
        self.source.write_bytes(b"source")
        self.lyrics=self.root/"lyrics.txt"
        self.reference="[Verse]\none two three"
        self.lyrics.write_text(self.reference,encoding="utf-8")
        self.baseline=self.root/"baseline.json"
        _write(self.baseline,{"provider":"whisper","text":"one two"})
        self.sh,self.lh,self.bh=map(_sha,(self.source,self.lyrics,self.baseline))
        self.a={"sha256":self.sh,"duration_seconds":5.0,"sample_rate_hz":48000,
                "channels":2,"integrated_lufs":-16.6,"true_peak_dbtp":0.0}

    def asr(self,d,target,transcript):
        d.mkdir()
        digest=_sha(target)
        _write(d/"submission.json",{"state":"SUBMITTING","audio_sha256":digest,
                                     "provider":"whisper","language_requested":None})
        _write(d/"receipt.json",{"state":"RESPONSE_RECEIVED","audio_sha256":digest})
        _write(d/"recognition.json",{"provider":"whisper","text":transcript})
        return compare(self.reference,"one two",transcript,"en")

    def custom(self,peak):
        d=self.root/"custom"
        (d/"dynamics").mkdir(parents=True)
        target=d/"dynamics/candidate.flac"
        target.write_bytes(b"custom")
        digest=_sha(target)
        acoustic={"arms":{"A":self.a,"B":{**self.a,"sha256":digest,"true_peak_dbtp":peak}}}
        screen=self.asr(d/"recognition",target,"one two three")
        hashes={"mix":self.sh,"lyrics":self.lh,"baseline_asr":self.bh}
        _write(d/"report.json",{"schema":"finish-existing-v1","source_sha256":hashes,
            "language":"en","candidate_sha256":digest,"dynamics_status":"candidate_created",
            "status":"candidate_nonregression_unverified","recognition_calls":1,"lyric_screen":screen})
        _write(d/"dynamics/report.json",{"status":"candidate_created","source_sha256":{"mix":self.sh},"acoustic":acoustic})
        return d

    def native(self,transcript="one two"):
        d=self.root/"native"
        c=d/"headroom-continuation"
        c.mkdir(parents=True)
        raw=d/"preview.flac"
        raw.write_bytes(b"raw")
        target=c/"candidate.flac"
        target.write_bytes(b"native")
        rh,digest=_sha(raw),_sha(target)
        request=effect_request("song","naturalize",0.2)
        screening={"language":"en","lyrics_sha256":self.lh,"baseline_asr_sha256":self.bh}
        _write(d/"submission.json",{"state":"SUBMITTING","source_sha256":self.sh,"request":request,"screening":screening})
        _write(d/"run_identity.json",{"run_id":"r","request":request})
        _write(d/"report.json",{"status":"preview_acoustic_blocked","source_sha256":self.sh,
            "preview_sha256":rh,"run_id":"r","request":request,"acoustic":{"arms":{"A":self.a,"B":{**self.a,"sha256":rh,"integrated_lufs":-17.07,"true_peak_dbtp":-0.45}}}})
        _write(c/"plan.json",{"gain_db":-0.6,"source_sha256":self.sh,"raw_preview_sha256":rh,
            "run_id":"r","screening":screening})
        before={"arms":{"A":self.a,"B":{**self.a,"sha256":rh,"integrated_lufs":-17.07,"true_peak_dbtp":-0.45}}}
        after={"arms":{"A":self.a,"B":{**self.a,"sha256":digest,"integrated_lufs":-17.67,"true_peak_dbtp":-1.05}}}
        screen=self.asr(c/"recognition",target,transcript)
        _write(c/"report.json",{"status":"candidate_nonregression_unverified","gain_db":-0.6,
            "before":before,"after":after,"recognition_calls":1,"lyric_screen":screen})
        return d

    def run_selection(self,custom=None,native=None):
        return select(self.source,self.lyrics,self.baseline,"en",self.root/"selection.json",
                      custom=custom,native=native)

    def test_headroom_gate_before_asr_ranking(self):
        result=self.run_selection(self.custom(0),self.native())
        self.assertEqual(result["status"],"provisional_candidate")
        self.assertEqual(result["candidates"][0]["reason"],"insufficient_headroom")
        self.assertTrue(result["candidates"][1]["eligible"])
        self.assertEqual(result["recognition_calls"],0)

    def test_tie_retains_source(self):
        result=self.run_selection(self.custom(-1.1),self.native("one two three"))
        self.assertEqual(result["status"],"tie_no_unique_candidate")
        self.assertEqual(Path(result["provisional_output"]),self.source.resolve())

    def test_mutated_candidate_rejected(self):
        d=self.custom(-1.1)
        (d/"dynamics/candidate.flac").write_bytes(b"changed")
        result=self.run_selection(d)
        self.assertEqual(result["status"],"retain_original_no_eligible_candidate")
        self.assertEqual(result["candidates"][0]["reason"],"evidence_invalid")


    def test_director_preserves_verified_technical_candidate_and_stops(self):
        result=direct(self.source,self.lyrics,self.baseline,"en",self.root/"director",
                      custom=self.custom(0),native=self.native())
        self.assertEqual(result["status"],"provisional_candidate")
        self.assertEqual(result["next_action"],"preserve_provisional_and_stop")
        self.assertEqual(result["execution_budget"],{"audio_jobs":0,"native_processing":0,"recognition":0,"score_edits":0})
        self.assertEqual(result["findings"][0]["issue"],"lyric_disagreement")
        self.assertEqual(result["findings"][0]["execution"],"blocked_missing_verified_alignment")
        self.assertEqual(result["findings"][1]["issue"],"insufficient_headroom")
        self.assertEqual(result["native_first_actions"][0]["action"],"use_existing_provisional_file")
        self.assertEqual(result["native_first_actions"][1]["director_command"],"timing-evidence")
        self.assertFalse(result["training_recommended"])
        self.assertFalse(result["lyric_localization"]["audio_timestamps_verified"])
        self.assertEqual(result["lyric_localization"]["lines"][0]["edits"],1)
        self.assertTrue((self.root/"director/selection.json").is_file())
        self.assertTrue((self.root/"director/report.json").is_file())

    def test_director_never_forces_another_candidate(self):
        result=direct(self.source,self.lyrics,self.baseline,"en",self.root/"director",
                      custom=self.custom(0))
        self.assertEqual(result["next_action"],"retain_original_and_stop")
        self.assertTrue(any(a["action"]=="consider_native_export_for_library_source" for a in result["native_first_actions"]))
        self.assertEqual(Path(result["provisional_output"]),self.source.resolve())
        self.assertEqual(result["recognition_calls"],0)
        self.assertFalse(result["automatic_acceptance"])


    def test_direct_native_pass_uses_actual_writer_contract(self):
        from unittest.mock import patch, Mock
        from yue2_music_director.native_process import preview
        from yue2_music_director.native_recognition import BUSY_KEYS
        client=Mock()
        request=effect_request("fixture","naturalize",0.2)
        run={"id":"r","song_id":"fixture","stages":["naturalize"],
             "request":{"naturalize":request["naturalize"]},"done":True,
             "preview_ready":True,"error":None}
        names=("studio_status","library_song_files","processing_get","processing_start",
               "karaoke_settings_get","lyrics_recognise")
        client.tools.return_value=[{"name":n,"inputSchema":{"properties":{"song_id":{},"naturalize":{}}}} for n in names]
        submitted=[]
        def call(name,args):
            if name=="processing_start":
                submitted.append(name)
                work=self.root/"processing"
                work.mkdir()
                (work/"preview.flac").write_bytes(b"native preview")
                return {"started":True}
            if name=="processing_get":
                return {"run":run if submitted else None}
            if name=="studio_status":
                return {**dict.fromkeys(BUSY_KEYS),"processing":run if submitted else None}
            if name=="library_song_files":
                return {"audio":str(self.source)}
            if name=="karaoke_settings_get":
                return {"provider":"whisper","enabled":True,"ready":True,"download":None,
                        "models":[{"id":"crisperwhisper-turbo","installed":True}]}
            if name=="lyrics_recognise":
                return {"provider":"whisper","text":"one two three"}
            raise AssertionError(name)
        client.call.side_effect=call
        def acoustic(source,target):
            return {"arms":{"A":self.a,"B":{**self.a,"sha256":_sha(target),
                       "integrated_lufs":-17.0,"true_peak_dbtp":-1.2}}}
        d=self.root/"direct-native"
        with patch("yue2_music_director.native_process.Client") as process_client, \
             patch("yue2_music_director.native_recognition.Client") as recognition_client, \
             patch("yue2_music_director.native_process.compare",side_effect=acoustic), \
             patch("yue2_music_director.native_process.shutil.which",return_value="ffmpeg"):
            process_client.return_value.connect.return_value=client
            recognition_client.return_value.connect.return_value=client
            preview(self.source,"fixture","naturalize",0.2,d,"http://127.0.0.1:1234/mcp",
                    confirm=True,lyrics=self.lyrics,baseline_asr=self.baseline,language="en",confirm_recognition=True)
        count=client.call.call_count
        result=self.run_selection(native=d)
        self.assertEqual(result["status"],"provisional_candidate")
        self.assertEqual(result["candidates"][0]["method"],"native_direct_preview")
        self.assertEqual(result["recognition_calls"],0)
        self.assertEqual(client.call.call_count,count)
        self.assertEqual(Path(result["provisional_output"]),d/"preview.flac")
