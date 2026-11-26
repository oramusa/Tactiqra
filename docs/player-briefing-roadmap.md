# CoachIQ — Player Briefing (V2.8 proposed)
Goal: translate an approved CoachIQ tactical plan into clear player-facing instructions, not a new independent analysis engine.

## MVP
1. Select a CoachIQ scenario and phase, snapshot the approved formation, player roles, movements, zones, objectives and selected evidence.
2. Team briefing: match objective, in-possession, out-of-possession, transition, set pieces.
3. Individual briefing: position, assigned player, starting location, movement, trigger, responsibility, fallback instruction. Coach edits and approves each instruction.
4. Presentation mode: full-screen pitch, step-by-step tactical playback, pause/replay, coach-controlled navigation.
5. Export printable team and individual briefing; no real messaging or player accounts in first release.
6. Keep analyst evidence separate from player-facing instructions. Never invent player assignments or claim causal certainty. Clearly label historical data and incomplete evidence.
7. Store versioned briefing snapshots separately from editable tactical plans; mark outdated snapshots after plan changes. No automatic publication.

## Sequence
- V2.8.1 briefing snapshot and approval model
- V2.8.2 team presentation
- V2.8.3 individual role cards
- V2.8.4 animated tactical walkthrough
- V2.8.5 printable export and validation

Dependencies: V2.7 tactical comparison and strategy generator, CoachIQ plan model, verified evidence transfer. Existing V2.6 validation remains a release gate. No production changes.
