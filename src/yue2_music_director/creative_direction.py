"""Versioned musical direction guidance for new autonomous jobs only."""
from .prosody import parse_lyrics

PREVIOUS_POLICY="reviewed-score-v2"
POLICY="reviewed-score-v3"
OPENINGS=("instrumental_intro","direct_vocal")
TIMING_GUIDANCE={"version":"opening-timing-v1","guidance":"Direct vocal allows a short breath or pickup of at most two seconds on the score clock. An instrumental intro should be purposeful and vocal-free, with notated instrumental activity where supported, followed by a prompt vocal entry (within two seconds of the end of the intro). Do not invent instrumental notes or claim acoustic timing from notation. Longer intentional silence is outside this default opening policy and requires separate review."}
VOICES=("male","female","duet","mixed","androgynous")
GUIDANCE={
    "version":"opening-vocal-v1",
    "composer":"Start performance with exactly three separate lines: Opening: instrumental_intro OR Opening: direct_vocal (choose one); Vocal: male/female/duet/mixed/androgynous (choose one); Narrator: a short description of perspective. Continue with concrete opening rationale, vocal character and arrangement progression. Prefer a brief purposeful instrumental introduction when it serves the story, not by formula; choose direct_vocal when intentional. Explicit user requirements take priority. Singer identity and narrator are separate: do not infer singer gender from the protagonist alone. Include the chosen vocal identity and timbre in the positive English style. Budget intro, transitions, contrast and closure within the target score duration.",
    "lyricist":"Follow the opening decision in composition.performance. For instrumental_intro start with a standalone [Intro] tag containing no sung lines, then the first sung section. For direct_vocal start immediately with a sung section (no intro tag). Preserve narrator perspective. Use concrete concise lyrics, meaningful development and an intentional final phrase. Do not sing production directions.",
    "reviewer":"Check opening decision against lyric structure, narrator perspective against story, chosen vocalist against style and explicit user requirements; assess whether the opening and closure serve this particular song. Stop unresolved mandatory requirements. Do not assume gender from story subject."
}


def parse_direction(composition):
    lines=composition["performance"].splitlines()
    if len(lines)<4:
        raise ValueError("Composer direction needs opening, vocalist, narrator and musical rationale")
    prefixes=("Opening: ","Vocal: ","Narrator: ")
    if any(not line.startswith(prefix) for line,prefix in zip(lines,prefixes)):
        raise ValueError("Composer direction headers missing or out of order")
    opening=lines[0][len(prefixes[0]):].strip()
    vocal=lines[1][len(prefixes[1]):].strip()
    narrator=lines[2][len(prefixes[2]):].strip()
    if opening not in OPENINGS or vocal not in VOICES or not narrator or not any(x.strip() for x in lines[3:]):
        raise ValueError("Invalid Composer opening/vocal direction")
    return {"opening":opening,"vocal":vocal,"narrator":narrator}


def validate_opening(composition,lyrics):
    direction=parse_direction(composition)
    groups=parse_lyrics(lyrics)
    first=groups[0]
    if direction["opening"]=="instrumental_intro":
        if first["name"]!="intro" or first["lines"] or len(groups)<2 or not groups[1]["lines"]:
            raise ValueError("Planned instrumental intro requires an empty opening [Intro] followed by sung lyrics")
    elif first["name"] in ("intro","interlude") or not first["lines"]:
        raise ValueError("Planned direct vocal requires an opening sung section")
    return direction
