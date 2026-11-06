"""Thread-confined GlobalSim prepared races through the C ABI (ctypes)."""
import json
import threading
from .capi import CGlobalSim
from .replay_protocol import decode


class NativeRace:
    """Prepare once, run many seeds. Each run returns owned replay bytes.

    Create/use/close this object on one thread. Other threads may create their
    own handles. Frame views from returned Replay objects outlive later runs.
    """
    def __init__(self, library=None, spec=None):
        if spec is None:
            raise TypeError('A race spec is required')
        self._thread = threading.current_thread()
        self._handle = CGlobalSim(library).new()
        try:
            self.prepare(spec)
        except BaseException:
            self.close()
            raise

    def _check(self):
        if threading.current_thread() is not self._thread:
            raise RuntimeError('Use a prepared race only on its creating thread')
        if self._handle is None:
            raise RuntimeError('Prepared race has been closed')

    def _success(self, status):
        if status:
            error = self._handle.error()
            raise ValueError(error or f'GlobalSim status {status}')

    def prepare(self, spec):
        self._check()
        wire = spec if isinstance(spec, (str, bytes)) else json.dumps(spec, separators=(',', ':')).encode('utf-8')
        self._success(self._handle.prepare(wire))

    def run_wire(self, seed):
        self._check()
        if not isinstance(seed, int) or not -(1 << 63) <= seed < (1 << 63):
            raise ValueError('Seed must be a signed 64-bit integer')
        self._success(self._handle.run(seed))
        packet = self._handle.copy_packet()
        if not packet:
            raise RuntimeError('GlobalSim returned no packet')
        return packet

    def run(self, seed):
        return decode(self.run_wire(seed))

    def close(self):
        if self._handle is not None:
            self._check()
            self._success(self._handle.close())
            self._handle = None

    def __enter__(self):
        self._check()
        return self

    def __copy__(self):
        raise TypeError('Native races cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('Native races cannot be copied')

    def __exit__(self, *_):
        self.close()

