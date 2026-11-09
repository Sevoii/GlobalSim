# WebAssembly binding

The `wasm` feature exposes the prepared-race API to JavaScript through
`wasm-bindgen`. Results match native builds bit for bit, replay frames included.
Most applications should use the [JavaScript package](JAVASCRIPT.md). It wraps
this binding with builders, the catalog, geometry loading and a worker pool.
This page documents the raw binding underneath it.

## Building

```sh
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --version 0.2.130 --locked   # must match Cargo.lock
cargo build --lib --release --target wasm32-unknown-unknown --features wasm,external-geometry
wasm-bindgen --target web --out-dir pkg target/wasm32-unknown-unknown/release/globalsim.wasm
```

Use `--target nodejs` for Node, or `--target bundler` for webpack/Vite.

Build with `external-geometry`. Without it, all captured course geometry is
compiled in, which makes the module about 36 MB instead of about 2 MB (about
475 KB gzipped). `mimalloc` is never used on wasm, so the default features
need no C compiler.

## API

```js
import init, { PreparedRace, registerCourseGeometry } from './pkg/globalsim.js';

await init();
// Needed for requests with "experimentalRetailGeometry": true (the validated
// v77 configuration). Supply the exact text of data/course_geometry/<id>.json.
registerCourseGeometry(10504, await (await fetch('course_geometry/10504.json')).text());

const race = new PreparedRace(requestJsonLine);   // same shape as a worker input line
const reply = JSON.parse(race.runJson(12345));    // full reply, frames included
const result = JSON.parse(race.runResults(12345)); // no frames: the Monte Carlo path
const packet = race.runBinary(12345);              // Uint8Array, GSIMRP01 (BINARY-REPLAY.md)
race.free();
```

| Member | Description |
| --- | --- |
| `new PreparedRace(json)` | Prepares a request. Throws `Error` on invalid input. |
| `prepare(json)` | Replaces the preparation. An invalid replacement keeps the current one. |
| `runJson(seed)` | Complete JSON reply for one seed. |
| `runResults(seed)` | Reply without replay frames or frame metadata. |
| `runBinary(seed)` | Lossless binary replay packet. |
| `registerCourseGeometry(id, json)` | Registers one course's captured geometry (`external-geometry` builds). |

Seeds are JS numbers and must be safe integers. Retail-initialized requests
also require a signed 32-bit seed, as on native builds. Geometry is
identity-checked when a race uses it. If it is missing, preparation throws
`Captured course geometry <id> unavailable`.

Instances belong to the JS realm that created them; there is no threading.
To run seeds in parallel, load the module in several Web Workers and give each
one its own `PreparedRace` and a share of the seeds. This needs no special
server headers. Panics abort the module (`panic = "abort"`), so a worker
whose instance trapped should be recreated.

Decoding a binary packet:

```js
const dv = new DataView(packet.buffer, packet.byteOffset, packet.byteLength);
const metaLen = Number(dv.getBigUint64(8, true));
const frameCount = dv.getUint32(16, true), horseCount = dv.getUint32(20, true);
const metadata = JSON.parse(new TextDecoder().decode(packet.subarray(32, 32 + metaLen)));
// Frames: per frame, f64 time then horseCount * 6 f64 values (little-endian).
// The payload offset is not 8-byte aligned, so copy before viewing as Float64Array.
const frames = new Float64Array(packet.slice(32 + metaLen).buffer);
```
