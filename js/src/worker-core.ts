/** The message loop shared by the browser worker and the Node worker thread. */
import { PreparedRace, init, isTrapped, registerCourseGeometry } from './engine.js';
import type { RaceResult } from './models.js';

export type WorkerRequest =
  | { type: 'init'; module: WebAssembly.Module }
  | { type: 'run'; mode: 'results' | 'replay'; seeds: number[]; request?: string; geometry?: [number, string] };

export type WorkerReply =
  | { type: 'ready' }
  | { type: 'initError'; message: string }
  | { type: 'done'; results: RaceResult[] | Uint8Array[] }
  | { type: 'error'; message: string; fatal: boolean };

export interface WorkerPort {
  post(message: WorkerReply, transfer?: ArrayBuffer[]): void;
  onMessage(listener: (message: WorkerRequest) => void): void;
}

const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error);

export function serve(port: WorkerPort): void {
  let race: PreparedRace | undefined;
  let queue = Promise.resolve();

  async function handle(message: WorkerRequest) {
    if (message.type === 'init') {
      try {
        await init(message.module);
        port.post({ type: 'ready' });
      } catch (error) {
        port.post({ type: 'initError', message: messageOf(error) });
      }
      return;
    }
    try {
      if (message.geometry) registerCourseGeometry(...message.geometry);
      if (message.request !== undefined) {
        if (race) race.prepare(message.request);
        else race = new PreparedRace(message.request);
      }
      if (!race) throw new Error('No race has been prepared in this worker');
      if (message.mode === 'results') {
        port.post({ type: 'done', results: message.seeds.map((seed) => race!.runResults(seed)) });
      } else {
        const packets = message.seeds.map((seed) => race!.runWire(seed));
        port.post({ type: 'done', results: packets }, packets.map((packet) => packet.buffer as ArrayBuffer));
      }
    } catch (error) {
      port.post({ type: 'error', message: messageOf(error), fatal: isTrapped() });
    }
  }

  port.onMessage((message) => { queue = queue.then(() => handle(message)); });
}
