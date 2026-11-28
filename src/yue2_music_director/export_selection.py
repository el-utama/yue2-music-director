"""Deterministic human-readable native selection."""
import unicodedata


def normalize(value):
    return unicodedata.normalize("NFC",value.strip()).casefold()


def by_name(rows,name,field):
    if not isinstance(name,str) or not name.strip():
        raise ValueError("Provide a nonempty exact name")
    matches=[row for row in rows if normalize(row[field])==normalize(name)]
    if not matches:
        raise ValueError("No exact matching native name; use the list command")
    if len(matches)!=1:
        raise ValueError("Ambiguous native name; choose an exact ID: "+", ".join(row["id"] for row in matches))
    return matches[0]["id"]
