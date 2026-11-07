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
[CATALOG-SOURCES.md](../python/globalsim/CATALOG-SOURCES.md), with the upstream license in `docs/uma-tools-LICENSE`.
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

Run `python -m unittest tests.test_builder tests.test_enums -v` to test.
`python tools/generate_catalog.py` refreshes the catalog from upstream and records
its commit (`--pinned` regenerates from the recorded commit instead); review
generated changes before committing. `tests/test_enums.py` checks enum structure
and naming offline; set `GLOBALSIM_ENUM_UPSTREAM=1` (or `GLOBALSIM_ENUM_SOURCE` to a
directory holding `skillnames.json` and `umas.json`) to also compare IDs, labels,
and an exact re-render against the pinned uma-tools commit. No network access is needed to use the resulting enums or builder.
