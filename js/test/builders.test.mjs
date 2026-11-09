import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  Aptitude, ChampionsMeeting, Course, Ground, Layout, RaceBuilder, RacePreset, Season, Skill, Strategy, Surface, Track,
  Uma, UmaBuilder, Weather, groundToEngine, inheritedSkill, skillDisplayName, skillIsInherited, skillLabel, uniqueSkill,
} from 'globalsim';

const oguri = () => new UmaBuilder(Uma.OGURI_CAP)
  .stats({ speed: 1540, stamina: 406, power: 1229, guts: 733, wisdom: 1213 })
  .strategy(Strategy.LATE_SURGER)
  .aptitudes({ distance: Aptitude.S, surface: Aptitude.A, strategy: Aptitude.A })
  .skill(Skill.TRIUMPHANT_PULSE_100061, { level: 5, unique: true })
  .skill(Skill.PROFESSOR_OF_CURVATURE)
  .mood(2);

describe('UmaBuilder', () => {
  it('prints the same summary as the Python builder', () => {
    assert.equal(String(oguri()), [
      'Oguri Cap (#1006)',
      '  Strategy   Late Surger',
      '  Mood       Great (+2)',
      '  Stats      Speed 1540  Stamina 406  Power 1229  Guts 733  Wit 1213',
      '  Aptitudes  Distance S  Surface A  Strategy A',
      '  Skills     2',
      '    Triumphant Pulse        #100061     Lv5  unique',
      '    Professor of Curvature  #200331     Lv1',
    ].join('\n'));
    assert.match(String(new UmaBuilder(Uma.SPECIAL_WEEK)), /Strategy {3}\(not set\)\n {2}Mood {7}Normal \(\+0\)/);
  });

  it('builds the engine runner shape', () => {
    assert.deepEqual(oguri().build(), {
      charaId: 1006, mood: 2,
      skills: [{ skillId: '100061', level: 5, isUnique: true }, { skillId: '200331', level: 1, isUnique: false }],
      speed: 1540, stamina: 406, power: 1229, guts: 733, wisdom: 1213,
      strategy: 'Sasi', distanceAptitude: 'S', surfaceAptitude: 'A', strategyAptitude: 'A',
    });
  });

  it('returns independent runners', () => {
    const builder = oguri();
    const runner = builder.build();
    runner.skills[0].level = 1;
    builder.mood(0);
    assert.equal(builder.build().skills[0].level, 5);
    assert.equal(runner.mood, 2);
  });

  it('round-trips JSON, keeping extra fields and canonicalizing skill IDs', () => {
    const json = JSON.stringify({ ...oguri().build(), gateIndex: 3,
      skills: [{ skillId: 201051, level: 2, note: 'x' }, '200331'] });
    const loaded = UmaBuilder.fromJson(json);
    assert.deepEqual(loaded.build().skills, [
      { skillId: '201051', level: 2, isUnique: false, note: 'x' },
      { skillId: '200331', level: 1, isUnique: false },
    ]);
    assert.equal(loaded.build().gateIndex, 3);
    assert.match(String(loaded), /Extra {6}gateIndex$/);
    assert.deepEqual(UmaBuilder.fromJson(loaded.toJson()).build(), loaded.build());
  });

  it('rejects invalid input', () => {
    assert.throws(() => new UmaBuilder(42), /Uma member/);
    assert.throws(() => UmaBuilder.fromJson('{"charaId": 1001}'), /Missing runner field: speed/);
    assert.throws(() => UmaBuilder.fromJson('[]'), /must be an object/);
    assert.throws(() => oguri().stats({ speed: -1, stamina: 1, power: 1, guts: 1, wisdom: 1 }), /nonnegative/);
    assert.throws(() => oguri().strategy('FRONT_RUNNER'), /Unknown strategy/);
    assert.throws(() => oguri().skill(Skill.PROFESSOR_OF_CURVATURE, { level: 7 }), /1 to 6/);
    assert.throws(() => oguri().mood(3), /-2 to 2/);
    assert.throws(() => new UmaBuilder(Uma.OGURI_CAP).build(), /before building/);
  });

  it('adds inherited uniques', () => {
    const runner = oguri().inherit(Skill.AD_ASTRA_101051).build();
    assert.deepEqual(runner.skills.at(-1), { skillId: '901051', level: 1, isUnique: false });
    assert.throws(() => oguri().inherit(Skill.TRIUMPHANT_PULSE_100061), /own unique/);
    assert.throws(() => oguri().inherit(Skill.PROFESSOR_OF_CURVATURE), /no inherited version/);
  });
});

describe('catalog helpers', () => {
  it('labels and pairs skills', () => {
    assert.equal(skillLabel(Skill.CORNER_ADEPT_CIRCLE), 'Corner Adept ○');
    assert.equal(inheritedSkill(Skill.AD_ASTRA_101051), Skill.AD_ASTRA_901051);
    assert.equal(uniqueSkill(Skill.AD_ASTRA_901051), Skill.AD_ASTRA_101051);
    assert.ok(skillIsInherited(Skill.AD_ASTRA_901051));
    assert.equal(skillDisplayName(Skill.AD_ASTRA_901051), 'Ad Astra (inherited)');
    assert.throws(() => skillLabel(1), /Unknown skill ID/);
  });
});

describe('RaceBuilder', () => {
  const runner = new UmaBuilder(Uma.SPECIAL_WEEK)
    .stats({ speed: 1200, stamina: 900, power: 1000, guts: 400, wisdom: 600 })
    .strategy(Strategy.LATE_SURGER)
    .aptitudes({ distance: Aptitude.A, surface: Aptitude.A, strategy: Aptitude.A });

  it('summarizes Champions Meeting presets like Python', () => {
    assert.equal(String(RaceBuilder.championsMeeting(ChampionsMeeting.TAURUS_CUP).seed(1).runner(runner)), [
      'Taurus Cup (2025-08-21)',
      '  Course      Tokyo Turf 2400m (Medium, left-handed) #10606',
      '  Conditions  Firm, Sunny, Spring, Midday, G1',
      '  Seed        1',
      '  Runners     1',
      '    1. Special Week (Late Surger)',
    ].join('\n'));
  });

  it('builds requests with engine ground names', () => {
    const request = new RaceBuilder(Track.KYOTO, Surface.TURF, 1600, { layout: Layout.OUTER })
      .ground(Ground.GOOD).weather(Weather.CLOUDY).season(Season.AUTUMN).seed(42).runner(runner).build();
    assert.equal(request.courseId, 10805);
    assert.equal(request.groundCondition, 'Yielding');
    assert.equal(groundToEngine(Ground.FIRM), 'Good');
    assert.deepEqual(Object.keys(request),
      ['time', 'grade', 'seed', 'courseId', 'groundCondition', 'weather', 'season', 'horses']);
  });

  it('finds courses and explains misses', () => {
    assert.equal(Course.find(Track.TOKYO, Surface.TURF, 2400), Course.get(10606));
    assert.throws(() => Course.find(Track.KYOTO, Surface.TURF, 1600), /2 courses match .* pass a layout/);
    assert.throws(() => Course.find(Track.KYOTO, Surface.TURF, 1234), /No Kyoto turf course of 1234m; available: /);
    assert.equal(RacePreset.allChampionsMeetings()[0].name, 'Taurus Cup');
  });

  it('rejects skills the table does not define', () => {
    const builder = RaceBuilder.fromCourse(10606).seed(1)
      .runner(new UmaBuilder(Uma.OGURI_CAP).stats({ speed: 1, stamina: 1, power: 1, guts: 1, wisdom: 1 })
        .strategy(Strategy.FRONT_RUNNER).aptitudes({ distance: 'A', surface: 'A', strategy: 'A' })
        .skill(inheritedSkill(Skill.ABOVE_THE_CLOUDLINE)));
    assert.deepEqual(builder.unknownSkills(), [[0, '901302211']]);
    assert.throws(() => builder.build(), /Above the Cloudline \(inherited\) #901302211.*allowUnknownSkills/);
    assert.equal(builder.build({ allowUnknownSkills: true }).horses.length, 1);
    assert.deepEqual(builder.skillData({ 901302211: {} }).unknownSkills(), []);
  });

  it('requires a seed, runners and valid conditions', () => {
    assert.throws(() => RaceBuilder.fromCourse(10606).runner(runner).build(), /seed/);
    assert.throws(() => RaceBuilder.fromCourse(10606).seed(1).build(), /runner/);
    assert.throws(() => RaceBuilder.fromCourse(10606).ground('Yielding'), /Ground member/);
    assert.throws(() => RaceBuilder.fromCourse(10606).seed(1.5), /safe integer/);
    assert.throws(() => RaceBuilder.fromCourse(1), /Unknown course ID/);
  });
});
