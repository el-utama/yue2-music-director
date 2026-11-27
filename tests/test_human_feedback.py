import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import human_feedback as hf, native_draft as nd


class HumanFeedbackTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo=Path(tmp.name)
        audio=self.repo/"fixture.flac"
        audio.write_bytes(b"synthetic original")
        self.source={"job":"one","audio":audio,"result":{"audio_sha256":nd._sha(audio)},
                     "evidence":{"result_sha256":"retained-result"}}
        self.key=hf.identity(self.source)
        self.payload={"kind":"listening","ratings":dict.fromkeys(hf.DIMENSIONS,"good"),
                      "observations":"Fixture listener","confirmed_preferences":["Soft vocals"],
                      "inferred_preferences":["May prefer folk"]}
        self.approve={"kind":"release_approval","release":"release-one","decision":"approve","note":""}
        self.load=self.enterContext(patch.object(hf,"load",return_value=self.source))
        self.ledger=self.repo/"results/feedback/one"

    def test_plan_only_and_append_only(self):
        self.assertEqual(hf.launch(self.repo,"one"),0)
        self.assertFalse(self.ledger.exists())
        with self.assertRaisesRegex(ValueError,"listening feedback"):
            hf.append(self.repo,"one",self.key,self.approve)
        first=hf.append(self.repo,"one",self.key,self.payload)
        path=self.ledger/"000001.json"
        before=path.read_bytes()
        second=hf.append(self.repo,"one",self.key,self.approve)
        self.assertEqual(first["sequence"],1)
        self.assertEqual(second["previous_sha256"],nd._sha(path))
        self.assertEqual(path.read_bytes(),before)
        status=hf.status(self.repo,self.source)
        self.assertEqual(status["release_approvals"],{"release-one":True})
        self.assertFalse(status["automatic_acceptance"])
        self.assertFalse(status["publishing_authorized"])
        hf.append(self.repo,"one",self.key,{**self.approve,"decision":"revoke"})
        self.assertEqual(hf.status(self.repo,self.source)["release_approvals"],{"release-one":False})
        self.assertEqual(path.read_bytes(),before)

    def test_changed_audio_cannot_inherit_feedback(self):
        hf.append(self.repo,"one",self.key,self.payload)
        hf.append(self.repo,"one",self.key,self.approve)
        audio=self.source["audio"]
        audio.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"source changed"):
            hf.append(self.repo,"one",self.key,self.payload)
        changed={**self.source,"result":{"audio_sha256":nd._sha(audio)}}
        self.load.return_value=changed
        state=hf.status(self.repo,changed)
        self.assertEqual(state["release_approvals"],{})
        self.assertEqual(state["listening"],[])
        self.assertEqual(state["other_source_records"],2)
        with self.assertRaisesRegex(ValueError,"source changed"):
            hf.append(self.repo,"one",self.key,self.payload)

    def test_import_exact_source_and_explicit_approval(self):
        supplied=self.repo/"feedback.json"
        nd.atomic_write(supplied,{"source":self.key,"payload":self.payload})
        with self.assertRaisesRegex(ValueError,"confirm-run"):
            hf.launch(self.repo,"one",record=supplied)
        self.assertEqual(hf.launch(self.repo,"one",confirm=True,record=supplied),0)
        with patch("builtins.input",return_value="no"):
            with self.assertRaisesRegex(ValueError,"No approval"):
                hf.launch(self.repo,"one",confirm=True,approve="release-one")
        with patch("builtins.input",return_value="APPROVE"):
            self.assertEqual(hf.launch(self.repo,"one",confirm=True,approve="release-one"),0)
        self.assertTrue(hf.status(self.repo,self.source)["release_approvals"]["release-one"])

    def test_partial_or_tampered_ledger_refused(self):
        hf.append(self.repo,"one",self.key,self.payload)
        hf.append(self.repo,"one",self.key,self.approve)
        path=self.ledger/"000001.json"
        record=nd.read(path)
        record["payload"]["observations"]="changed"
        nd.atomic_write(path,record)
        with self.assertRaisesRegex(ValueError,"ledger identity"):
            hf.status(self.repo,self.source)
        with self.assertRaises(ValueError):
            hf.append(self.repo,"one",self.key,self.payload)

