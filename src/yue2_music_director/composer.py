"""YuE2-specific style and musical concept role."""
from .creative_contracts import fields, object_schema

# Independently summarized pinned Studio advice; see docs/CREATIVE_CORE.md.
STYLE_GUIDE = ("Use concise positive English sound descriptors (usually 12–50 words), "
               "vocal language first, coherent genre, concrete instrumental palette, "
               "vocal register and delivery, mood, groove and optional BPM at the end. "
               "Describe audible textures and contrast rather than instructions, negative "
               "prompts, quality slogans or artist-name imitation. Keep lyric tags out of style. "
               "Tempo and arrangement are preferences, not guarantees; native engine owns melody.")
PROMPT = ("You are a musical direction specialist for local YuE2. "+STYLE_GUIDE+
          " Develop concept and emotional progression, contrasting instrumental roles and "
          "performance direction. Return only JSON with title, concept, emotional_arc, performance, style strings.")


LIMITS = {"title":150,"concept":2000,"emotional_arc":2000,"performance":2000,"style":2000}
SCHEMA = object_schema(LIMITS)


def validate(value):
    return fields(value, LIMITS)


class Structured:
    """New default wire contract; retain canonical legacy-shaped musical prose.

    A fully valid legacy-format response remains acceptable for providers that
    do not enforce JSON schema. Never infer or fill missing artistic decisions.
    """
    PROMPT = ("You are a musical direction specialist for local YuE2. "+STYLE_GUIDE+
              " Return only JSON with title, concept, emotional_arc, performance, style, "
              "opening, vocal, narrator, musical_rationale strings. "
              "Opening is instrumental_intro or direct_vocal; vocal is male, female, "
              "duet, mixed or androgynous. Narrator is a single-line description of perspective. "
              "Explain why the opening and musical progression suit this story in musical_rationale. "
              "Performance is ordinary musical prose, not labelled headers. "
              "Separate vocalist identity from narrator and follow explicit user requirements. "
              "Follow the direction and timing guidance in the input.")
    LIMITS = {**LIMITS, "opening":32, "vocal":32, "narrator":300, "musical_rationale":1000}
    SCHEMA = object_schema(LIMITS, {"opening":("instrumental_intro","direct_vocal"),
                                   "vocal":("male","female","duet","mixed","androgynous")})

    @staticmethod
    def validate(value):
        from .creative_direction import parse_direction, OPENINGS, VOICES
        if isinstance(value,dict) and set(value)==set(LIMITS):
            # Retained canonical receipts and complete legacy-format responses.
            result=validate(value)
            parse_direction(result)
            return result
        fields(value, Structured.LIMITS)
        opening,vocal,narrator=(value[k].strip() for k in ("opening","vocal","narrator"))
        if opening not in OPENINGS:
            raise ValueError("Invalid structured Composer field: opening")
        if vocal not in VOICES:
            raise ValueError("Invalid structured Composer field: vocal")
        if len(narrator.splitlines())!=1:
            raise ValueError("Invalid structured Composer field: narrator")
        result={k:value[k] for k in LIMITS}
        result["performance"]="Opening: "+opening+"\nVocal: "+vocal+"\nNarrator: "+narrator+"\n"+value["performance"].strip()+"\nMusical rationale: "+value["musical_rationale"].strip()
        validate(result)
        parse_direction(result)
        return result
