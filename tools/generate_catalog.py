"""Generate readable enums from an uma-tools Global snapshot.

Writes python/globalsim/enums.py (skills, characters) and python/globalsim/courses.py
(tracks, the engine's course table, Champions Meeting presets), then js/src/catalog.ts
from those modules (generate_js_catalog.py). Course geometry IDs
come from the engine's own data/course_data.json; names and presets from uma-tools.

By default the latest upstream commit is used and recorded in CATALOG-SOURCES.md;
pass --commit SHA or --pinned to regenerate from a specific commit.
"""
import argparse
import json
from pathlib import Path
import re
import unicodedata
import urllib.request

import generate_js_catalog

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'python/globalsim'
ENGINE_COURSES = ROOT / 'data/course_data.json'
ENGINE_SKILLS = ROOT / 'data/skill_data.json'
REPO = 'alpha123/uma-tools'
# Grade markers carry meaning (○/◎ are buffs, × is the negative variant), so they
# must survive normalization instead of being dropped as non-ASCII.
MARKERS = {'○': 'CIRCLE', '◎': 'DOUBLE_CIRCLE', '×': 'CROSS'}
PRESET_LINE = re.compile(
    r"\{type: EventType\.CM, name: '([^']+)', date: '(\d{4}-\d{2}-\d{2})', courseId: (\d+), "
    r"season: Season\.(\w+), ground: GroundCondition\.(\w+), weather: Weather\.(\w+), "
    r"time: Time\.(\w+)\},?")


def fetch(url):
    with urllib.request.urlopen(url) as response:
        return response.read()


def raw_url(commit, path):
    return f'https://raw.githubusercontent.com/{REPO}/{commit}/{path}'


def latest_commit():
    return json.loads(fetch(f'https://api.github.com/repos/{REPO}/commits/master'))['sha']


def pinned_commit():
    text = (PACKAGE / 'CATALOG-SOURCES.md').read_text(encoding='utf-8')
    return re.search(r'Commit: `([0-9a-f]{40})`', text).group(1)


def load_sources(commit):
    skills = json.loads(fetch(raw_url(commit, 'umalator-global/skillnames.json')))
    umas = json.loads(fetch(raw_url(commit, 'umalator-global/umas.json')))
    return skills, umas


def load_course_sources(commit):
    tracks = json.loads(fetch(raw_url(commit, 'umalator-global/tracknames.json')))
    app = fetch(raw_url(commit, 'umalator/app.tsx')).decode('utf-8')
    return tracks, app


def engine_courses():
    return json.loads(ENGINE_COURSES.read_text(encoding='utf-8'))


def engine_skill_ids():
    """IDs defined by the engine's bundled (fallback) skill table."""
    return sorted(int(k) for k in json.loads(ENGINE_SKILLS.read_text(encoding='utf-8')))


def entries(skills, umas):
    """Map enum name -> [(id, label)] for each generated enum."""
    return {'Skill': [(int(k), v[0]) for k, v in skills.items()],
            'Uma': [(int(k), v['name'][1]) for k, v in umas.items()]}


def identifier(name):
    for glyph, word in MARKERS.items():
        name = name.replace(glyph, f' {word} ')
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub('[^A-Za-z0-9]+', '_', name).strip('_').upper()
    return name if name and not name[0].isdigit() else 'ID_' + name


def labelled_enum(category, items, base='IntEnum'):
    """Render an enum whose members carry a `.label` from a generated table."""
    lines = ['', '', f'class {category}({base}):']
    groups = {}
    for key, name in items:
        groups.setdefault(identifier(name), []).append((key, name))
    for name, group in sorted(groups.items()):
        for key, label in sorted(group):
            member = name if len(group) == 1 else f'{name}_{key}'
            lines.append(f'    {member} = {key!r}  # {label}')
    table = f'_{identifier(category)}_LABELS'
    lines += ['', '    @property', '    def label(self) -> str:',
              '        """Display name from uma-tools."""', f'        return {table}[self.value]']
    tables = ['', '', f'{table} = {{', *(f'    {key!r}: {label!r},' for key, label in sorted(items)), '}']
    return lines, tables


def render(skills, umas, bundled_skill_ids):
    lines = ['"""Generated from alpha123/uma-tools and data/skill_data.json; see CATALOG-SOURCES.md."""',
             'from enum import IntEnum']
    tables = []
    for category, items in entries(skills, umas).items():
        enum_lines, enum_tables = labelled_enum(category, items)
        if category == 'Skill':
            enum_lines += ['', '    @property', '    def in_bundled_table(self) -> bool:',
                           '        """Whether the bundled data/skill_data.json defines this skill.',
                           '',
                           '        The engine silently ignores skills missing from the table a race uses.',
                           '        """',
                           '        return self.value in _BUNDLED_SKILL_IDS',
                           '',
                           '    @property',
                           "    def inherited(self) -> 'Skill':",
                           '        """The inherited version of this unique (its ID with a leading 9 for the 1)."""',
                           '        text = str(self.value)',
                           "        if text[0] == '1' and int('9' + text[1:]) in _SKILL_LABELS:",
                           "            return Skill(int('9' + text[1:]))",
                           "        raise ValueError(f'{self.name} has no inherited version')",
                           '',
                           '    @property',
                           '    def is_inherited(self) -> bool:',
                           '        """Whether this is the inherited version of a unique."""',
                           '        text = str(self.value)',
                           "        return text[0] == '9' and int('1' + text[1:]) in _SKILL_LABELS",
                           '',
                           '    @property',
                           "    def unique(self) -> 'Skill':",
                           '        """The unique this inherited skill comes from."""',
                           '        if not self.is_inherited:',
                           "            raise ValueError(f'{self.name} is not an inherited skill')",
                           "        return Skill(int('1' + str(self.value)[1:]))"]
        lines += enum_lines
        tables += enum_tables
    ids = sorted(bundled_skill_ids)
    tables += ['', '', '# Skill IDs in the bundled (fallback) engine table, data/skill_data.json.',
               '_BUNDLED_SKILL_IDS = frozenset({',
               *('    ' + ', '.join(map(str, ids[i:i + 8])) + ',' for i in range(0, len(ids), 8)), '})']
    return '\n'.join(lines + tables) + '\n'


def global_presets(app):
    """Parse the Global Champions Meeting presets from umalator/app.tsx."""
    match = re.search(r'const presets = \(CC_GLOBAL \? \[(.*?)\n\] : \[', app, re.S)
    if not match:
        raise ValueError('Global preset block not found in umalator/app.tsx')
    presets = []
    for line in match[1].splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = PRESET_LINE.fullmatch(line)
        if not parsed:
            raise ValueError(f'Unrecognized Global preset line in umalator/app.tsx: {line}')
        name, date, course, *conditions = parsed.groups()
        presets.append((name, date, int(course), *conditions))
    return sorted(presets, key=lambda p: p[1])


def render_courses(courses, tracks, app):
    used = sorted({c['raceTrackId'] for c in courses.values()})
    names = [(t, tracks[str(t)][1] if str(t) in tracks else f'Track {t}') for t in used]
    lines = ['"""Generated from data/course_data.json and alpha123/uma-tools; see CATALOG-SOURCES.md."""',
             'from enum import Enum, IntEnum']
    track_lines, tables = labelled_enum('Track', names)
    lines += track_lines
    presets = global_presets(app)
    missing = [p for p in presets if str(p[2]) not in courses]
    if missing:
        raise ValueError(f'Presets reference courses the engine lacks: {missing}')
    cm_lines, cm_tables = labelled_enum('ChampionsMeeting', [(identifier(p[0]).lower(), p[0])
                                                             for p in presets], base='Enum')
    lines += cm_lines
    tables += cm_tables
    tables += ['', '', '# courseId: (raceTrackId, surface, distance, distanceType, course layout, turn)',
               '_COURSES = {', *(f"    {int(k)}: ({c['raceTrackId']}, {c['surface']}, {c['distance']}, "
                                 f"{c['distanceType']}, {c['course']}, {c['turn']}),"
                                 for k, c in sorted(courses.items(), key=lambda i: int(i[0]))), '}',
               '', '', '# Global Champions Meeting presets (uma-tools umalator/app.tsx); conditions use',
               "# the engine's JP-derived names, e.g. ground 'Good' is shown as Firm on Global.",
               '# value: (date, courseId, season, ground, weather, time)',
               '_CHAMPIONS_MEETINGS = {',
               *(f"    {identifier(p[0]).lower()!r}: {(p[1], *p[2:])!r}," for p in presets), '}']
    return '\n'.join(lines + tables) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', help='uma-tools commit SHA (default: latest master)')
    parser.add_argument('--pinned', action='store_true',
                        help='regenerate from the commit recorded in CATALOG-SOURCES.md')
    args = parser.parse_args()
    commit = pinned_commit() if args.pinned else args.commit or latest_commit()
    skills, umas = load_sources(commit)
    tracks, app = load_course_sources(commit)
    courses_text = render_courses(engine_courses(), tracks, app)
    (PACKAGE / 'enums.py').write_text(render(skills, umas, engine_skill_ids()), encoding='utf-8')
    (PACKAGE / 'courses.py').write_text(courses_text, encoding='utf-8')
    (PACKAGE / 'uma-tools-LICENSE').write_bytes(fetch(raw_url(commit, 'LICENSE')))
    (PACKAGE / 'CATALOG-SOURCES.md').write_text(
        f'# Enum data provenance\n\nSource: https://github.com/{REPO}\n'
        f'Commit: `{commit}`\n\nInputs: `umalator-global/skillnames.json`, '
        '`umalator-global/umas.json`, `umalator-global/tracknames.json`, and the Global '
        'presets in `umalator/app.tsx`. GPL-3.0 license is included alongside this file.\n'
        'Enums contain character IDs, not outfit/card IDs. Duplicate normalized skill '
        'names have an ID suffix so no distinct skills become enum aliases.\n'
        'The catalog may include skills beyond the engine snapshot; enum membership '
        'does not guarantee that a supplied simulation skill table supports a skill.\n'
        "`Skill.in_bundled_table` and the course table come from GlobalSim's "
        '`data/skill_data.json` and `data/course_data.json`; tracks without an upstream '
        'name are named by ID.\n', encoding='utf-8')
    generate_js_catalog.write()
    print(f'Generated {len(skills)} skills, {len(umas)} characters, '
          f'{len(engine_courses())} courses, and {len(global_presets(app))} presets at {commit}')


if __name__ == '__main__':
    main()
