# GlobalSim JavaScript API

The `js/` package wraps the [WebAssembly binding](WASM.md) with the same
high-level API as the [Python package](PYTHON-DOCUMENTATION.md): `UmaBuilder`,
`RaceBuilder`, Champions Meeting presets, generated `Skill`/`Uma`/`Track`
catalogs, prepared races, and replay decoding. It adds a worker pool for running
seeds in parallel. Everything runs client-side, so static hosting is enough.
Results match native builds bit for bit.

It is written in TypeScript and ships type declarations, so editors complete
`Skill.`, `Uma.` and the builder methods.

## Building

Requires Node 20+, the `wasm32-unknown-unknown` Rust target and
`wasm-bindgen-cli` matching `Cargo.lock` (see [WASM.md](WASM.md#building)).

```sh
cd js
npm install
npm run build      # cargo + wasm-bindgen + tsc; writes js/dist
npm test
```

Set `CARGO` or `WASM_BINDGEN` to override the tool paths. Use
`npm run build:ts` to rebuild only the TypeScript.

`dist/` holds the modules, `dist/wasm/` the engine (about 2 MB, 475 KB
gzipped), and `dist/course_geometry/` a copy of the captured geometry. Each
course file is fetched only when a race on that course needs it.

## Example

```js
import {
  Aptitude, ChampionsMeeting, PreparedRace, RaceBuilder, RacePool, Skill, Strategy, Uma, UmaBuilder,
} from 'globalsim';

const runner = new UmaBuilder(Uma.SPECIAL_WEEK)
  .stats({ speed: 1200, stamina: 900, power: 1000, guts: 400, wisdom: 600 })
  .strategy(Strategy.LATE_SURGER)
  .aptitudes({ distance: Aptitude.A, surface: Aptitude.A, strategy: Aptitude.A })
  .skill(Skill.SHOOTING_STAR_100011, { level: 3, unique: true })
  .inherit(Skill.AD_ASTRA_101051)
  .mood(2);

const builder = RaceBuilder.championsMeeting(ChampionsMeeting.TAURUS_CUP).seed(1).runner(runner);
console.log(String(builder));
const request = builder.build();

// One seed at a time, on the current thread.
const race = await PreparedRace.create(request);
const replay = race.run(1);              // metadata + Float64Array frames
const result = race.runResults(2);       // no frames: fastest
race.close();

// Many seeds across Web Workers (worker threads in Node).
const pool = await RacePool.create();    // one worker per core
const results = await pool.runResults(request, [1, 2, 3, 4, 5], {
  onProgress: (done, total) => console.log(`${done}/${total}`),
});
pool.close();
```

`js/examples/browser.html` is a runnable page. Serve `js/` over HTTP, for
example with `python -m http.server`, and open `/examples/browser.html`.

## Differences from Python

The behavior, validation and messages are the same, with JavaScript conventions:

- Methods are camelCase, and keyword arguments are option objects:
  `.stats({ speed, ... })`, `.skill(id, { level, unique })`,
  `new RaceBuilder(track, surface, distance, { layout })`,
  `build({ allowUnknownSkills: true })`.
- Enums are `as const` objects plus a matching type. Members are plain numbers
  or strings, so labels come from functions: `skillLabel(Skill.X)`, `umaLabel`,
  `trackLabel`, `championsMeetingLabel`. `inheritedSkill`, `uniqueSkill`,
  `skillIsInherited` and `skillInBundledTable` replace the Python properties.
- **`Ground` values are the Global names** (`Ground.FIRM === 'Firm'`).
  `RaceBuilder.build()` converts them to the engine's names, so Firm becomes
  `'Good'` and Good becomes `'Yielding'`. That way a bare `'Good'` can't
  silently mean Firm. Use `groundToEngine` and `groundFromEngine` to convert.
- Runners and requests are plain objects in the engine's JSON shape. There is
  no separate `Runner`/`RaceRequest` class or `to_dict()`. They are TypeScript
  interfaces instead.
- `RacePreset.date` is an ISO string. `Course` instances are shared, so `===`
  compares them.
- Seeds must be safe integers (|seed| < 2^53).

## Engine API

| API | Description |
| --- | --- |
| `await init(source?)` | Loads the engine; called automatically by `PreparedRace.create` and `RacePool.create`. `source` can be a URL, `Response`, bytes, or a `WebAssembly.Module`. |
| `await PreparedRace.create(request)` | Loads the engine and any needed geometry, then prepares. `request` is an object or JSON text. |
| `new PreparedRace(request)` | Synchronous; requires `init()` and loaded geometry. |
| `race.run(seed)` | Returns a `Replay`. |
| `race.runResults(seed)` | Results object, without frames. |
| `race.runJson(seed)` | Conventional JSON reply, frames included. |
| `race.runWire(seed)` | Binary packet (`Uint8Array`). |
| `race.prepare(request)` | Replaces the request; a failure keeps the current one. |
| `race.close()` | Frees engine memory. Also `using race = ...` where supported. |
| `setGeometrySource(urlOrFn)` | Where to fetch `<courseId>.json` from; defaults to the package's copy. |
| `registerCourseGeometry(id, json)` / `await loadCourseGeometry(id)` / `await ensureGeometry(request)` | Manual geometry control. |
| `decode(packet)` | Validates and decodes a binary packet. |

`Replay` has `metadata`, `count`, `horseCount`, `width` (values per frame),
`stride` (bytes per frame), and `frames`: a `Float64Array` of
`count * width` values. Each frame row is the time followed by
`pos, speed, hp, lane, temptationMode, blockFrontHorseIndex` for every runner
(see `FIELDS`). `frame(i)` returns `[time, values]` as views, `typedFrame(i)`
returns named values, and `toJson()` rebuilds the conventional reply.

Unknown course IDs are rejected before they reach the engine, because they can
make it panic. A native panic aborts that copy of the module. After one, the
wrapper throws for every call on that thread until the page is reloaded.
`RacePool` replaces a worker that panicked.

## RacePool

| API | Description |
| --- | --- |
| `await RacePool.create({ size?, chunkSize?, spawn? })` | Starts `size` workers (default: logical cores). Each gets the compiled engine, so it is downloaded once. |
| `pool.runResults(request, seeds, { onProgress?, signal? })` | Results for every seed, in seed order. |
| `pool.run(request, seeds, options)` | `Replay`s for every seed. |
| `pool.close()` | Terminates the workers. In Node, a pool that is not closed keeps the process alive. |

Batches run one at a time. Each worker prepares a request once and reuses it
until the request changes. Geometry is loaded once on the calling thread and
sent to each worker. The pool uses plain Web Workers, not shared-memory
threads, so it needs no cross-origin isolation headers. With bundlers,
`new Worker(new URL('./worker.js', import.meta.url))` is the pattern that Vite
and webpack 5 detect and bundle.

## Catalog

`js/src/catalog.ts` is generated by `tools/generate_js_catalog.py` from
`python/globalsim/enums.py` and `courses.py`, so both packages have identical
members. `tools/generate_catalog.py` regenerates it automatically; run
`npm run catalog` after editing the Python modules by hand. Provenance and
license: [CATALOG-SOURCES.md](../python/globalsim/CATALOG-SOURCES.md).
