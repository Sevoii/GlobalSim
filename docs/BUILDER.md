# UmaBuilder

Load an existing runner with `UmaBuilder.from_json(json_text)`. It also accepts
UTF-8 JSON bytes or a decoded dictionary. `builder.to_json()` returns indented
JSON for the built runner (accepted by `from_json`), so it requires stats,
strategy, and aptitudes to be set. `str(builder)` / `print(builder)` shows a
readable summary instead and works on incomplete builders:

```python
builder = UmaBuilder.from_json(json_text)
builder.mood(2)
runner = builder.build()
print(builder)
saved = builder.to_json()
```

```text
Oguri Cap (#1006)
  Strategy   Late Surger
  Mood       Great (+2)
  Stats      Speed 1540  Stamina 406  Power 1229  Guts 733  Wit 1213
  Aptitudes  Distance S  Surface A  Strategy A
  Skills     2
    Triumphant Pulse        #100061     Lv5  unique
    Professor of Curvature  #200331     Lv1
```

`Skill` and `Uma` members also have a `.label` property with the display name,
e.g. `Skill.CORNER_ADEPT_CIRCLE.label == 'Corner Adept ○'`.

Import preserves extra runner and skill fields and validates known character
and skill IDs against the bundled enums. Missing mood defaults to `0`; missing
skills default to an empty list. Repeated skill IDs follow the builder's existing
replacement behavior. Missing required fields and invalid values raise errors.

Install GlobalSim using `python -m pip install .` or `maturin develop`.
The generated enums provide IDE completion for 70 characters and 1,431 skill IDs
from the uma-tools Global dataset. Provenance is recorded in
[CATALOG-SOURCES.md](../python/globalsim/CATALOG-SOURCES.md), with the upstream license
alongside it in `python/globalsim/uma-tools-LICENSE`.
Names shared by multiple skill IDs have ID suffixes (including unique/inherited
versions); choose the specific variant you want. Grade markers are spelled out:
`○` → `_CIRCLE`, `◎` → `_DOUBLE_CIRCLE`, `×` (negative variant) → `_CROSS`, e.g.
`Skill.CORNER_ADEPT_CIRCLE` vs `Skill.CORNER_ADEPT_CROSS`.

```python
from globalsim import Aptitude, Skill, Strategy, Uma, UmaBuilder

runner = (UmaBuilder(Uma.SPECIAL_WEEK)
          .stats(speed=1200, stamina=900, power=1000, guts=400, wisdom=600)
          .strategy(Strategy.LATE_SURGER)
          .aptitudes(distance=Aptitude.A, surface=Aptitude.A, strategy=Aptitude.A)
          .skill(Skill.SHOOTING_STAR_100011, level=3, unique=True)
          .mood(2)
          .build())

horse_json = runner.to_dict()
# Supply runner to RaceRequest.horses, or horse_json in a request dictionary.
```

The builder requires trained stats, strategy, and race-relevant aptitudes.
Character identity sets `charaId`; it does not infer outfit, stats, skills, or
aptitudes. Skills are explicit, with repeated IDs replacing the previous level.
Each build returns independent skill data. Skills in the catalog are not
necessarily supported by every GlobalSim skill-table version.

### Inherited uniques

Add a parent's unique skill with `inherit()`, passing the parent's unique:

```python
runner = (UmaBuilder(Uma.SPECIAL_WEEK)
          ...
          .skill(Skill.SHOOTING_STAR_100011, level=3, unique=True)   # own unique
          .inherit(Skill.AD_ASTRA_101051)                            # -> #901051
          .build())
```

`inherit()` adds the inherited version (the unique's ID with a leading `9`) at
level 1, not marked unique, since inherited uniques don't level up. It also accepts
the inherited member itself, and rejects non-unique skills and the runner's own
unique. On the enum, `Skill.X.inherited`, `.is_inherited`, and `.unique` convert
between the two. `print(builder)` labels inherited skills even where the catalog
gives both versions the same name (e.g. "Ad Astra").

The bundled skill table only defines inherited versions of the older (5- and
6-digit) uniques. Inherited versions of newer outfit uniques (9-digit IDs such as
`Skill.ABOVE_THE_CLOUDLINE.inherited`, #901302211) have no definition in any table
in this repository or in uma-tools, so `RaceBuilder.build()` rejects them unless
you supply a `skill_data()` table that defines them.

## RaceBuilder and Champions Meeting presets

Pick a course by track, surface, and distance, or start from a Global Champions
Meeting preset, then add runners and build a `RaceRequest`:

```python
from globalsim import (ChampionsMeeting, Ground, Layout, PreparedRace, RaceBuilder,
                       Season, Surface, Track, Weather)

race = (RaceBuilder(Track.KYOTO, Surface.TURF, 1600, layout=Layout.OUTER)
        .ground(Ground.GOOD).weather(Weather.CLOUDY).season(Season.AUTUMN)
        .seed(42)
        .runners([uma_builder, other_runner])
        .build())

cm = RaceBuilder.champions_meeting(ChampionsMeeting.TAURUS_CUP).seed(1).runner(uma_builder)
print(cm)
with PreparedRace(cm.build()) as prepared:
    replay = prepared.run_wire(1)
```

```text
Taurus Cup (2025-08-21)
  Course      Tokyo Turf 2400m (Medium, left-handed) #10606
  Conditions  Firm, Sunny, Spring, Midday, G1
  Seed        1
  Runners     1
    1. Special Week (Late Surger)
```

- `Course.find(track, surface, distance, layout=None)` returns the one matching
  course. When several match (e.g. Kyoto turf 1600m inner/outer) it raises and
  lists the course IDs; pass `layout=`, or use `RaceBuilder.from_course(course_id)`.
  `Course.all()` lists every course; each has `category` (sprint/mile/medium/long),
  `layout`, and `turn`.
- **Ground uses Global names.** `Ground.FIRM` and `Ground.GOOD` are sent to the
  engine as its JP-derived `'Good'` and `'Yielding'`, so `ground()` only accepts
  `Ground` members, not strings.
- Defaults are Firm, Sunny, Spring, Midday, G1. A seed and at least one runner are
  required. `UmaBuilder`s are built when added, so later edits don't affect the race.
- **Skills must exist in the race's skill table.** The engine silently ignores a
  skill ID its table doesn't define (the race is identical to one without that
  skill), so `build()` raises and lists them instead. The enum covers the whole
  uma-tools catalog, but the bundled `data/skill_data.json` lacks 338 of its skills
  (mostly inherited variants of uniques, plus scenario/event skills). Check with
  `Skill.X.in_bundled_table`, supply another table with
  `.skill_data(json.load(open('data/v70-skill-data.json')))` (sent as `skillData`;
  checks then use that table), inspect `builder.unknown_skills()`, or opt out with
  `build(allow_unknown_skills=True)`. Skills that are in the table but whose
  conditions the engine can't build are also dropped by the engine; that can only be
  detected by running it.
- `ChampionsMeeting` has every Global CM from uma-tools (repeat cups are `_2`).
  `RacePreset.champions_meeting(cm)` and `RacePreset.all_champions_meetings()`
  expose the date, course, and conditions.
- `Track` names come from uma-tools; the three overseas tracks it doesn't name are
  `Track.TRACK_10201`, `TRACK_10202`, and `TRACK_10203`. The course table is
  generated from the engine's `data/course_data.json`, so every course ID is one the
  engine knows.

## Testing and regeneration

Run `python -m unittest tests.test_builder tests.test_enums tests.test_race -v` to test.
`python tools/generate_catalog.py` refreshes `enums.py` and `courses.py` from upstream and records
its commit (`--pinned` regenerates from the recorded commit instead); review
generated changes before committing. `tests/test_enums.py` checks enum structure
and naming offline; set `GLOBALSIM_ENUM_UPSTREAM=1` (or `GLOBALSIM_ENUM_SOURCE` to a
directory holding `skillnames.json`, `umas.json`, `tracknames.json`, and `app.tsx`) to also compare IDs, labels,
and an exact re-render against the pinned uma-tools commit. No network access is needed to use the
resulting enums or builders. New CMs appear upstream regularly; regenerate to pick them up.
