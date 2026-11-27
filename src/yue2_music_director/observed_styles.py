"""Offline index of observed music metadata, distinct from authored style recipes."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from .style_library import GENRES

SCHEMA = "observed-style-metadata-v4"

def load(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (root / "incompetech.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if manifest["schema"] != "observed-style-metadata-v1":
        raise ValueError("Invalid reference schema")
    ids = set()
    for row in rows:
        if (row["category"] not in GENRES or row["id"] in ids
                or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", row["isrc"])
                or row["id"] != "incompetech-" + row["isrc"]
                or row["artist"] != manifest["author"]
                or row["source_snapshot"] != manifest["metadata_snapshot"]["revision"]
                or row["source_url"] != "https://incompetech.com/music/royalty-free/index.html?isrc=" + row["isrc"]
                or row["rights_status"] != "catalog_reports_cc_by_4_0_individual_review_pending"
                or row["lyrics"] is not None or row["lyrics_status"] != "not_supplied"
                or row["validation"] != "metadata_only_not_listened"):
            raise ValueError("Invalid or duplicate reference")
        ids.add(row["id"])
    counts = {g: sum(row["category"] == g for row in rows) for g in GENRES}
    if counts != manifest["counts"] or len(rows) != manifest["distinct_tracks"]:
        raise ValueError("Reference inventory mismatch")
    clip_manifest = json.loads((root / "musiccaps-manifest.json").read_text(encoding="utf-8"))
    clips = [json.loads(line) for line in (root / "musiccaps.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if clip_manifest["schema"] != "musiccaps-style-annotations-v1" or clip_manifest["license"] != "CC-BY-SA-4.0":
        raise ValueError("Invalid annotation manifest")
    clip_counts = {g: 0 for g in GENRES}
    for row in clips:
        if (row["category"] not in GENRES or row["id"] in ids
                or not re.fullmatch(r"[A-Za-z0-9_-]{11}", row["youtube_id"])
                or row["id"] != "musiccaps-" + row["youtube_id"]
                or row["source_url"] != "https://www.youtube.com/watch?v=" + row["youtube_id"]
                or row["source_snapshot"] != clip_manifest["snapshot"]["revision"]
                or row["metadata_license"] != "CC-BY-SA-4.0"
                or row["rights_status"] != "annotation_licensed_recording_unreviewed"
                or row["lyrics"] is not None or row["lyrics_status"] != "not_supplied"
                or row["validation"] != "source_annotation_not_independently_listened"
                or not 0 <= row["start_seconds"] < row["end_seconds"]
                or not (row["genre_evidence"]["audioset_label"] or row["genre_evidence"]["annotation_keyword_match"])):
            raise ValueError("Invalid or duplicate annotation reference")
        ids.add(row["id"])
        clip_counts[row["category"]] += 1
    if clip_counts != clip_manifest["counts"] or len(clips) != clip_manifest["distinct_clips"]:
        raise ValueError("Annotation inventory mismatch")
    rows += clips
    counts = {g: counts[g] + clip_counts[g] for g in GENRES}
    if counts != clip_manifest["combined_candidates"] or any(n > 100 for n in counts.values()):
        raise ValueError("Combined inventory mismatch")
    curated_manifest = json.loads((root / "curated-manifest.json").read_text(encoding="utf-8"))
    curated = [json.loads(line) for line in (root / "curated.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if curated_manifest["schema"] != "curated-style-candidates-v1":
        raise ValueError("Invalid curated manifest")
    observed_counts = Counter()
    for row in curated:
        source = next((s for s in curated_manifest["sources"] if s["revision"] == row["source_snapshot"]), None)
        if (source is None or row["category"] != source["category"] or row["id"] in ids
                or not row["source_url"].startswith("https://")
                or not row["title"] or not row["artist"]
                or row["lyrics"] is not None or row["lyrics_status"] != "not_supplied"
                or row["validation"] != "metadata_only_not_listened"
                or row["reported_license"] not in ("CC0-1.0", "CC-BY-4.0")
                or row["rights_status"] not in ("playlist_reports_license_individual_review_pending", "creator_claims_cc0_ai_origin_unreviewed")):
            raise ValueError("Invalid curated candidate")
        if row["category"] == "lofihop" and (row["metadata_origin"] != "creator_catalog_disclosed_suno_v5" or row["rights_status"] != "creator_claims_cc0_ai_origin_unreviewed"):
            raise ValueError("AI origin must be explicit")
        observed_counts[row["source_snapshot"]] += 1
        ids.add(row["id"])
        counts[row["category"]] += 1
    if any(observed_counts[s["revision"]] != s["count"] for s in curated_manifest["sources"]):
        raise ValueError("Curated source count mismatch")
    rows += curated
    if counts != curated_manifest["counts"] or len(rows) != curated_manifest["distinct_candidate_ids"] or any(n > 100 for n in counts.values()):
        raise ValueError("Curated combined count mismatch")
    album_manifest = json.loads((root / "fma-albums-manifest.json").read_text(encoding="utf-8"))
    album_rows = [json.loads(line) for line in (root / "fma-albums.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if album_manifest["schema"] != "fma-album-candidates-v1":
        raise ValueError("Invalid FMA album manifest")
    album_counts = Counter()
    # Compare known artist/title pairs in addition to source-specific identifiers.
    def identity(row):
        return re.sub(r"[^a-z0-9]", "", (row.get("artist", "") + " " + row.get("title", "")).lower())
    known = {identity(row) for row in rows if row.get("artist") and row.get("title")}
    for row in album_rows:
        source = next((s for s in album_manifest["sources"] if s["id"] == row["source_id"]), None)
        if (source is None or row["category"] != source["category"] or row["id"] in ids
                or row["source_url"] != source["url"]
                or row["artist"] != source["artist"]
                or row["source_snapshot"] != album_manifest["snapshot"]
                or row["metadata_origin"] != "fma_album_catalog"
                or row["reported_license"] != "CC0-1.0"
                or row["rights_status"] != "album_reports_cc0_track_review_pending"
                or row["validation"] != "metadata_only_not_listened"
                or row["lyrics"] is not None or row["lyrics_status"] != "not_supplied"
                or not row["title"] or identity(row) in known):
            raise ValueError("Invalid or duplicate FMA album candidate")
        known.add(identity(row))
        ids.add(row["id"])
        album_counts[row["source_id"]] += 1
        counts[row["category"]] += 1
    if any(album_counts[s["id"]] != s["count"] for s in album_manifest["sources"]):
        raise ValueError("FMA album count mismatch")
    rows += album_rows
    if counts != album_manifest["counts"] or len(rows) != album_manifest["distinct_candidate_ids"] or any(n > 100 for n in counts.values()):
        raise ValueError("FMA combined count mismatch")
    return rows, counts

def build(root, database):
    rows, counts = load(root)
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=database.parent) as temp:
        path = Path(temp) / "references.sqlite"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE meta(schema TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES (?)", (SCHEMA,))
            db.execute("CREATE TABLE refs(id TEXT PRIMARY KEY, category TEXT NOT NULL, record TEXT NOT NULL)")
            db.execute("CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, metadata, tokenize='unicode61')")
            for row in rows:
                db.execute("INSERT INTO refs VALUES (?, ?, ?)", (row["id"], row["category"], json.dumps(row, ensure_ascii=False)))
                text = " ".join(str(row.get(key) or "") for key in ("title", "artist", "source_genre", "collection", "reported_bpm", "reported_instruments", "reported_moods", "annotation_tags"))
                db.execute("INSERT INTO search VALUES (?, ?)", (row["id"], text))
        path.replace(database)
    return {"metadata_candidates": len(rows), "by_category": counts,
            "track_metadata": sum("isrc" in row for row in rows),
            "annotated_clips": sum("youtube_id" in row for row in rows),
            "curated_track_candidates": sum(row.get("metadata_origin") == "third_party_playlist_manifest" for row in rows),
            "disclosed_ai_track_candidates": sum(row.get("metadata_origin") == "creator_catalog_disclosed_suno_v5" for row in rows),
            "fma_album_candidates": sum(row.get("metadata_origin") == "fma_album_catalog" for row in rows),
            "rights_reviewed_tracks": 0, "lyrics": 0,
            "missing_metadata_to_100": {g: max(0, 100-n) for g,n in counts.items()}}

def search(database, category, query=None, limit=10):
    if category not in GENRES or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Invalid reference category or limit")
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        if db.execute("SELECT schema FROM meta").fetchone() != (SCHEMA,):
            raise ValueError("Invalid reference index")
        if query is None:
            rows = db.execute("SELECT record FROM refs WHERE category=? ORDER BY id LIMIT ?", (category, limit))
        else:
            terms = re.findall(r"[^\W_]+", query)
            if not terms or len(terms) > 20 or len(query) > 300:
                raise ValueError("Invalid query")
            match = " AND ".join('"' + term + '"' for term in terms)
            rows = db.execute("SELECT refs.record FROM search JOIN refs ON refs.id=search.id WHERE search MATCH ? AND refs.category=? ORDER BY bm25(search), refs.id LIMIT ?", (match, category, limit))
        return [json.loads(row[0]) for row in rows]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path.cwd())
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--genre", choices=GENRES)
    p.add_argument("--search")
    p.add_argument("--limit", type=int, default=10)
    a = p.parse_args()
    db = a.repo / "local" / "observed-style.sqlite"
    try:
        result = build(a.repo / "data/observed_styles", db) if a.build else search(db, a.genre, a.search, a.limit)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        p.exit(1, str(exc) + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
