"""Verify enums.py and courses.py are faithful renders of the pinned uma-tools snapshot.

The offline tests always run. The upstream comparison needs the uma-tools data at
the commit in CATALOG-SOURCES.md; enable it with either
  GLOBALSIM_ENUM_SOURCE=path/to/dir  (containing skillnames.json, umas.json,
                                      tracknames.json and app.tsx), or
  GLOBALSIM_ENUM_UPSTREAM=1          (fetch from GitHub).
"""
import ast
from collections import Counter
import importlib.util
import json
import keyword
import os
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import generate_catalog as gen  # noqa: E402

ENUMS = gen.PACKAGE / 'enums.py'
COURSES = gen.PACKAGE / 'courses.py'
MEMBER_LINE = re.compile(r"^    (\w+) = (\d+|'\w+')  # (.*)$")
CATEGORIES = ('Skill', 'Uma')


def load_module(path=ENUMS):
    # Load by path so the check doesn't require the native extension to be built.
    spec = importlib.util.spec_from_file_location(f'globalsim_{path.stem}_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_labels(path=ENUMS):
    """Map enum name -> {member: (value, label)} from the generated source comments."""
    result, current = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('class '):
            current = result.setdefault(line[6:].split('(')[0], {})
        elif (match := MEMBER_LINE.match(line)) and current is not None:
            value = match[2]
            current[match[1]] = (int(value) if value.isdigit() else ast.literal_eval(value), match[3])
    return result


def count_marker(tokens, word):
    parts = word.split('_')
    count = sum(tokens[i:i + len(parts)] == parts for i in range(len(tokens)))
    if word == 'CIRCLE':  # don't count the CIRCLE inside DOUBLE_CIRCLE
        count -= sum(tokens[i:i + 2] == ['DOUBLE', 'CIRCLE'] for i in range(len(tokens)))
    return count


class BundledSkillTableTests(unittest.TestCase):
    """Compare the Skill enum with the engine's saved table, data/skill_data.json.

    The upstream tests check the enum against uma-tools; only this checks it against
    the skill IDs the engine actually has. Catalog skills may be missing from the
    bundled table (they can come from a supplied skillData table), but the enum's
    record of which ones are present must be exact.
    """
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.engine_ids = set(gen.engine_skill_ids())

    def test_recorded_ids_match_data_file(self):
        self.assertEqual(set(self.module._BUNDLED_SKILL_IDS), self.engine_ids)

    def test_in_bundled_table_matches_data_file(self):
        mismatched = [s.name for s in self.module.Skill
                      if s.in_bundled_table != (s.value in self.engine_ids)]
        self.assertEqual(mismatched, [])

    def test_bundled_table_is_mostly_covered(self):
        # Guard against the enum and table drifting apart wholesale (e.g. a table
        # keyed by a different ID scheme); the known gap is inherited/scenario skills.
        missing = [s for s in self.module.Skill if not s.in_bundled_table]
        self.assertLess(len(missing), len(self.module.Skill) // 3, [s.name for s in missing[:20]])


class InheritedSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = load_module().Skill

    def test_uniques_and_inherited_versions_pair_one_to_one(self):
        pairs = {}
        for s in self.skill:
            try:
                pairs[s] = s.inherited
            except ValueError:
                continue
        inherited = [s for s in self.skill if s.is_inherited]
        self.assertEqual(sorted(pairs.values()), sorted(inherited))
        self.assertEqual(len(set(pairs.values())), len(pairs))
        for unique, inh in pairs.items():
            with self.subTest(unique=unique.name):
                self.assertIs(inh.unique, unique)
                self.assertEqual(str(inh.value), '9' + str(unique.value)[1:])
                self.assertFalse(unique.is_inherited)

    def test_non_uniques(self):
        for s in (self.skill.CORNER_ADEPT_CIRCLE, self.skill.UNQUENCHED_THIRST):
            with self.subTest(skill=s.name):
                self.assertFalse(s.is_inherited)
                with self.assertRaises(ValueError):
                    s.inherited
                with self.assertRaises(ValueError):
                    s.unique


class EnumStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.labels = parse_labels()

    def test_no_aliased_values(self):
        for name in CATEGORIES:
            enum = getattr(self.module, name)
            with self.subTest(enum=name):
                aliases = [m for m, v in enum.__members__.items() if v.name != m]
                self.assertEqual(aliases, [])

    def test_identifiers_are_upper_snake(self):
        for name in CATEGORIES:
            with self.subTest(enum=name):
                bad = [m for m in getattr(self.module, name).__members__
                       if not re.fullmatch(r'[A-Z][A-Z0-9_]*', m) or '__' in m or keyword.iskeyword(m)]
                self.assertEqual(bad, [])

    def test_every_member_has_matching_label(self):
        for name in CATEGORIES:
            members = getattr(self.module, name).__members__
            parsed = self.labels.get(name, {})
            with self.subTest(enum=name):
                self.assertEqual(set(members), set(parsed))
                self.assertEqual({m: int(v) for m, v in members.items()},
                                 {m: v for m, (v, _) in parsed.items()})


    def test_label_property_matches_comment_labels(self):
        for name in CATEGORIES:
            enum = getattr(self.module, name)
            with self.subTest(enum=name):
                self.assertEqual({m: v.label for m, v in enum.__members__.items()},
                                 {m: label for m, (_, label) in self.labels[name].items()})
                self.assertNotIn('label', enum.__members__)


class EnumNamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = parse_labels()

    def test_names_derive_from_labels_with_suffix_only_when_shared(self):
        for name, members in self.labels.items():
            bases = {m: gen.identifier(label) for m, (_, label) in members.items()}
            shared = Counter(bases.values())
            wrong = []
            for member, (value, label) in members.items():
                expected = bases[member] if shared[bases[member]] == 1 else f'{bases[member]}_{value}'
                if member != expected:
                    wrong.append(f'{member} = {value} ({label!r}) should be {expected}')
            with self.subTest(enum=name):
                self.assertEqual(wrong, [])

    def test_grade_markers_are_preserved(self):
        # ○/◎ are positive grades and × is the negative variant; dropping a marker
        # would give e.g. the debuff the plain, obvious-looking name.
        for name, members in self.labels.items():
            dropped = [f'{member} ({label!r}) drops {glyph}'
                       for member, (_, label) in members.items()
                       for glyph, word in gen.MARKERS.items()
                       if count_marker(member.split('_'), word) < label.count(glyph)]
            with self.subTest(enum=name):
                self.assertEqual(dropped, [])

    def test_negative_variants_are_distinct_from_positive(self):
        skill = load_module().Skill
        self.assertEqual(skill.CORNER_ADEPT_CIRCLE, 200332)
        self.assertEqual(skill.CORNER_ADEPT_CROSS, 200333)
        self.assertNotIn('CORNER_ADEPT', skill.__members__)


class CourseEnumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(COURSES)
        cls.labels = parse_labels(COURSES)

    def test_labels_match_comments_and_values_are_unique(self):
        for name in ('Track', 'ChampionsMeeting'):
            enum = getattr(self.module, name)
            with self.subTest(enum=name):
                self.assertEqual(len(enum.__members__), len(enum))
                self.assertEqual({m: (v.value, v.label) for m, v in enum.__members__.items()},
                                 self.labels[name])

    def test_tracks_cover_course_table(self):
        self.assertEqual({t.value for t in self.module.Track},
                         {c[0] for c in self.module._COURSES.values()})

    def test_every_preset_has_data_and_a_known_course(self):
        presets = self.module._CHAMPIONS_MEETINGS
        self.assertEqual({cm.value for cm in self.module.ChampionsMeeting}, set(presets))
        for key, (_, course_id, *_rest) in presets.items():
            with self.subTest(preset=key):
                self.assertIn(course_id, self.module._COURSES)


def upstream_sources():
    source = os.environ.get('GLOBALSIM_ENUM_SOURCE')
    if source:
        source = Path(source)
        return (json.loads((source / 'skillnames.json').read_text(encoding='utf-8')),
                json.loads((source / 'umas.json').read_text(encoding='utf-8')),
                json.loads((source / 'tracknames.json').read_text(encoding='utf-8')),
                (source / 'app.tsx').read_text(encoding='utf-8'))
    commit = gen.pinned_commit()
    return (*gen.load_sources(commit), *gen.load_course_sources(commit))


@unittest.skipUnless(os.environ.get('GLOBALSIM_ENUM_SOURCE') or os.environ.get('GLOBALSIM_ENUM_UPSTREAM'),
                     'set GLOBALSIM_ENUM_SOURCE or GLOBALSIM_ENUM_UPSTREAM=1 to compare with uma-tools')
class EnumUpstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skills, cls.umas, cls.tracks, cls.app = upstream_sources()
        cls.labels = parse_labels()

    def test_ids_and_labels_match_upstream(self):
        for name, items in gen.entries(self.skills, self.umas).items():
            local = {value: label for value, label in self.labels.get(name, {}).values()}
            with self.subTest(enum=name):
                self.assertEqual(sorted(local), sorted(dict(items)))
                self.assertEqual(local, dict(items))

    def test_file_is_exact_render_of_pinned_snapshot(self):
        self.maxDiff = 4000
        self.assertEqual(ENUMS.read_text(encoding='utf-8').splitlines(),
                         gen.render(self.skills, self.umas, gen.engine_skill_ids()).splitlines(),
                         'run: python tools/generate_catalog.py --pinned')

    def test_courses_file_is_exact_render_of_pinned_snapshot(self):
        self.maxDiff = 4000
        self.assertEqual(COURSES.read_text(encoding='utf-8').splitlines(),
                         gen.render_courses(gen.engine_courses(), self.tracks, self.app).splitlines(),
                         'run: python tools/generate_catalog.py --pinned')


if __name__ == '__main__':
    unittest.main()
