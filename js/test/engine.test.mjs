import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { after, before, describe, it } from 'node:test';
import { PreparedRace, RacePool, decode, init, registerCourseGeometry } from 'globalsim';

// The validated v77 configuration: retail runtime with world geometry.
const line = readFileSync(new URL('../../examples/v77-race.jsonl', import.meta.url), 'utf8').trim();
const request = JSON.parse(line);
const simple = readFileSync(new URL('../../examples/race.jsonl', import.meta.url), 'utf8').trim();
const seeds = Array.from({ length: 24 }, (_, i) => 1000 + i * 37);

describe('PreparedRace', () => {
  let race;
  before(async () => { race = await PreparedRace.create(request); });
  after(() => race.close());

  it('is deterministic per seed and differs across seeds', () => {
    assert.deepEqual(race.runResults(7), race.runResults(7));
    const orders = seeds.map((seed) => race.runResults(seed).results.map((r) => r.finishOrder).join());
    assert.ok(new Set(orders).size > 1);
  });

  it('decodes binary replays losslessly against the JSON reply', () => {
    const replay = race.run(11);
    const json = race.runJson(11);
    assert.ok(replay.count > 100);
    assert.equal(replay.horseCount, request.horses.length);
    assert.deepEqual(replay.toJson(), json);
    const { frames, ...metadata } = json;
    assert.deepEqual(replay.metadata, metadata);
    assert.deepEqual(race.runResults(11).results, json.results);
    const frame = replay.typedFrame(1);
    assert.equal(frame.horses[0].position, frames[1].horses[0].pos);
    assert.deepEqual(decode(race.runWire(11)), replay);
  });

  it('validates seeds and requests before reaching the engine', () => {
    assert.throws(() => race.runResults(1.5), /safe integer/);
    assert.throws(() => race.runResults(2 ** 60), /safe integer/);
    assert.throws(() => new PreparedRace({ ...request, courseId: 1 }), /Unknown course ID/);
    assert.throws(() => new PreparedRace('{bad'), SyntaxError);
  });

  it('keeps the current preparation when a replacement fails', () => {
    const before = race.runResults(5);
    assert.throws(() => race.prepare({ ...request, horses: [] }));
    assert.deepEqual(race.runResults(5), before);
  });

  it('requires geometry for synchronous preparation on a new course', async () => {
    await init();
    assert.throws(() => new PreparedRace({ ...request, courseId: 10101 }), /geometry 10101 is not loaded/);
    registerCourseGeometry(10101, readFileSync(new URL('../../data/course_geometry/10101.json', import.meta.url), 'utf8'));
    new PreparedRace({ ...request, courseId: 10101 }).close();
  });

  it('runs requests without geometry and rejects use after close', () => {
    const other = new PreparedRace(simple);
    assert.ok(other.runResults(3).results.length);
    other.close();
    other.close();
    assert.ok(other.closed);
    assert.throws(() => other.runResults(3), /closed/);
  });
});

describe('RacePool', () => {
  let pool;
  let race;
  before(async () => {
    pool = await RacePool.create({ size: 3, chunkSize: 4 });
    race = await PreparedRace.create(line);
  });
  after(() => { pool.close(); race.close(); });

  it('matches sequential results, in seed order', async () => {
    const progress = [];
    const results = await pool.runResults(line, seeds, { onProgress: (done, total) => progress.push([done, total]) });
    assert.deepEqual(results, seeds.map((seed) => race.runResults(seed)));
    assert.deepEqual(progress.at(-1), [seeds.length, seeds.length]);
  });

  it('returns replays and switches requests between batches', async () => {
    const replays = await pool.run(request, seeds.slice(0, 5));
    assert.deepEqual(replays.map((r) => r.toJson()), seeds.slice(0, 5).map((seed) => race.runJson(seed)));
    const plain = new PreparedRace(simple);
    assert.deepEqual(await pool.runResults(simple, [1, 2, 3]), [1, 2, 3].map((s) => plain.runResults(s)));
    plain.close();
  });

  it('reports engine errors and recovers', async () => {
    await assert.rejects(pool.runResults({ ...request, horses: [] }, [1, 2]));
    await assert.rejects(pool.runResults(line, [1.5]), /safe integers/);
    assert.deepEqual(await pool.runResults(line, [9]), [race.runResults(9)]);
  });

  it('stops on abort', async () => {
    const controller = new AbortController();
    controller.abort(new Error('stop'));
    await assert.rejects(pool.runResults(line, seeds, { signal: controller.signal }), /stop/);
  });
});
