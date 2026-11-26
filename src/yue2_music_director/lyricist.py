"""Original songwriting and text diagnostics, separate from music conditioning."""
from .creative_contracts import fields
from .prosody import parse_lyrics, estimate_syllables

PROMPT = ("Write original sung lyrics in the specified language, based on the request and musical concept. "
          "Use concrete narrative detail, coherent perspective, earned emotion and natural singable phrasing. "
          "Avoid generic filler, forced rhyme and copying existing songs. Use standalone [Verse], [Chorus], "
          "[Bridge] tags and actual repeated lyrics where appropriate. No production cues within sung lines. "
          "Return only JSON with a lyrics string.")


def validate(value):
    fields(value, {"lyrics":20000})
    groups=parse_lyrics(value["lyrics"])
    count=sum(len(g["lines"]) for g in groups)
    if not 1<=count<=120 or len(groups)>24 or any(len(s)>200 for g in groups for s in g["lines"]):
        raise ValueError("Invalid lyric structure or size")
    return value


def diagnostics(lyrics, language):
    return [{"section":g["name"],"occurrence":g["occurrence"],"lines":len(g["lines"]),
             "rough_english_syllables":[estimate_syllables(s) for s in g["lines"]] if language=="en" else None}
            for g in parse_lyrics(lyrics)]
