/** Browser Web Worker entry for RacePool. */
import { serve, type WorkerReply, type WorkerRequest } from './worker-core.js';

const scope = self as unknown as {
  postMessage(message: WorkerReply, transfer: ArrayBuffer[]): void;
  addEventListener(type: 'message', listener: (event: { data: WorkerRequest }) => void): void;
};

serve({
  post: (message, transfer) => scope.postMessage(message, transfer ?? []),
  onMessage: (listener) => scope.addEventListener('message', (event) => listener(event.data)),
});
