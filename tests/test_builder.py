import unittest
import json

from globalsim import Aptitude, Strategy, UmaBuilder, Skill, Uma


def builder():
    return (UmaBuilder(Uma.SPECIAL_WEEK)
            .stats(speed=1200, stamina=900, power=1000, guts=400, wisdom=600)
            .strategy(Strategy.LATE_SURGER)
            .aptitudes(distance=Aptitude.A, surface=Aptitude.A, strategy=Aptitude.A))


class UmaBuilderTests(unittest.TestCase):
    def test_import_oguri_example(self):
        ids = ['100061', '200201', '200331', '200362', '200492', '200592',
               '200602', '200652', '200961', '201002', '201391', '201591',
               '201611', '201662', '202401', '202472', '900511', '910611']
        value = dict(speed=1540, stamina=406, power=1229, guts=733, wisdom=1213,
                     strategy='Sasi', distanceAptitude='S', surfaceAptitude='A',
                     strategyAptitude='A', charaId=1006,
                     skills=[dict(skillId=s, level=5 if i == 0 else 1, isUnique=i == 0)
                             for i, s in enumerate(ids)])
        for source in (value, json.dumps(value), json.dumps(value).encode()):
            imported = UmaBuilder.from_json(source)
            self.assertEqual(json.loads(imported.to_json()), dict(value, mood=0))
            self.assertEqual(UmaBuilder.from_json(imported.to_json()).build(), imported.build())

    def test_import_extra_fields_are_independent(self):
        value = builder().build().to_dict()
        value['custom'] = {'items': [1]}
        imported = UmaBuilder.from_json(value)
        value['custom']['items'].append(2)
        self.assertEqual(imported.build().extra['custom'], {'items': [1]})
        self.assertEqual(imported.mood(2).build().extra['mood'], 2)

    def test_invalid_json_inputs(self):
        for source in ('{', {}, {'charaId': True}, {'charaId': 999999}):
            with self.subTest(source=source), self.assertRaises(ValueError):
                UmaBuilder.from_json(source)
        with self.assertRaises(TypeError):
            UmaBuilder.from_json('[]')

    def test_wire_and_independent_builds(self):
        b = builder().skill(Skill.SHOOTING_STAR_100011, level=3, unique=True)
        first = b.build()
        wire = first.to_dict()
        self.assertEqual(wire['charaId'], 1001)
        self.assertEqual(wire['strategy'], 'Sasi')
        self.assertEqual(wire['distanceAptitude'], 'A')
        self.assertEqual(wire['skills'], [{'skillId': '100011', 'level': 3, 'isUnique': True}])
        first.extra['skills'][0]['level'] = 6
        self.assertEqual(b.build().extra['skills'][0]['level'], 3)

    def test_required_fields(self):
        with self.assertRaises(ValueError):
            UmaBuilder(Uma.SPECIAL_WEEK).build()

    def test_invalid_stats(self):
        for value in (-1, float('nan'), float('inf'), True, '1200'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder().stats(speed=value, stamina=1, power=1, guts=1, wisdom=1)

    def test_duplicate_skill_replaces_level(self):
        result = builder().skill(Skill.SHOOTING_STAR_100011).skill(Skill.SHOOTING_STAR_100011, level=2).build()
        self.assertEqual(len(result.extra['skills']), 1)
        self.assertEqual(result.extra['skills'][0]['level'], 2)

    def test_enum_values_are_unique(self):
        for enum in (Skill, Uma):
            with self.subTest(enum=enum.__name__):
                self.assertEqual(len(enum.__members__), len(enum))

    def test_setter_type_checks(self):
        with self.assertRaises(TypeError):
            UmaBuilder(1001)
        with self.assertRaises(TypeError):
            builder().skill(100011)
        with self.assertRaises(TypeError):
            builder().skill(Skill.SHOOTING_STAR_100011, unique=1)
        for level in (0, 7, True, 1.0, '1'):
            with self.subTest(level=level), self.assertRaises(ValueError):
                builder().skill(Skill.SHOOTING_STAR_100011, level=level)
        for mood in (-3, 3, True, 1.0, None):
            with self.subTest(mood=mood), self.assertRaises(ValueError):
                builder().mood(mood)
        for bad in ('x', 'nige', None):
            with self.subTest(strategy=bad), self.assertRaises(ValueError):
                builder().strategy(bad)
        with self.assertRaises(ValueError):
            builder().aptitudes(distance='s', surface='A', strategy='A')

    def test_setter_boundaries(self):
        b = builder().stats(speed=0, stamina=0.5, power=0, guts=0, wisdom=2000)
        for level in (1, 6):
            b.skill(Skill.SHOOTING_STAR_100011, level=level)
        for mood in (-2, 2):
            self.assertEqual(b.mood(mood).build().extra['mood'], mood)
        self.assertEqual(b.build().speed, 0)
        for strategy in Strategy:
            with self.subTest(strategy=strategy):
                self.assertEqual(b.strategy(strategy.value).build().strategy, strategy.value)



class InheritTests(unittest.TestCase):
    def test_unique_or_inherited_member_adds_inherited_at_level_1(self):
        for given in (Skill.AD_ASTRA_101051, Skill.AD_ASTRA_901051):
            with self.subTest(given=given.name):
                skills = builder().inherit(given).build().extra['skills']
                self.assertEqual(skills, [{'skillId': '901051', 'level': 1, 'isUnique': False}])
        self.assertEqual(builder().inherit(Skill.ABOVE_THE_CLOUDLINE).build().extra['skills'][0]['skillId'],
                         '901302211')

    def test_rejects_non_uniques_and_non_members(self):
        for bad in (Skill.CORNER_ADEPT_CIRCLE, Skill.UNQUENCHED_THIRST):
            with self.subTest(skill=bad.name), self.assertRaisesRegex(ValueError, 'no inherited version'):
                builder().inherit(bad)
        for bad in (100011, '100011', None):
            with self.subTest(skill=bad), self.assertRaises(TypeError):
                builder().inherit(bad)

    def test_cannot_inherit_own_unique(self):
        b = builder().skill(Skill.SHOOTING_STAR_100011, level=3, unique=True)
        for given in (Skill.SHOOTING_STAR_100011, Skill.SHOOTING_STAR_900011):
            with self.subTest(given=given.name), self.assertRaisesRegex(ValueError, 'own unique'):
                b.inherit(given)
        # The same skill added without the unique flag isn't the runner's own unique.
        builder().skill(Skill.SHOOTING_STAR_100011).inherit(Skill.SHOOTING_STAR_100011)

    def test_inheriting_twice_keeps_one_entry_and_overrides_level(self):
        b = builder().skill(Skill.AD_ASTRA_901051, level=4).inherit(Skill.AD_ASTRA_101051)
        self.assertEqual(b.build().extra['skills'], [{'skillId': '901051', 'level': 1, 'isUnique': False}])

    def test_str_marks_inherited_skills(self):
        text = str(builder().skill(Skill.AD_ASTRA_101051, level=2, unique=True)
                   .inherit(Skill.SHOOTING_STAR_100011).inherit(Skill.ABOVE_THE_CLOUDLINE))
        self.assertIn('    Ad Astra                         #101051     Lv2  unique', text)
        self.assertIn('    Shooting Star (inherited)        #900011     Lv1', text)
        self.assertIn('    Above the Cloudline (inherited)  #901302211  Lv1', text)
        self.assertNotIn('(inherited) (inherited)', text)

    def test_round_trips_through_json(self):
        b = builder().inherit(Skill.AD_ASTRA_101051)
        self.assertEqual(UmaBuilder.from_json(b.to_json()).build(), b.build())


def runner_json(**changes):
    """A minimal valid runner dictionary; pass key=None to remove a field."""
    value = dict(speed=1200, stamina=900, power=1000, guts=400, wisdom=600,
                 strategy='Sasi', distanceAptitude='A', surfaceAptitude='A',
                 strategyAptitude='A', charaId=1001)
    value.update(changes)
    return {k: v for k, v in value.items() if v is not None}


def skills_of(**changes):
    return UmaBuilder.from_json(runner_json(**changes)).build().extra['skills']


REQUIRED = ('speed', 'stamina', 'power', 'guts', 'wisdom', 'strategy',
            'distanceAptitude', 'surfaceAptitude', 'strategyAptitude', 'charaId')


class FromJsonEdgeCaseTests(unittest.TestCase):
    def test_each_missing_required_field_is_named(self):
        for field in REQUIRED:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, f'Missing runner field: {field}'):
                    UmaBuilder.from_json(runner_json(**{field: None}))

    def test_optional_fields_default(self):
        built = UmaBuilder.from_json(runner_json()).build()
        self.assertEqual(built.extra, {'charaId': 1001, 'mood': 0, 'skills': []})
        self.assertEqual(skills_of(skills=[{'skillId': '100011'}]),
                         [{'skillId': '100011', 'level': 1, 'isUnique': False}])

    def test_source_types(self):
        text = json.dumps(runner_json())
        for source in (text, text.encode(), bytearray(text.encode()), runner_json()):
            with self.subTest(source=type(source).__name__):
                self.assertEqual(UmaBuilder.from_json(source).build().extra['charaId'], 1001)
        for source in (None, 5, [runner_json()], '[]', '"x"', 'null'):
            with self.subTest(source=source), self.assertRaises(TypeError):
                UmaBuilder.from_json(source)
        # JSONDecodeError and UnicodeDecodeError are both ValueErrors.
        for source in ('', '{', b'\xff', '{"speed": NaN}'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                UmaBuilder.from_json(source)

    def test_invalid_field_values(self):
        cases = dict(charaId=['1001', 1001.0, True, 0, 999999],
                     speed=[-1, '1200', True, float('nan'), float('inf')],
                     strategy=['x', 'sasi', 1], distanceAptitude=['s', 'SS', 1],
                     surfaceAptitude=['Z'], strategyAptitude=[''],
                     mood=[3, -3, 1.0, '1'],
                     skills=[{}, '100011', 100011])
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    UmaBuilder.from_json(runner_json(**{field: value}))
        # An explicit null is not the same as a missing optional field.
        for field in ('mood', 'skills', 'charaId', 'speed'):
            with self.subTest(field=field, value=None), self.assertRaises(ValueError):
                UmaBuilder.from_json(dict(runner_json(), **{field: None}))

    def test_invalid_skill_entries(self):
        for entry in ({}, {'level': 2}, {'skillId': None}, {'skillId': True},
                      {'skillId': 100011.0}, {'skillId': '1e5'}, {'skillId': ' 100011'},
                      {'skillId': -100011}, {'skillId': '1'}, None, 1.5, [100011],
                      {'skillId': '100011', 'level': 0}, {'skillId': '100011', 'level': 7},
                      {'skillId': '100011', 'level': '2'}, {'skillId': '100011', 'level': None}):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                skills_of(skills=[entry])
        for unique in ('true', 1, None):
            with self.subTest(isUnique=unique), self.assertRaises(TypeError):
                skills_of(skills=[{'skillId': '100011', 'isUnique': unique}])

    def test_skill_ids_are_canonicalized(self):
        # The engine looks skills up by the exact string, so every accepted spelling
        # of an ID must be emitted as the canonical decimal string.
        for raw in (100011, '100011', '0100011', '١٠٠٠١١'):
            with self.subTest(raw=raw):
                self.assertEqual(skills_of(skills=[{'skillId': raw, 'level': 2}]),
                                 [{'skillId': '100011', 'level': 2, 'isUnique': False}])

    def test_bare_skill_ids(self):
        self.assertEqual([s['skillId'] for s in skills_of(skills=[100011, '200201'])],
                         ['100011', '200201'])

    def test_skill_extra_fields_and_duplicates(self):
        skills = skills_of(skills=[
            {'skillId': '100011', 'level': 2, 'note': 'first'},
            {'skillId': '200201', 'tag': {'a': [1]}},
            {'skillId': '100011', 'level': 3}])
        # A repeated ID replaces the earlier entry entirely, keeping first-seen order.
        self.assertEqual(skills, [{'skillId': '100011', 'level': 3, 'isUnique': False},
                                  {'skillId': '200201', 'level': 1, 'isUnique': False,
                                   'tag': {'a': [1]}}])

    def test_input_is_not_mutated_or_shared(self):
        value = runner_json(skills=[{'skillId': '100011', 'tag': {'a': [1]}}],
                            custom={'items': [1]})
        snapshot = json.loads(json.dumps(value))
        imported = UmaBuilder.from_json(value)
        built = imported.mood(1).skill(Skill.SHOOTING_STAR_100011, level=6).build()
        built.extra['custom']['items'].append(9)
        self.assertEqual(value, snapshot)
        self.assertEqual(imported.build().extra['custom'], {'items': [1]})

    def test_known_fields_do_not_leak_into_extra(self):
        built = UmaBuilder.from_json(runner_json(mood=1, skills=[], custom=1)).build()
        self.assertEqual(set(built.extra), {'charaId', 'mood', 'skills', 'custom'})
        self.assertEqual(set(built.to_dict()), set(REQUIRED) | {'mood', 'skills', 'custom'})

    def test_imported_builder_can_be_modified(self):
        imported = UmaBuilder.from_json(runner_json(skills=[{'skillId': '100011', 'level': 2}]))
        built = (imported.strategy(Strategy.FRONT_RUNNER)
                 .stats(speed=1, stamina=2, power=3, guts=4, wisdom=5)
                 .skill(Skill.SHOOTING_STAR_100011, level=5, unique=True).build())
        self.assertEqual((built.strategy, built.speed), ('Nige', 1))
        self.assertEqual(built.extra['skills'],
                         [{'skillId': '100011', 'level': 5, 'isUnique': True}])


class ToJsonTests(unittest.TestCase):
    def test_incomplete_builder_raises(self):
        for b in (UmaBuilder(Uma.SPECIAL_WEEK),
                  UmaBuilder(Uma.SPECIAL_WEEK).stats(speed=1, stamina=1, power=1, guts=1, wisdom=1)):
            with self.assertRaises(ValueError):
                b.to_json()

    def test_format_round_trips_and_keeps_unicode(self):
        imported = UmaBuilder.from_json(runner_json(name='スペシャルウィーク ○'))
        text = imported.to_json()
        self.assertTrue(text.startswith('{\n  "'))
        self.assertIn('スペシャルウィーク ○', text)
        self.assertEqual(UmaBuilder.from_json(text).build(), imported.build())
        self.assertNotIn('\n', imported.to_json(indent=None))

    def test_non_finite_extra_values_are_rejected(self):
        with self.assertRaises(ValueError):
            UmaBuilder.from_json(runner_json(custom=float('nan'))).to_json()


class StrTests(unittest.TestCase):
    def test_complete_summary(self):
        b = (builder().mood(2).stats(speed=1200, stamina=900, power=1000, guts=400, wisdom=600.5)
             .skill(Skill.SHOOTING_STAR_100011, level=3, unique=True)
             .skill(Skill.CORNER_ADEPT_CIRCLE))
        self.assertEqual(str(b), '\n'.join([
            'Special Week (#1001)',
            '  Strategy   Late Surger',
            '  Mood       Great (+2)',
            '  Stats      Speed 1200  Stamina 900  Power 1000  Guts 400  Wit 600.5',
            '  Aptitudes  Distance A  Surface A  Strategy A',
            '  Skills     2',
            '    Shooting Star   #100011     Lv3  unique',
            '    Corner Adept ○  #200332     Lv1']))

    def test_incomplete_builder_does_not_raise(self):
        self.assertEqual(str(UmaBuilder(Uma.T_M_OPERA_O)), '\n'.join([
            'T.M. Opera O (#1015)',
            '  Strategy   (not set)',
            '  Mood       Normal (+0)',
            '  Stats      (not set)',
            '  Aptitudes  (not set)',
            '  Skills     none']))

    def test_every_strategy_and_mood_has_a_name(self):
        for strategy in Strategy:
            with self.subTest(strategy=strategy):
                self.assertIn(strategy.name.replace('_', ' ').title(),
                              str(builder().strategy(strategy)))
        for mood, name in zip(range(-2, 3), ('Awful', 'Bad', 'Normal', 'Good', 'Great')):
            with self.subTest(mood=mood):
                self.assertIn(f'Mood       {name} ({mood:+d})', str(builder().mood(mood)))

    def test_imported_extra_fields_are_listed_by_key(self):
        text = str(UmaBuilder.from_json(runner_json(zeta=1, alpha={'nested': [1]})))
        self.assertTrue(text.endswith('\n  Extra      alpha, zeta'))
        self.assertNotIn('nested', text)

    def test_print_does_not_change_build(self):
        b = builder().skill(Skill.SHOOTING_STAR_100011)
        before = b.build()
        str(b)
        self.assertEqual(b.build(), before)


if __name__ == '__main__':
    unittest.main()
