"""Versioned structured Composer contract, selected only for explicit typed jobs."""
from . import composer
from .creative_contracts import fields, object_schema
from .typed_creative import validate_direction
from .creative_direction import OPENINGS, VOICES

PROMPT=("You are a musical direction specialist for local YuE2. "+composer.STYLE_GUIDE+
        " Treat typed_requirements as explicit operator requirements, not suggestions. "
        " Return JSON with title, concept, emotional_arc, performance, style strings and a direction object "
        " containing opening, vocal, narrator and ordered section_plan array of section/purpose objects. "
        "Performance is musical prose, not magic headers. Respect exact lyrics/style and requested section purposes. "
        "Singer identity is separate from narrator; no guarantees of acoustic voice identity. "
        "Use positive literal chosen vocal descriptors in style. Follow the typed guidance in the input.")
LIMITS=composer.LIMITS
SCHEMA=object_schema(LIMITS)
SCHEMA["properties"]["direction"]={"type":"object","properties":{
    "opening":{"type":"string","enum":list(OPENINGS)},
    "vocal":{"type":"string","enum":list(VOICES)},
    "narrator":{"type":"string"},
    "section_plan":{"type":"array","items":{"type":"object","properties":{"section":{"type":"string"},"purpose":{"type":"string"}},
                                            "required":["section","purpose"],"additionalProperties":False}}},
    "required":["opening","vocal","narrator","section_plan"],"additionalProperties":False}
SCHEMA["required"].append("direction")


def validate(value):
    if not isinstance(value,dict) or set(value)!=set(LIMITS)|{"direction"}:
        raise ValueError("Unexpected typed Composer fields")
    fields({k:value[k] for k in LIMITS},LIMITS)
    validate_direction(value["direction"])
    return value
