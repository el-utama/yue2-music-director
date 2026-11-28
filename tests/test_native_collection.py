import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import native_collection as nc, release_export as ex, native_draft as nd
from test_release_export import fixture, URL, LRC


def raw(kind="playlist"):
    return {"id":"native-id","name":"Evening Sessions","song_ids":["s2","s1"],
            "description":nc.ALBUM_PREFIX+"Notes" if kind=="album" else None}


class NativeCollectionTests(unittest.TestCase):
    def test_native_album_envelopes_and_list(self):
        self.assertEqual(nc.parse_collection(raw("album"))["kind"],"album")
        v={**raw(),"description":nc.COLLECTION_PREFIX+'{"kind":"album","coverUrl":"ignored"}'}
        self.assertEqual(nc.parse_collection(v)["kind"],"album")
        with patch.object(nc,"native_library_read",return_value=[v]) as read:
            self.assertEqual(nc.collections(URL),[{"id":"native-id","name":"Evening Sessions","kind":"album","tracks":2}])
            read.assert_called_once_with(URL,"/v1/library/playlists")
        for bad in (["s1","s1"],[]):
            with patch.object(nc,"native_library_read",return_value={**raw(),"song_ids":bad}):
                with self.assertRaises(ValueError):
                    nc.collection(URL,"native-id")

    def test_native_selection_export_preserves_exact_order_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            for j,song in (("one","s1"),("two","s2")):
                tracks[j]["result"]["song_id"]=song
                nd.atomic_write(repo/"results/autonomous"/j/"result.json",tracks[j]["result"])
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]),patch.object(nc,"native_library_read",return_value=raw()) as read:
                self.assertEqual(ex.launch(repo,"collection",[],URL,native_collection="native-id",confirm=True,timing_reader=lambda *a:LRC),0)
                root=repo/"results/exports/playlists/Evening Sessions--collection"
                self.assertEqual((root/"playlist.m3u8").read_bytes(),b"#EXTM3U\n01 - two/01 - two.flac\n02 - one/02 - one.flac\n")
                self.assertEqual(nd.read(root/"release.json")["contract"]["native_collection"]["song_ids"],["s2","s1"])
                self.assertEqual(read.call_count,2)
                self.assertEqual(ex.launch(repo,"collection",[],URL,native_collection="native-id",confirm=True,timing_reader=lambda *a:self.fail("repeat timing")),0)
                read.return_value={**raw(),"song_ids":["s1","s2"]}
                with self.assertRaises(ValueError):
                    ex.launch(repo,"collection",[],URL,native_collection="native-id",confirm=True)

    def test_missing_native_only_result_and_manual_playlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            with patch.object(nc,"native_library_read",return_value=raw()):
                with self.assertRaisesRegex(ValueError,"Studio-only"):
                    ex.launch(repo,"missing",[],URL,native_collection="native-id",confirm=True)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]):
                self.assertEqual(ex.launch(repo,"manual",["two","one"],URL,kind="playlist",title="Set",confirm=True,timing_reader=lambda *a:LRC),0)
                self.assertTrue((repo/"results/exports/playlists/Set--manual/playlist.m3u8").is_file())

    def test_collection_change_aborts_staged_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            tracks={j:fixture(repo,j) for j in ("one","two")}
            for j,song in (("one","s1"),("two","s2")):
                tracks[j]["result"]["song_id"]=song
                nd.atomic_write(repo/"results/autonomous"/j/"result.json",tracks[j]["result"])
            with patch.object(ex,"retained",side_effect=lambda r,j:tracks[j]),patch.object(nc,"native_library_read",side_effect=[raw(),{**raw(),"song_ids":["s1","s2"]}]):
                with self.assertRaisesRegex(ValueError,"changed during export"):
                    ex.launch(repo,"changed",[],URL,native_collection="native-id",confirm=True,timing_reader=lambda *a:LRC)
            self.assertFalse((repo/"results/exports/playlists/Evening Sessions--changed").exists())
