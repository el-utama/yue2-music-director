"""Offline, reproducible pilot index for the bundled rights-reviewed scores.

No network access, embeddings, model calls or native Studio operations.
The database is a disposable derived index; source assets remain immutable.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from contextlib import closing

SCHEMA = "knowledge-index-v2"
SOURCE_REV = "38c5db510224d9facdc4b08d741fc788cfb58ea8"
MAX_ASSET = 2_000_000
MAX_XML = 8_000_000


def asset(root, item, *, external=False):
    name = item["file"]
    if not isinstance(name, str):
        raise ValueError("Invalid asset name")
    if external:
        if name != item["source_path"] or not name.startswith("scores/Schubert,_Franz/Winterreise,_D.911/"):
            raise ValueError("Invalid external corpus path")
        if any(piece in ("", ".", "..") for piece in name.split("/")) or chr(92) in name:
            raise ValueError("Invalid external corpus path")
    elif not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
        raise ValueError("Invalid asset name")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > MAX_ASSET:
        raise ValueError("Missing or oversized corpus asset")
    data = path.read_bytes()
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if digest != item["git_blob_sha"]:
        raise ValueError("Corpus asset checksum mismatch: " + name)
    return data


def score_features(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = [x for x in archive.infolist() if x.filename.lower().endswith((".xml", ".musicxml"))
                 and not x.filename.startswith("META-INF/")]
        if len(files) != 1 or files[0].file_size > MAX_XML:
            raise ValueError("Unsupported compressed MusicXML layout")
        raw = archive.read(files[0])
    if b"<!ENTITY" in raw.upper():
        raise ValueError("XML entity declarations are not supported")
    root = ET.fromstring(raw)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    if root.tag != "score-partwise":
        raise ValueError("Expected partwise MusicXML")
    parts = root.findall("part")
    if not parts:
        raise ValueError("No score parts")
    vocal = [p for p in parts if p.findall(".//lyric/text")]
    pitches = []
    syllables = Counter()
    note_count = 0
    intervals = Counter()
    rest_count = 0
    key_signatures = set()
    for part in vocal:
        previous = None
        for note in part.findall(".//note"):
            if note.find("rest") is not None:
                rest_count += 1
                previous = None
            if note.find("lyric/text") is not None:
                note_count += 1
            for lyric in note.findall("lyric"):
                if lyric.find("text") is not None:
                    syllables[lyric.findtext("syllabic") or "unspecified"] += 1
            p = note.find("pitch")
            if p is not None:
                steps = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
                alter = float(p.findtext("alter", "0"))
                pitch = 12 * (int(p.findtext("octave")) + 1) + steps[p.findtext("step")] + alter
                pitches.append(pitch)
                if note.find("chord") is None:
                    if previous is not None:
                        delta = pitch - previous
                        intervals["repeat" if delta == 0 else "step" if abs(delta) <= 2 else "leap"] += 1
                        intervals["ascending" if delta > 0 else "descending" if delta < 0 else "level"] += 1
                    previous = pitch
        for key in part.findall(".//key"):
            fifths = key.findtext("fifths")
            if fifths is not None:
                key_signatures.add(fifths + ":" + (key.findtext("mode") or "unspecified"))
    meters = sorted({t.findtext("beats", "?") + "/" + t.findtext("beat-type", "?")
                     for t in root.findall(".//time")})
    return {"parts": len(parts), "lyric_bearing_parts": len(vocal),
            "notated_measures_max_part": max(len(p.findall("measure")) for p in parts),
            "lyric_bearing_notes": note_count, "syllabic_tags": dict(syllables),
            "vocal_pitch_range_semitones": max(pitches)-min(pitches) if pitches else None,
            "meters": meters, "key_signatures_fifths_mode": sorted(key_signatures),
            "notated_vocal_rest_events": rest_count, "notated_melodic_intervals": dict(intervals)}


def records(root, *, external_root=None):
    root = Path(root).resolve()
    manifest = json.loads((root / ("winterreise-full.json" if external_root else "manifest.json")).read_text(encoding="utf-8"))
    asset_root = Path(external_root).resolve() if external_root else root
    source = manifest["source"]
    if (manifest["schema"] != "knowledge-bank-v1" or source["revision"] != SOURCE_REV
            or source["repository"] != "https://github.com/OpenScore/Lieder"
            or source["license"] != "CC0-1.0"):
        raise ValueError("Unreviewed corpus source")
    seen, scores = set(), set()
    work_rows = [(w, asset_root, external_root is not None) for w in manifest["works"]]
    if external_root:
        bundled = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        work_rows += [(w, root, False) for w in bundled["works"] if not w["work_id"].startswith("schubert-d911-")]
    for work, row_root, external in work_rows:
        key = work["work_id"]
        if work["rights"] != "approved_public_domain_cc0":
            raise ValueError("Unapproved work: " + key)
        if key in seen or work["assets"]["score"]["git_blob_sha"] in scores:
            raise ValueError("Duplicate work or score")
        seen.add(key)
        scores.add(work["assets"]["score"]["git_blob_sha"])
        lyrics = asset(row_root, work["assets"]["lyrics"], external=external).decode("utf-8")
        harmony = asset(row_root, work["assets"]["harmony"], external=external).decode("utf-8")
        features = score_features(asset(row_root, work["assets"]["score"], external=external))
        if not lyrics.strip() or not harmony.strip() or not features["lyric_bearing_notes"]:
            raise ValueError("Missing expected lyric or harmony evidence: " + key)
        words = re.findall(r"[^\W_]+", lyrics.casefold(), re.UNICODE)
        features["text_words"] = len(words)
        features["unique_text_words"] = len(set(words))
        features["lexical_type_token_ratio"] = round(len(set(words)) / len(words), 4) if words else None
        features["harmony_annotated_measure_lines"] = len(re.findall(r"^m\d+", harmony, re.M))
        metadata = {k: work[k] for k in ("work_id", "title", "composer", "lyricist", "language", "genre",
                                        "published_year", "rights")}
        metadata["source_revision"] = SOURCE_REV
        metadata["assets"] = work["assets"]
        yield metadata, lyrics, harmony, features


def build(root, database, *, external_root=None):
    """Rebuild the derived index atomically; failed imports keep the old index."""
    rows = list(records(root, external_root=external_root))
    if not rows:
        raise ValueError("Empty corpus")
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=database.parent) as temp:
        path = Path(temp) / "index.sqlite"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE meta (schema TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES (?)", (SCHEMA,))
            db.execute("CREATE TABLE works (id TEXT PRIMARY KEY, metadata TEXT NOT NULL, features TEXT NOT NULL)")
            db.execute("CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, metadata, lyrics, harmony, score, tokenize='unicode61')")
            for meta, lyrics, harmony, features in rows:
                key = meta["work_id"]
                db.execute("INSERT INTO works VALUES (?, ?, ?)", (key, json.dumps(meta, ensure_ascii=False),
                                                                json.dumps(features, ensure_ascii=False)))
                searchable = " ".join(str(meta[k]) for k in ("title", "composer", "lyricist", "language", "genre"))
                db.execute("INSERT INTO search VALUES (?, ?, ?, ?, ?)",
                           (key, searchable, lyrics, harmony, json.dumps(features, ensure_ascii=False)))
        path.replace(database)
    return {"schema": SCHEMA, "unique_works": len(rows), "lyric_assets": len(rows),
            "score_assets": len(rows), "automatic_harmony_assets": len(rows),
            "languages": dict(Counter(m["language"] for m, *_ in rows)),
            "genres": dict(Counter(m["genre"] for m, *_ in rows))}


def retrieve(database, query, role, limit=5):
    if role not in ("lyricist", "composer") or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Invalid retrieval role or limit")
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("Query must be at most 500 characters")
    tokens = re.findall(r"[^\W_]+", query, re.UNICODE)
    if not tokens or len(tokens) > 30:
        raise ValueError("Query needs 1–30 search terms")
    columns = "{metadata lyrics}" if role == "lyricist" else "{metadata harmony score}"
    match = columns + " : (" + " OR ".join('"' + t + '"' for t in tokens) + ")"
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        if db.execute("SELECT schema FROM meta").fetchone() != (SCHEMA,):
            raise ValueError("Unsupported knowledge index")
        hits = db.execute("SELECT works.metadata, works.features FROM search JOIN works ON works.id=search.id "
                          "WHERE search MATCH ? ORDER BY bm25(search), works.id LIMIT ?", (match, limit))
        return [{"work": json.loads(m), "features": json.loads(f)} for m, f in hits]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--search")
    parser.add_argument("--role", choices=("lyricist", "composer"), default="lyricist")
    parser.add_argument("--source-dir", type=Path, help="Offline extracted pinned OpenScore checkout for full Winterreise")
    args = parser.parse_args()
    if args.source_dir is not None and not args.build:
        parser.error("--source-dir requires --build")
    db = args.repo / "local" / "knowledge-bank.sqlite"
    try:
        result = (build(args.repo / "data" / "knowledge_bank", db, external_root=args.source_dir) if args.build
                  else retrieve(db, args.search, args.role))
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, ET.ParseError, zipfile.BadZipFile) as exc:
        parser.exit(1, "Knowledge bank: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
