// Build the package: the wasm engine, its JS glue, the TypeScript, and the assets.
//   node build.mjs              everything
//   node build.mjs --skip-wasm  TypeScript and assets only (reuses src/wasm)
// CARGO and WASM_BINDGEN override the tool paths. wasm-bindgen-cli must match
// the wasm-bindgen version in ../Cargo.lock.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const glue = join(here, 'src/wasm');
const dist = join(here, 'dist');
const run = (command, args, cwd = here) => execFileSync(command, args, { cwd, stdio: 'inherit' });

if (!process.argv.includes('--skip-wasm')) {
  run(process.env.CARGO ?? 'cargo', ['build', '--lib', '--release', '--target', 'wasm32-unknown-unknown',
    '--features', 'wasm,external-geometry'], root);
  rmSync(glue, { recursive: true, force: true });
  run(process.env.WASM_BINDGEN ?? 'wasm-bindgen', ['--target', 'web', '--out-dir', glue,
    join(root, 'target/wasm32-unknown-unknown/release/globalsim.wasm')]);
}
if (!existsSync(join(glue, 'globalsim.js'))) throw new Error('src/wasm is missing; run `node build.mjs` without --skip-wasm');

rmSync(dist, { recursive: true, force: true });
run(process.execPath, [createRequire(import.meta.url).resolve('typescript/bin/tsc'), '-p', here]);
mkdirSync(join(dist, 'wasm'), { recursive: true });
cpSync(glue, join(dist, 'wasm'), { recursive: true });
cpSync(join(root, 'data/course_geometry'), join(dist, 'course_geometry'), { recursive: true });
console.log('Built js/dist');
