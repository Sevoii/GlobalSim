"""Convenient Python interface to the PyO3 prepared race."""
import json
import threading
from .replay_protocol import decode


class PreparedRace:
    """Prepare a request once and simulate independent seeds on its owner thread."""
    def __init__(self, spec):
        from ._native import PreparedRace as RustRace
        self._thread = threading.current_thread()
        self._race = RustRace(self._json(spec))

    @staticmethod
    def _json(spec):
        if isinstance(spec, bytes):
            return spec.decode('utf-8')
        return spec if isinstance(spec, str) else json.dumps(spec, separators=(',', ':'))

    def _check(self):
        if threading.current_thread() is not self._thread:
            raise RuntimeError('Use a prepared race only on its creating thread')
        if self._race is None:
            raise RuntimeError('Prepared race has been closed')

    def prepare(self, spec):
        self._check()
        self._race.prepare(self._json(spec))

    def run_wire(self, seed):
        self._check()
        if isinstance(seed, bool) or not isinstance(seed, int) or not -(1 << 63) <= seed < (1 << 63):
            raise ValueError('Seed must be a signed 64-bit integer')
        return self._race.run_wire(seed)

    def run(self, seed):
        return decode(self.run_wire(seed))

    def close(self):
        if self._race is not None:
            self._check()
            self._race.close()
            self._race = None

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *_):
        self.close()
