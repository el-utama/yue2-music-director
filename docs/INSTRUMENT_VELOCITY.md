# Instrument velocity — first implementation

`instrument-velocity INPUT.mid --out NEW.mid --strength 12`

Only constant-velocity tracks explicitly named Ins, Instrument or Chords are eligible. Vocal tracks, already expressive tracks and drum-channel tracks are protected. The deterministic heuristic reduces weak/offbeat accents and shapes a four-bar contour; it is not a learned performance model. All changes are note-on velocity bytes; pitches, timing, note durations, programs and other MIDI bytes are preserved. Output never overwrites an existing file. Render using a velocity-sensitive instrument to hear the result.

This does not modify ABC or regenerate YuE2 audio. Upstream Studio revision ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25 advertises backing_song_id (native YuE2, existing instrumental library song, matching Chord bed ABC, lyrics, ready separator). Its backing_vocals.rs mixes extracted vocals over the existing backing and attenuates only the vocal as needed. This is a plausible separate production route for externally rendered humanized accompaniment, not proof that the local installed build supports it or that the original orchestration is recoverable from the exported two-line score. Check local capabilities and rendering instruments before implementation of this route. Never alter frozen A/B/C artifacts. No audio jobs are created by this command.
