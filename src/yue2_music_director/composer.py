"""YuE2-specific style and musical concept role."""
from .creative_contracts import fields

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


def validate(value):
    return fields(value, {"title":150,"concept":2000,"emotional_arc":2000,"performance":2000,"style":2000})
