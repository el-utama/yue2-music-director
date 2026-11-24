"""Text comparison only; not verified pronunciation or ASR language support."""
import unicodedata as ud
from .prosody import parse_lyrics

WORD_LANGUAGES = {"en", "id", "fr", "de", "es", "it", "pt", "nl", "ar", "ru", "vi", "tr"}
CHAR_LANGUAGES = {"ja", "zh", "ko", "th"}
SUPPORTED = WORD_LANGUAGES | CHAR_LANGUAGES


def _normalized(text):
    return ud.normalize("NFC", ud.normalize("NFC", text).casefold()).replace("’", "'")


def _words(text):
    tokens, current = [], []
    for i,c in enumerate(text):
        category=ud.category(c)[0]
        if category in "LN" or (category=="M" and current):
            current.append(c)
        elif c=="'" and current and i+1<len(text) and ud.category(text[i+1])[0]=="L":
            current.append(c)
        elif current:
            tokens.append("".join(current))
            current=[]
    if current:
        tokens.append("".join(current))
    return tokens


def _chars(text):
    return [c for c in text if ud.category(c)[0] in "LNM"]


def distance(a,b):
    if not a or not b:
        raise ValueError("Nonempty reference and recognized text required")
    if max(len(a),len(b))>6000 or len(a)*len(b)>16000000:
        raise ValueError("Text exceeds edit-distance budget")
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):
            row.append(min(prev[j]+1,row[-1]+1,prev[j-1]+(x!=y)))
        prev=row
    return {"reference_units":len(a),"observed_units":len(b),
            "edits":prev[-1],"disagreement_rate":prev[-1]/len(a)}


def assess(lyrics, transcript, language):
    if language not in SUPPORTED:
        raise ValueError("Unsupported scoring language; no automatic ranking")
    ref=_normalized(" ".join(l for g in parse_lyrics(lyrics) for l in g["lines"]))
    obs=_normalized(transcript)
    result={"language":language,"CER":distance(_chars(ref),_chars(obs)),
            "primary_metric":"CER" if language in CHAR_LANGUAGES else "WER"}
    if language in WORD_LANGUAGES:
        result["WER"]=distance(_words(ref),_words(obs))
    return result


def compare(lyrics,a,b,language):
    arms={k:assess(lyrics,v,language) for k,v in (("source",a),("candidate",b))}
    metric=arms["source"]["primary_metric"]
    delta=arms["candidate"][metric]["edits"]-arms["source"][metric]["edits"]
    return {"schema":"multilingual-asr-screen-v1","arms":arms,"primary_metric":metric,
            "candidate_minus_source_edits":delta,
            "status":"regression" if delta>0 else "improved" if delta<0 else "unchanged",
            "warnings":["ASR text disagreement, not verified sung error rate.",
                        "CER counts normalized Unicode code points, not graphemes or phonemes.",
                        "Word tokenization is basic; no dictionary segmentation, romanization or script conversion.",
                        "Language is supplied by the operator; recognition language support is not established by scoring."]}
