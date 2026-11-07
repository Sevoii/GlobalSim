from collections import Counter
from datetime import date
import json
from pathlib import Path
import unittest

from globalsim import (Aptitude, ChampionsMeeting, Course, DistanceCategory, Grade, Ground, Layout,
                       PreparedRace, RaceBuilder, RacePreset, RaceRequest, Season, Skill, Strategy, Surface,
                       Time, Track, Turn, Uma, UmaBuilder, Weather)

ENGINE_COURSES = json.loads((Path(__file__).resolve().parents[1] / 'data/course_data.json')
                            .read_text(encoding='utf-8'))


def uma(chara=Uma.SPECIAL_WEEK, strategy=Strategy.LATE_SURGER):
    return (UmaBuilder(chara)
            .stats(speed=1200, stamina=900, power=1000, guts=400, wisdom=600)
            .strategy(strategy)
            .aptitudes(distance=Aptitude.A, surface=Aptitude.A, strategy=Aptitude.A))


class CourseTableTests(unittest.TestCase):
    def test_table_matches_engine_course_data(self):
        self.assertEqual({c.id for c in Course.all()}, {int(k) for k in ENGINE_COURSES})
        for course in Course.all():
            raw = ENGINE_COURSES[str(course.id)]
            with self.subTest(course=course.id):
                self.assertEqual((course.track, course.surface, course.distance, course.category,
                                  course.layout, course.turn),
                                 (raw['raceTrackId'], raw['surface'], raw['distance'],
                                  raw['distanceType'], raw['course'], raw['turn']))

    def test_every_unambiguous_course_is_found_by_track_surface_distance(self):
        keys = Counter((c.track, c.surface, c.distance) for c in Course.all())
        for course in Course.all():
            key = (course.track, course.surface, course.distance)
            with self.subTest(course=course.id):
                if keys[key] == 1:
                    self.assertEqual(Course.find(*key), course)
                layouts = Counter(c.layout for c in Course.all()
                                  if (c.track, c.surface, c.distance) == key)
                if layouts[course.layout] == 1:
                    self.assertEqual(Course.find(*key, layout=course.layout), course)

    def test_get_rejects_unknown_ids(self):
        for bad in (0, 99999, '10606', 10606.0, True, None):
            with self.subTest(course_id=bad), self.assertRaises(ValueError):
                Course.get(bad)

    def test_find_errors(self):
        with self.assertRaisesRegex(ValueError, r'#10804 \(INNER\), #10805 \(OUTER\); pass layout='):
            Course.find(Track.KYOTO, Surface.TURF, 1600)
        with self.assertRaisesRegex(ValueError, r'#11612 .*#11615 .*from_course'):
            Course.find(Track.TRACK_10202, Surface.TURF, 2000)
        with self.assertRaisesRegex(ValueError, r'No Tokyo turf course of 1234m; available: .*2400m'):
            Course.find(Track.TOKYO, Surface.TURF, 1234)
        with self.assertRaisesRegex(ValueError, 'with layout OUTER'):
            Course.find(Track.TOKYO, Surface.TURF, 2400, layout=Layout.OUTER)
        with self.assertRaisesRegex(ValueError, 'No Track 10201 dirt course'):
            Course.find(Track.TRACK_10201, Surface.DIRT, 2400)
        for bad in (2400.0, '2400', True):
            with self.subTest(distance=bad), self.assertRaises(TypeError):
                Course.find(Track.TOKYO, Surface.TURF, bad)
        for args in ((1, Surface.TURF, 2400), (Track.TOKYO, 3, 2400)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Course.find(*args)
        with self.assertRaises(ValueError):
            Course.find(Track.KYOTO, Surface.TURF, 1600, layout=9)

    def test_find_accepts_raw_ids(self):
        self.assertEqual(Course.find(10006, 1, 2400).id, 10606)
        self.assertEqual(Course.find(Track.KYOTO, Surface.TURF, 1600, layout=2).id, 10804)

    def test_str(self):
        self.assertEqual(str(Course.get(10606)), 'Tokyo Turf 2400m (Medium, left-handed)')
        self.assertEqual(str(Course.get(10805)), 'Kyoto Turf 1600m outer (Mile, right-handed)')
        straight = [c for c in Course.all() if c.turn == Turn.STRAIGHT]
        self.assertTrue(straight and all('straight)' in str(c) for c in straight))
        to_inner = [c for c in Course.all() if c.layout == Layout.OUTER_TO_INNER]
        self.assertTrue(to_inner and all(' outer to inner ' in str(c) for c in to_inner))


class ChampionsMeetingTests(unittest.TestCase):
    def test_presets_are_valid_and_unique(self):
        presets = RacePreset.all_champions_meetings()
        self.assertEqual(len(presets), len(ChampionsMeeting))
        self.assertEqual(len({p.name for p in presets}), len(presets))
        self.assertEqual(len({p.date for p in presets}), len(presets))
        self.assertEqual([p.date for p in presets], sorted(p.date for p in presets))
        for p in presets:
            with self.subTest(preset=p.name):
                self.assertIsInstance(p.course, Course)
                self.assertIsInstance(p.ground, Ground)
                self.assertNotEqual(p.season, Season.SAKURA)

    def test_known_preset(self):
        p = RacePreset.champions_meeting(ChampionsMeeting.TAURUS_CUP)
        self.assertEqual((p.name, p.date, p.course.id, p.season, p.ground, p.weather, p.time),
                         ('Taurus Cup', date(2025, 8, 21), 10606, Season.SPRING, Ground.FIRM,
                          Weather.SUNNY, Time.MIDDAY))
        self.assertEqual(ChampionsMeeting.TAURUS_CUP.label, 'Taurus Cup')

    def test_preset_requires_member(self):
        for bad in ('taurus_cup', 'Taurus Cup', None):
            with self.subTest(cm=bad), self.assertRaises(TypeError):
                RacePreset.champions_meeting(bad)

    def test_builder_uses_preset_conditions(self):
        for cm in ChampionsMeeting:
            p = RacePreset.champions_meeting(cm)
            wire = RaceBuilder.champions_meeting(cm).seed(1).runner(uma()).build().to_dict()
            with self.subTest(cm=cm.name):
                self.assertEqual((wire['courseId'], wire['groundCondition'], wire['weather'],
                                  wire['season'], wire['time'], wire['grade']),
                                 (p.course.id, p.ground.value, p.weather.value, p.season.value,
                                  p.time.value, 'G1'))

    def test_every_preset_runs_in_the_engine(self):
        for cm in ChampionsMeeting:
            with self.subTest(cm=cm.name):
                request = RaceBuilder.champions_meeting(cm).seed(7).runner(uma()).build()
                with PreparedRace(request) as race:
                    self.assertTrue(race.run_wire(7))


class RaceBuilderTests(unittest.TestCase):
    def test_defaults_and_wire_format(self):
        request = RaceBuilder(Track.TOKYO, Surface.TURF, 2400).seed(5).runner(uma()).build()
        self.assertIsInstance(request, RaceRequest)
        wire = request.to_dict()
        self.assertEqual({k: v for k, v in wire.items() if k != 'horses'},
                         dict(seed=5, courseId=10606, groundCondition='Good', weather='Sunny',
                              season='Spring', time='Midday', grade='G1'))
        self.assertEqual(wire['horses'][0]['charaId'], 1001)

    def test_ground_uses_global_names(self):
        expected = {Ground.FIRM: 'Good', Ground.GOOD: 'Yielding', Ground.SOFT: 'Soft',
                    Ground.HEAVY: 'Heavy'}
        for ground, wire in expected.items():
            with self.subTest(ground=ground.name):
                request = RaceBuilder.from_course(10606).ground(ground).seed(1).runner(uma()).build()
                self.assertEqual(request.ground_condition, wire)
        for bad in ('Good', 'Firm', None):
            with self.subTest(ground=bad), self.assertRaises(TypeError):
                RaceBuilder.from_course(10606).ground(bad)

    def test_condition_setters(self):
        b = (RaceBuilder.from_course(Course.get(10606)).weather('Rainy').season(Season.AUTUMN)
             .time(Time.NIGHT).grade(Grade.PRE_OP).seed(1).runner(uma()))
        wire = b.build().to_dict()
        self.assertEqual((wire['weather'], wire['season'], wire['time'], wire['grade']),
                         ('Rainy', 'Autumn', 'Night', 'Pre-OP'))
        for setter, bad in (('weather', 'Foggy'), ('season', 'Fall'), ('time', 'Noon'), ('grade', 'G4')):
            with self.subTest(setter=setter), self.assertRaises(ValueError):
                getattr(b, setter)(bad)

    def test_seed_validation(self):
        for good in (0, -2 ** 63, 2 ** 63 - 1):
            self.assertEqual(RaceBuilder.from_course(10606).seed(good).runner(uma()).build().seed, good)
        for bad in (2 ** 63, -2 ** 63 - 1, 1.0, True, '1', None):
            with self.subTest(seed=bad), self.assertRaises(ValueError):
                RaceBuilder.from_course(10606).seed(bad)

    def test_build_requires_seed_and_runners(self):
        with self.assertRaisesRegex(ValueError, 'seed'):
            RaceBuilder.from_course(10606).runner(uma()).build()
        with self.assertRaisesRegex(ValueError, 'runner'):
            RaceBuilder.from_course(10606).seed(1).build()

    def test_runner_inputs(self):
        built = uma(Uma.OGURI_CAP).build()
        request = (RaceBuilder.from_course(10606).seed(1)
                   .runners([uma(), built]).runner(uma(Uma.GOLD_SHIP)).build())
        self.assertEqual([h.extra['charaId'] for h in request.horses], [1001, 1006, 1007])
        for bad in ({'speed': 1}, None, 'runner'):
            with self.subTest(runner=bad), self.assertRaises(TypeError):
                RaceBuilder.from_course(10606).runner(bad)

    def test_runners_are_snapshots(self):
        source, runner = uma(), uma().build()
        b = RaceBuilder.from_course(10606).seed(1).runner(source).runner(runner)
        source.strategy(Strategy.FRONT_RUNNER)
        runner.extra['mood'] = 2
        first = b.build()
        first.horses[0].speed = 1
        second = b.build()
        self.assertEqual(second.horses[0].strategy, 'Sasi')
        self.assertEqual(second.horses[1].extra['mood'], 0)
        self.assertEqual(second.horses[0].speed, 1200)

    def test_alternate_constructors_match(self):
        a = RaceBuilder(Track.KYOTO, Surface.TURF, 1600, layout=Layout.OUTER)
        self.assertEqual(a.course, RaceBuilder.from_course(10805).course)
        self.assertEqual(a.course.category, DistanceCategory.MILE)
        with self.assertRaises(ValueError):
            RaceBuilder(Track.KYOTO, Surface.TURF, 1600)
        with self.assertRaises(ValueError):
            RaceBuilder.from_course(1)

    def test_str(self):
        b = RaceBuilder.champions_meeting(ChampionsMeeting.TAURUS_CUP).seed(42).runners(
            [uma(), uma(Uma.OGURI_CAP, Strategy.FRONT_RUNNER)])
        self.assertEqual(str(b), '\n'.join([
            'Taurus Cup (2025-08-21)',
            '  Course      Tokyo Turf 2400m (Medium, left-handed) #10606',
            '  Conditions  Firm, Sunny, Spring, Midday, G1',
            '  Seed        42',
            '  Runners     2',
            '    1. Special Week (Late Surger)',
            '    2. Oguri Cap (Front Runner)']))
        # Changing a preset condition drops the preset title.
        self.assertTrue(str(b.ground(Ground.HEAVY)).startswith('Tokyo Turf 2400m (Medium, left-handed)\n'))
        self.assertEqual(str(RaceBuilder.from_course(10606)).splitlines()[3:],
                         ['  Seed        (not set)', '  Runners     none'])


ROOT = Path(__file__).resolve().parents[1]
V70_SKILLS = json.loads((ROOT / 'data/v70-skill-data.json').read_text(encoding='utf-8'))


def race_with(*skills, table=None):
    runner = uma()
    for skill in skills:
        runner.skill(skill)
    return RaceBuilder.from_course(10606).seed(3).skill_data(table).runner(runner)


class SkillTableTests(unittest.TestCase):
    def test_engine_silently_ignores_skills_missing_from_its_table(self):
        # Why build() checks: an unknown skill ID produces the same race as no skill.
        def replay(builder):
            with PreparedRace(builder.build(allow_unknown_skills=True)) as race:
                return race.run_wire(3)
        baseline = replay(race_with())
        self.assertFalse(Skill.ABOVE_THE_CLOUDLINE_INHERITED.in_bundled_table)
        self.assertEqual(replay(race_with(Skill.ABOVE_THE_CLOUDLINE_INHERITED)), baseline)
        self.assertNotEqual(replay(race_with(Skill.CORNER_ADEPT_CIRCLE)), baseline)

    def test_inherited_skill_in_table_takes_effect_and_differs_from_unique(self):
        def replay(builder):
            with PreparedRace(builder.build()) as race:
                return race.run_wire(3)
        self.assertTrue(Skill.AD_ASTRA_901051.in_bundled_table)
        inherited = RaceBuilder.from_course(10606).seed(3).runner(uma().inherit(Skill.AD_ASTRA_101051))
        unique = RaceBuilder.from_course(10606).seed(3).runner(
            uma().skill(Skill.AD_ASTRA_101051, level=1, unique=True))
        self.assertNotEqual(replay(inherited), replay(race_with()))
        self.assertNotEqual(replay(inherited), replay(unique))

    def test_missing_inherited_skill_error_explains_why(self):
        builder = RaceBuilder.from_course(10606).seed(1).runner(uma().inherit(Skill.ABOVE_THE_CLOUDLINE))
        with self.assertRaisesRegex(ValueError, 'Above the Cloudline \(inherited\) #901302211.*'
                                                'Inherited versions of newer uniques'):
            builder.build()

    def test_bundled_table_rejects_unknown_skills(self):
        builder = race_with(Skill.CORNER_ADEPT_CIRCLE, Skill.ABOVE_THE_CLOUDLINE_INHERITED)
        self.assertEqual(builder.unknown_skills(), [(0, '901302211')])
        with self.assertRaisesRegex(ValueError, r'1 skill\(s\) are not in the bundled skill table.*'
                                                r'runner 0 \(Special Week \(Late Surger\)\): '
                                                r'Above the Cloudline \(inherited\) #901302211'):
            builder.build()
        wire = builder.build(allow_unknown_skills=True).to_dict()
        self.assertNotIn('skillData', wire)
        self.assertEqual([s['skillId'] for s in wire['horses'][0]['skills']], ['200332', '901302211'])

    def test_every_bundled_enum_skill_is_accepted(self):
        runner = uma()
        for skill in Skill:
            if skill.in_bundled_table:
                runner.skill(skill)
        self.assertEqual(RaceBuilder.from_course(10606).seed(1).runner(runner).unknown_skills(), [])

    def test_supplied_table_is_used_for_checks_and_sent(self):
        self.assertFalse(Skill.UNQUENCHED_THIRST.in_bundled_table)
        self.assertIn('300011', V70_SKILLS)
        request = race_with(Skill.UNQUENCHED_THIRST, table=V70_SKILLS).build()
        self.assertEqual(request.to_dict()['skillData'], V70_SKILLS)
        with PreparedRace(request) as race:
            self.assertTrue(race.run_wire(3))
        # A skill in the bundled table can still be missing from the supplied one.
        self.assertNotIn('101302211', V70_SKILLS)
        with self.assertRaisesRegex(ValueError, 'supplied skill_data table.*#101302211'):
            race_with(Skill.ABOVE_THE_CLOUDLINE, table=V70_SKILLS).build()
        # None restores the bundled table.
        builder = race_with(Skill.ABOVE_THE_CLOUDLINE, table=V70_SKILLS).skill_data(None)
        self.assertNotIn('skillData', builder.build().to_dict())

    def test_supplied_table_is_copied(self):
        table = {'300011': V70_SKILLS['300011']}
        builder = race_with(Skill.UNQUENCHED_THIRST, table=table)
        table.clear()
        self.assertEqual(builder.unknown_skills(), [])
        with self.assertRaises(TypeError):
            builder.skill_data(list(V70_SKILLS))

    def test_raw_runner_skill_entries_are_checked_like_the_engine_reads_them(self):
        runner = uma().build()
        runner.extra['skills'] = [{'skillId': 200332}, {'skillId': 200332.0}, '200332',
                                  {'skillId': '0200332'}, {'skillId': 901302211}, {}]
        builder = RaceBuilder.from_course(10606).seed(1).runner(runner)
        self.assertEqual([sid for _, sid in builder.unknown_skills()],
                         ['0200332', '901302211', 'None'])


if __name__ == '__main__':
    unittest.main()
