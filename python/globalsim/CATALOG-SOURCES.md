# Enum data provenance

Source: https://github.com/alpha123/uma-tools
Commit: `9c1d21ee4f2a1c02f8fb3684fa4ae428b124eda6`

Inputs: `umalator-global/skillnames.json` and `umalator-global/umas.json`. GPL-3.0 license is included alongside this file.
Enums contain character IDs, not outfit/card IDs. Duplicate normalized skill names have an ID suffix so no distinct skills become enum aliases.
The catalog may include skills beyond the engine snapshot; enum membership does not guarantee that a supplied simulation skill table supports a skill.
