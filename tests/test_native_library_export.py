import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from yue2_music_director import native_library_export as nl, native_collection as nc, release_export as ex, native_draft as nd
from test_release_export import URL


class NativeLibraryExportTests(unittest.TestCase):
    def test_plain_lyrics_mixed_formats_and_instrumental(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            audio=repo/"song.wav"
            audio.write_bytes(b"synthetic")
            instrumental=repo/"instrumental.mp3"
            instrumental.write_bytes(b"synthetic second")
            records={
                "s1":{"id":"s1","title":"Plain Song","lyrics":"First line\n\nSecond line","lrc":"[00:01.00]First line\n[00:03.00]Second line","active_version":None,"updated_at":1,"audio_path":"song.wav"},
                "s2":{"id":"s2","title":"Instrumental","lyrics":"[Instrumental]","lrc":None,"active_version":None,"updated_at":1,"audio_path":"instrumental.mp3"}}
            with patch.object(nl,"Client"),patch.object(nl,"duration",return_value=6.0),patch.object(nl,"read_song",side_effect=lambda u,j:records[j]),patch.object(nl,"file_for",side_effect=lambda c,j:audio if j=="s1" else instrumental):
                self.assertEqual(ex.launch(repo,"native",[],URL,kind="playlist",title="Mixed",native_songs=["s1","s2"],confirm=True),0)
                root=repo/"results/exports/playlists/Mixed--native"
                self.assertEqual((root/"playlist.m3u8").read_bytes(),b"#EXTM3U\n01 - Plain Song/01 - Plain Song.wav\n02 - Instrumental/02 - Instrumental.mp3\n")
                self.assertEqual((root/"01 - Plain Song/01 - Plain Song.clean.txt").read_bytes(),b"First line\n\nSecond line\n")
                self.assertTrue((root/"01 - Plain Song/01 - Plain Song.srt").is_file())
                self.assertFalse((root/"02 - Instrumental/02 - Instrumental.clean.txt").exists())
                manifest=nd.read(root/"release.json")
                self.assertEqual(manifest["contract"]["source_policy"],"native-library-draft-v1")
                self.assertEqual(manifest["tracks"][1]["timing"]["status"],"not_applicable")
                self.assertFalse(manifest["release_approved"])

    def test_library_collection_without_director_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            audio=repo/"song.flac"
            audio.write_bytes(b"synthetic")
            snap={"id":"s1","title":"Song","lyrics":"Hello","lrc":None}
            selection={"id":"album","name":"Album","kind":"album","song_ids":["s1"]}
            with patch.object(nc,"collection",return_value=selection),patch.object(nl,"Client"),patch.object(nl,"duration",return_value=10.0),patch.object(nl,"read_song",return_value=snap),patch.object(nl,"file_for",return_value=audio):
                self.assertEqual(ex.launch(repo,"album",[],URL,native_collection="album",library_only=True,confirm=True),2)
                root=repo/"results/exports/albums/Album--album"
                self.assertTrue((root/"01 - Song/01 - Song.flac").is_file())
                self.assertEqual(nd.read(root/"release.json")["status"],"partial_missing_timing")
                self.assertFalse((repo/"results/autonomous").exists())

    def test_native_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            audio=repo/"song.flac"
            audio.write_bytes(b"synthetic")
            snap={"id":"s","title":"Song","lyrics":"Hello","lrc":None}
            with patch.object(nl,"Client"),patch.object(nl,"duration",return_value=4.0),patch.object(nl,"read_song",side_effect=[snap,snap,{**snap,"title":"Changed"}]),patch.object(nl,"file_for",return_value=audio):
                with self.assertRaisesRegex(ValueError,"changed during export"):
                    ex.launch(repo,"changed",[],URL,native_songs=["s"],confirm=True,preset="distribution")
            self.assertFalse((repo/"results/exports/songs/Song--changed").exists())
