/** Node worker-thread entry for RacePool. */
import { parentPort } from 'node:worker_threads';
import { serve, type WorkerRequest } from './worker-core.js';

const port = parentPort!;
serve({
  post: (message, transfer) => port.postMessage(message, transfer),
  onMessage: (listener) => port.on('message', (message: WorkerRequest) => listener(message)),
});
