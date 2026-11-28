import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import export_selection as sel, export_acceptance as ea, release_export as ex, native_library_export as nl, native_collection as nc, native_draft as nd
from test_release_export import URL


class ExportSelectionAcceptanceTests(unittest.TestCase):
    def test_exact_unicode_names_and_ambiguity(self):
        rows=[{"id":"1","title":"Café at Midnight"},{"id":"2","title":"Другой мир"}]
        self.assertEqual(sel.by_name(rows," CAFE\u0301 AT MIDNIGHT ","title"),"1")
        self.assertEqual(sel.by_name(rows,"другой мир","title"),"2")
        with self.assertRaisesRegex(ValueError,"No exact"):
            sel.by_name(rows,"Café","title")
        with self.assertRaisesRegex(ValueError,"Ambiguous"):
            sel.by_name(rows+[{"id":"3","title":"CAFÉ AT MIDNIGHT"}],"Café at Midnight","title")

    def test_cli_name_selection_and_conflict(self):
        argv=["export","--repo",".","--url",URL,"--export","draft","--song-name","Café at Midnight"]
        with patch("sys.argv",argv),patch.object(nl,"song_list",return_value=[{"id":"native-id","title":"Café at Midnight"}]),patch.object(ex,"launch",return_value=0) as launch:
            self.assertEqual(ex.main(),0)
            self.assertEqual(launch.call_args.kwargs["native_songs"],["native-id"])
            self.assertFalse(launch.call_args.kwargs["confirm"])
        with patch("sys.argv",argv+["--native-song","other"]),patch.object(ex,"launch") as launch:
            self.assertEqual(ex.main(),2)
            launch.assert_not_called()

    def test_consolidated_native_sample_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            audio=repo/"source.flac"
            audio.write_bytes(b"synthetic audio")
            songs=[{"id":"a","title":"One"},{"id":"b","title":"Two"}]
            collections=[{"id":"album","name":"Album","kind":"album","tracks":2},
                         {"id":"playlist","name":"Playlist","kind":"playlist","tracks":2}]
            def collection(url,ident):
                return {"id":ident,"name":ident.title(),"kind":ident,"song_ids":["b","a"]}
            def song(url,ident):
                return {"id":ident,"title":ident,"lyrics":"Hello","lrc":"[00:01.00]Hello"}
            with patch.object(nl,"song_list",return_value=songs),patch.object(nc,"collections",return_value=collections),patch.object(nc,"collection",side_effect=collection),patch.object(nl,"Client"),patch.object(nl,"duration",return_value=5.0),patch.object(nl,"read_song",side_effect=song),patch.object(nl,"file_for",return_value=audio):
                self.assertEqual(ea.run(repo,URL,confirm=False,launch=ex.launch),0)
                self.assertFalse((repo/"results").exists())
                self.assertEqual(ea.run(repo,URL,confirm=True,launch=ex.launch),0)
                reports=list((repo/"results/export-check").glob("*/report.json"))
                self.assertEqual(len(reports),1)
                report=nd.read(reports[0])
                self.assertEqual(report["status"],"sample_checks_passed")
                self.assertEqual(len(report["outcomes"]),4)
                self.assertFalse(report["human_player_review"])
                self.assertEqual(audio.read_bytes(),b"synthetic audio")
                self.assertFalse((repo/"results/exports").exists())

    def test_no_collections_not_full_acceptance(self):
        with patch.object(nl,"song_list",return_value=[{"id":"a","title":"One"}]),patch.object(nc,"collections",return_value=[]):
            plan=ea.plan(URL)
            self.assertFalse(plan["native_album_available"])
            self.assertFalse(plan["native_playlist_available"])
            self.assertEqual([c["id"] for c in plan["cases"]],["single-video","album-manual","playlist-manual"])

    def test_acceptance_rejects_semantically_wrong_playlist_even_with_matching_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            audio=repo/"source.flac"
            audio.write_bytes(b"synthetic audio")
            def song(url,ident):
                return {"id":ident,"title":ident,"lyrics":"Hello","lrc":"[00:01.00]Hello"}
            with patch.object(nl,"Client"),patch.object(nl,"duration",return_value=5.0),patch.object(nl,"read_song",side_effect=song),patch.object(nl,"file_for",return_value=audio):
                self.assertEqual(ex.launch(repo,"playlist",[],URL,kind="playlist",title="Set",native_songs=["b","a"],preset="video",confirm=True),0)
                package=repo/"results/exports/playlists/Set--playlist"
                manifest=nd.read(package/"release.json")
                case={"kind":"playlist","preset":"video"}
                ea.verify_sample(package,manifest,case,["b","a"])
                (package/"playlist.m3u8").write_bytes(b"#EXTM3U\nwrong.flac\n")
                manifest["files"]["playlist.m3u8"]=nd._sha(package/"playlist.m3u8")
                nd.atomic_write(package/"release.json",manifest)
                with self.assertRaisesRegex(ValueError,"playlist order"):
                    ea.verify_sample(package,manifest,case,["b","a"])
