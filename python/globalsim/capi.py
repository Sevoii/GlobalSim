"""Direct, thread-confined access to the GlobalSim C ABI through ctypes."""
import ctypes
from pathlib import Path
import threading
from . import _native


class CGlobalSim:
    """Load a GlobalSim C shared library and create independent C handles."""
    def __init__(self, library=None):
        """Load ``library``, or the Maturin-installed extension when omitted."""
        if library is None:
            library = _native.__file__
        self._lib = ctypes.CDLL(str(Path(library).resolve()))
        signatures = {
            'globalsim_new': (ctypes.c_void_p, []),
            'globalsim_prepare': (ctypes.c_int32, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]),
            'globalsim_run': (ctypes.c_int32, [ctypes.c_void_p, ctypes.c_int64]),
            'globalsim_data': (ctypes.c_void_p, [ctypes.c_void_p]),
            'globalsim_size': (ctypes.c_size_t, [ctypes.c_void_p]),
            'globalsim_error': (ctypes.c_char_p, [ctypes.c_void_p]),
            'globalsim_free': (ctypes.c_int32, [ctypes.c_void_p]),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(self._lib, name)
            function.restype, function.argtypes = result, arguments

    def new(self):
        """Allocate a thread-confined :class:`CHandle`."""
        result = object.__new__(CHandle)
        result._lib = self._lib
        result._thread = threading.current_thread()
        handle = self._lib.globalsim_new()
        if not handle:
            raise MemoryError('GlobalSim could not allocate a handle')
        result._handle = handle
        return result


class CHandle:
    """A direct C-ABI handle with explicit status and packet lifetime control.

    Create, use, and close a handle on the thread that created it. Methods that
    invoke the C ABI return its status code: 0 is success, -1 is a recoverable
    engine error, and -2 is reserved by the ABI for an incorrect native thread.
    This wrapper rejects cross-thread use with ``RuntimeError`` before calling C.
    """
    def __init__(self, *args, **kwargs):
        raise TypeError('Create handles with CGlobalSim.new()')

    def __copy__(self):
        raise TypeError('C handles cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('C handles cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('C handles cannot be serialized')

    def _check(self):
        if threading.current_thread() is not self._thread:
            raise RuntimeError('Use a C handle only on its creating thread')
        if self._handle is None:
            raise RuntimeError('C handle has been closed')

    @staticmethod
    def _wire(json):
        if isinstance(json, str):
            return json.encode('utf-8')
        try:
            return memoryview(json).tobytes()
        except (TypeError, ValueError) as error:
            raise TypeError('JSON input must be str or bytes-like') from error

    def prepare(self, json):
        """Prepare UTF-8 JSON and return its C status code.

        The input is copied by the engine during this call. A status of -1 clears
        the previously prepared race; retrieve the message with :meth:`error`.
        """
        self._check()
        wire = self._wire(json)
        buffer = ctypes.create_string_buffer(wire)
        return self._lib.globalsim_prepare(self._handle, buffer, len(wire))

    def run(self, seed):
        """Run one signed-64-bit seed and return its C status code."""
        self._check()
        if isinstance(seed, bool) or not isinstance(seed, int) or not -(1 << 63) <= seed < (1 << 63):
            raise ValueError('Seed must be a signed 64-bit integer')
        return self._lib.globalsim_run(self._handle, seed)

    def error(self):
        """Return the current C error message, or ``None`` if no message exists."""
        self._check()
        message = self._lib.globalsim_error(self._handle)
        return message.decode('utf-8') if message else None

    def data_pointer(self):
        """Return the borrowed packet address as an integer, or ``None`` when empty."""
        self._check()
        # Vec::as_ptr may be non-null even when its length is zero. The C ABI
        # pointer is only meaningful together with a nonzero returned size.
        if not self._lib.globalsim_size(self._handle):
            return None
        return self._lib.globalsim_data(self._handle) or None

    def data_size(self):
        """Return the byte length of the borrowed binary replay packet."""
        self._check()
        return self._lib.globalsim_size(self._handle)

    def copy_packet(self):
        """Copy the current binary replay packet into owned Python ``bytes``.

        The native packet pointer remains valid only until the next ``prepare``,
        ``run``, or ``close`` on this handle.
        """
        self._check()
        size, pointer = self.data_size(), self.data_pointer()
        if not size or pointer is None:
            return b''
        return ctypes.string_at(pointer, size)

    def close(self):
        """Free the native handle. Closing an already closed handle is harmless."""
        if self._handle is None:
            return 0
        self._check()
        status = self._lib.globalsim_free(self._handle)
        if status == 0:
            self._handle = None
        return status

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *_):
        self.close()
