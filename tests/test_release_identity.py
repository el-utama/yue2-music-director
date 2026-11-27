import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_release_export import fixture, LRC, URL
from yue2_music_director import release_export as ex, release_identity as ri, native_draft as nd


class ReleaseIdentityTests(unittest.TestCase):
    def test_portable_names_and_path_lengths(self):
        for title in ("CON","nul.txt","Prn","COM1","LPT9.","COM¹.test","CONIN$"):
            self.assertTrue(ri.safe_title(title).startswith("_"),title)
        self.assertEqual(ri.safe_title('a<b>c:d"e/f\\g|h?i*j'),"a_b_c_d_e_f_g_h_i_j")
        self.assertLessEqual(len(ri.safe_title("🎵"*80).encode("utf-8")),56)
        with self.assertRaisesRegex(ValueError,"component length"):
            ri.ensure_paths([Path("x"*256)])
        with self.assertRaisesRegex(ValueError,"Windows length"):
            ri.ensure_paths([Path("x"*200)/("y"*100)],windows=True)

    def test_same_id_cannot_change_title_type_order_or_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]):
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:LRC),0)
                root=repo/"results/exports/songs/one--release"
                before={p:nd._sha(p) for p in root.rglob("*") if p.is_file()}
                for release,jobs,kwargs in (
                    ("release",["one"],{"title":"Other title"}),
                    ("release",["two"],{}),
                    ("release",["one","two"],{"title":"Album","kind":"album"}),
                    ("RELEASE",["one"],{})):
                    with self.subTest(kwargs=kwargs,release=release),self.assertRaises(ValueError):
                        ex.launch(repo,release,jobs,URL,confirm=True,timing_reader=lambda *a:self.fail("native read"),**kwargs)
                self.assertEqual(before,{p:nd._sha(p) for p in root.rglob("*") if p.is_file()})
                self.assertTrue((repo/"results/exports/.release-index/release/identity.json").is_file())

    def test_legacy_export_discovery_without_registry_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            track=fixture(repo,"one")
            with patch.object(ex,"retained",return_value=track):
                ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:LRC)
                exports=repo/"results/exports"
                index=exports/".release-index/release/identity.json"
                # Synthetic legacy migration fixture: old manifests have no index.
                index.unlink()
                root=exports/"songs/one--release"
                before=nd._sha(root/"release.json")
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:self.fail("repeat read")),0)
                self.assertFalse(index.exists())
                with self.assertRaises(ValueError):
                    ex.launch(repo,"release",["one"],URL,title="Changed",confirm=True,timing_reader=lambda *a:self.fail("read"))
                self.assertEqual(before,nd._sha(root/"release.json"))

    def test_partial_to_complete_explicit_revision_preserves_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            track=fixture(repo,"one")
            with patch.object(ex,"retained",return_value=track):
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:None),2)
                base=repo/"results/exports/songs/one--release"
                before={p:nd._sha(p) for p in base.rglob("*") if p.is_file()}
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:self.fail("repeat read")),2)
                self.assertEqual(ex.launch(repo,"release",["one"],URL,snapshot="v2",confirm=True,timing_reader=lambda *a:LRC),0)
                revision=repo/"results/exports/revisions/release/v2"
                manifest=nd.read(revision/"release.json")
                self.assertEqual(manifest["contract"]["base_release_manifest_sha256"],before[base/"release.json"])
                self.assertEqual(manifest["status"],"complete")
                self.assertTrue((revision/"one.srt").exists())
                self.assertEqual(before,{p:nd._sha(p) for p in base.rglob("*") if p.is_file()})
                self.assertEqual(ex.launch(repo,"release",["one"],URL,snapshot="v2",confirm=True,timing_reader=lambda *a:self.fail("repeat revision")),0)
                with self.assertRaises(ValueError):
                    ex.launch(repo,"release",["one"],URL,snapshot="V2",confirm=True,timing_reader=lambda *a:self.fail("case collision"))
                with self.assertRaises(ValueError):
                    ex.launch(repo,"missing",["one"],URL,snapshot="v2",confirm=True,timing_reader=lambda *a:self.fail("missing v1"))

    def test_reserved_title_actual_single_and_duplicate_album_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            for track in tracks.values():
                track["brief"]["title"]="CON"
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]):
                self.assertEqual(ex.launch(repo,"one",["one"],URL,confirm=True,timing_reader=lambda *a:LRC),0)
                root=repo/"results/exports/songs/_CON--one"
                self.assertTrue((root/"_CON.flac").is_file())
                self.assertEqual(ex.launch(repo,"album",["one","two"],URL,kind="album",title="NUL",
                                          confirm=True,timing_reader=lambda *a:LRC),0)
                root=repo/"results/exports/albums/_NUL--album"
                self.assertTrue((root/"01 - _CON/01 - _CON.flac").exists())
                self.assertTrue((root/"02 - _CON/02 - _CON.flac").exists())

    def test_interruption_reserves_id_without_publishing_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            track=fixture(repo,"one")
            write=Path.write_bytes
            def fail(path,data):
                if path.suffix==".srt":
                    raise OSError("disk failure")
                return write(path,data)
            with patch.object(ex,"retained",return_value=track):
                with patch.object(Path,"write_bytes",fail),self.assertRaises(OSError):
                    ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:LRC)
                exports=repo/"results/exports"
                self.assertFalse((exports/"songs/one--release").exists())
                self.assertTrue((exports/".release-index/release/identity.json").is_file())
                with self.assertRaises(ValueError):
                    ex.launch(repo,"release",["one"],URL,title="Different",confirm=True,timing_reader=lambda *a:self.fail("read"))
                self.assertEqual(ex.launch(repo,"release",["one"],URL,confirm=True,timing_reader=lambda *a:LRC),0)
