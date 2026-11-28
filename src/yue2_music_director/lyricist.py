"""Original songwriting and text diagnostics, separate from music conditioning."""
import re
import unicodedata

from .creative_contracts import fields, object_schema
from .prosody import parse_lyrics, estimate_syllables

PROMPT = ("Write original sung lyrics in the specified language, based on the request and musical concept. "
          "Use concrete narrative detail, coherent perspective, earned emotion and natural singable phrasing. "
          "Avoid generic filler, forced rhyme and copying existing songs. Use standalone [Verse], [Chorus], "
          "[Bridge] tags and actual repeated lyrics where appropriate. No production cues within sung lines. "
          "Return only JSON with a lyrics string.")


LIMITS = {"lyrics":20000}
SCHEMA = object_schema(LIMITS)


def validate(value):
    fields(value, LIMITS)
    groups=parse_lyrics(value["lyrics"])
    count=sum(len(g["lines"]) for g in groups)
    if not 1<=count<=120 or len(groups)>24 or any(len(s)>200 for g in groups for s in g["lines"]):
        raise ValueError("Invalid lyric structure or size")
    return value


COMPACT_FORM = "compact-form-v1"
TARGET_DURATION = 180
ENDING_ALLOWANCE = 10
DEFAULT_DURATION = TARGET_DURATION + ENDING_ALLOWANCE
FORM_GUIDANCE = {
    "preferred_sections": ["[Intro]", "[Verse 1]", "[Pre-Chorus]", "[Chorus]",
                           "[Verse 2]", "[Bridge]", "[Instrumental Break]", "[Outro]"],
    "composer": ("Choose a form that fits the brief and duration budget. The section list is a "
                 "preference. Shorten, combine or omit sections as needed. An explicit opening, "
                 "supplied lyrics or typed section plan takes priority. Describe what closes the "
                 "song, when the last sung phrase ends, and what the instruments do after it."),
    "lyricist": ("Write from the narrator's particular situation. Let a gesture, object, action "
                 "or change of mind carry the emotion. Give the second verse a new beat. Read "
                 "each line aloud and revise stock images, filler and syntax bent to force a rhyme. "
                 "Keep the break and any instrumental outro empty of words or stage directions. "
                 "A sung refrain may return when the brief or story gives it a purpose."),
    "reviewer": ("Check the ending against the request and composition. Compare the final chorus "
                 "and outro, including repeated closing lines. A deliberate hook can work. "
                 "For generated words, identify a specific line or section when stock imagery, "
                 "empty restatement or forced rhyme undermines the song. Stop an unresolved "
                 "editorial problem before synthesis and explain the needed edit. Short forms "
                 "are acceptable. Respect exact supplied lyrics."),
}


def _line_key(line):
    normalized = unicodedata.normalize("NFKC", line).casefold().replace("’", "'")
    return tuple(re.findall(r"[^\W_]+(?:'[^\W_]+)*", normalized))


def diagnostics(lyrics, language, *, compact_form=False):
    groups = parse_lyrics(lyrics)
    rows = [{"section":g["name"],"occurrence":g["occurrence"],"lines":len(g["lines"]),
             "rough_english_syllables":[estimate_syllables(s) for s in g["lines"]] if language=="en" else None}
            for g in groups]
    if compact_form and groups[-1]["name"] == "outro":
        from .music import native_section
        chorus = next((g for g in reversed(groups[:-1]) if native_section(g["name"]) == "chorus"), None)
        if chorus is not None:
            chorus_keys = {_line_key(line) for line in chorus["lines"]}
            rows[-1]["final_chorus_line_matches"] = [
                number for number, line in enumerate(groups[-1]["lines"], start=1)
                if (key := _line_key(line)) and key in chorus_keys
            ]
    return rows
