"""Read and query the original offline style recipes (not song references)."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import tempfile

GENRES = ("blues", "jazz", "lofi", "pop", "indie", "folk", "backsound", "hiphop", "lofihop", "trap")
SCHEMA = "original-style-library-v1"

def load(root):
    rows = []
    for genre in GENRES:
        path = Path(root) / (genre + ".jsonl")
        group = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(group) != 100:
            raise ValueError("Expected 100 style recipes for " + genre)
        for n, row in enumerate(group, 1):
            if (row["id"] != f"{genre}-{n:03d}" or row["genre"] != genre
                or row["kind"] != "original_style_recipe" or row["reference_track"] is not None
                or row["lyrics"] is not None or row["validation"] != "not_rendered"
                or not isinstance(row["style"], str) or not 10 <= len(row["style"]) <= 500):
                raise ValueError("Invalid style recipe")
        rows.extend(group)
    if len({r["id"] for r in rows}) != 1000 or len({r["style"] for r in rows}) != 1000:
        raise ValueError("Duplicate style recipes")
    return rows

def build(root, database):
    rows = load(root)
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=database.parent) as temp:
        path = Path(temp) / "style.sqlite"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE meta(schema TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES (?)", (SCHEMA,))
            db.execute("CREATE TABLE styles(id TEXT PRIMARY KEY, genre TEXT NOT NULL, record TEXT NOT NULL)")
            db.execute("CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, style, tokenize='unicode61')")
            for row in rows:
                db.execute("INSERT INTO styles VALUES (?, ?, ?)", (row["id"], row["genre"], json.dumps(row, ensure_ascii=False)))
                db.execute("INSERT INTO search VALUES (?, ?)", (row["id"], row["style"]))
        path.replace(database)
    return {"schema": SCHEMA, "original_recipes": len(rows),
            "by_genre": dict(Counter(r["genre"] for r in rows)), "real_track_references": 0, "lyrics": 0}

def search(database, genre, query=None, limit=10):
    if genre not in GENRES or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Invalid genre or limit")
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        if db.execute("SELECT schema FROM meta").fetchone() != (SCHEMA,):
            raise ValueError("Invalid style index")
        if query is None:
            rows = db.execute("SELECT record FROM styles WHERE genre=? ORDER BY id LIMIT ?", (genre, limit))
        else:
            terms = re.findall(r"[^\W_]+", query)
            if not terms or len(terms) > 20 or len(query) > 300:
                raise ValueError("Invalid search query")
            match = " AND ".join('"' + term + '"' for term in terms)
            rows = db.execute("SELECT styles.record FROM search JOIN styles ON styles.id=search.id WHERE search MATCH ? AND styles.genre=? ORDER BY bm25(search), styles.id LIMIT ?", (match, genre, limit))
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
    db = a.repo / "local" / "style-library.sqlite"
    try:
        output = build(a.repo / "data/style_library", db) if a.build else search(db, a.genre, a.search, a.limit)
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        p.exit(1, str(exc) + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
