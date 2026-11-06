# GlobalSim Python API

## Testing the bindings

Install the package into your virtual environment with `python -m pip install .`
or `maturin develop`, then run from the repository root:

```sh
python -m unittest discover -s tests -p test_python_bindings.py -v
python -m unittest discover -s tests -p test_replay_protocol.py -v
```

The integration suite requires the compiled extension and compares PyO3 packets
byte for byte with the C ABI from the same build across seeds and frame modes.
It also checks input forms, seed bounds, preparation recovery, result ownership,
context cleanup, thread restrictions, and public replay helpers. This verifies
binding correctness; simulation fidelity is covered by the engine regression suite.

The `globalsim` package calls the Rust shared library directly through Python's
PyO3, packaged with Maturin. Python 3.9 or newer is required. There are no Python
runtime dependencies. Installation compiles and bundles the native extension.

## Installation

From the repository root:

```sh
python -m pip install .
```

For development, install Maturin and run `maturin develop --release` inside a virtual environment. Building requires a Rust toolchain,
native linker and (for the default allocator) C compiler. Add
`--no-default-features` to `maturin develop` to use the platform allocator.
Build distributable wheels with `maturin build --release`.

## Prepare once, run multiple seeds

Run this example from the repository root:

```python
import json
from pathlib import Path
from globalsim import PreparedRace

spec = json.loads(Path('../examples/v77-race.jsonl').read_text(encoding='utf-8'))
spec['retainAllFrames'] = True

with PreparedRace(spec) as race:
    for seed in [100003, 107922, 115841]:
        replay = race.run(seed)
        print(replay.metadata)
        if replay.count:
            time, runners = replay.frame(0)
            print(time, runners[:6])
```

Start with the included example to retain the validated runtime settings and
skill table. Request fields and result metadata follow [the interface reference](INTERFACE.md).

## `PreparedRace`

| API | Behavior |
|---|---|
| `PreparedRace(spec)` | Prepare a request dictionary, JSON string, or UTF-8 JSON `bytes`. |
| `prepare(spec)` | Replace the prepared request; returns `None`. |
| `run(seed)` | Simulate one seed and return a `Replay`. |
| `run_wire(seed)` | Simulate one seed and return the complete binary packet as owned `bytes`. |
| `close()` | Free the native handle; repeated calls are harmless. |

Use the context manager to close the handle deterministically, including when
an exception occurs. Without a context manager, call `close()` explicitly.
Create, use and close each handle on the same thread. Independent threads may
create their own handles. Using a closed handle or using it on another thread
raises `RuntimeError`.

Seeds must be Python integers within the signed 64-bit range; the retail runtime
further requires signed 32-bit seeds. Invalid seeds and recoverable engine errors
raise `ValueError`. A missing compiled extension raises `ImportError`. Invalid JSON input
or serialization can also raise Python exceptions. Failed preparation preserves the previous race. Each run starts
with fresh simulation state while reusing prepared setup.

Returned packets and replay views own their Python storage and remain valid
after subsequent runs or closing the handle. Native panics and allocation failures
can terminate the host process; the worker interface provides process isolation.

## `Replay`

| Member | Meaning |
|---|---|
| `metadata` | Result dictionary excluding frame data. |
| `count` | Number of retained frames. |
| `horse_count` | Number of runners per frame. |
| `stride` | Bytes per frame: `8 + 48 * horse_count`. |
| `frames` | Read-only byte `memoryview` for packets returned by the binding. |
| `frame(index)` | `(time, flat_runner_values)` as Python floats; invalid indices raise `IndexError`. |
| `to_json_value()` | Materialize the conventional reply dictionary including frames; nonfinite numbers become `None`. |
| `assert_matches(reference)` | Compare against a conventional reply dictionary; raises `AssertionError` on differences. |

Each frame contains a little-endian float64 timestamp followed by six float64
values per runner, in the order exported as `FIELDS`:
`pos`, `speed`, `hp`, `lane`, `temptationMode`, `blockFrontHorseIndex`.
Runner `i` occupies `flat_runner_values[i * 6:(i + 1) * 6]`.
Frame count can be zero, for example with results-only output.

Optional NumPy access (install NumPy separately):

```python
import numpy as np
rows = np.frombuffer(replay.frames, dtype='<f8').reshape(
    replay.count, 1 + 6 * replay.horse_count
)
times = rows[:, 0]
runners = rows[:, 1:].reshape(replay.count, replay.horse_count, 6)
```

## Binary replay helpers

`decode(wire: bytes) -> Replay` validates and decodes a complete binary packet.
`read_wire(stream, *, max_bytes=134217728) -> bytes` reads one packet from a
blocking binary stream. `read_reply(stream, *, max_bytes=134217728) -> Replay`
reads and decodes one packet. The limit applies to metadata plus frame payload,
excluding the header. Truncated streams raise `EOFError`; malformed packets and
oversized stream replies raise `ValueError`. `decode` has no size-limit argument.
Worker error packets are returned as replay metadata containing `error`.

See [the binary protocol](BINARY-REPLAY.md) for worker configuration and wire
format. Existing repository scripts can continue importing `native_engine` and
`replay_protocol` from `tools`; applications should import `globalsim`.

## Legacy ctypes API

Use `NativeRace(spec=spec)` to load the bundled library automatically. The existing
`NativeRace(library, spec)` form also works. Requests can be dictionaries, JSON
strings, or UTF-8 JSON bytes. Create and close each race on its worker thread.

The compiled `_native` module ships with `_native.pyi` so IDEs can resolve its
classes and methods directly from source. For development, select the virtual
environment where you ran `maturin develop`; the stub supplies type information,
while the compiled extension supplies the runtime implementation.

`NativeRace(library, spec)` remains available for loading an explicitly supplied
C ABI shared library. It accepts dictionaries or JSON bytes and exposes the same
run, run_wire, prepare, close and context manager methods. Unlike `PreparedRace`,
a failed preparation clears its previous race. Build that library using
`cargo build --release --locked`; library loading failures raise `OSError`.
The PyO3 API currently holds the GIL during simulation. Neither API supports
sharing a prepared race across threads.

## Direct C API access

`CGlobalSim` and `CHandle` provide fine-grained access to the exported C API.
This is useful when an application needs status codes, an error message, or the
address and length of the currently borrowed packet. The high-level `NativeRace`
class is built on this API and is preferred for ordinary Python use.

```python
from globalsim import CGlobalSim

# Uses the native extension bundled by `pip install .`.
engine = CGlobalSim()
with engine.new() as handle:
    status = handle.prepare(open("race.json", "rb").read())
    if status != 0:
        raise RuntimeError(handle.error())
    status = handle.run(100003)
    if status != 0:
        raise RuntimeError(handle.error())
    packet = handle.copy_packet()  # Owned bytes, safe after later calls.
```

`prepare()` accepts UTF-8 `str` or any bytes-like value; `run()` accepts a signed
64-bit Python integer. Both return the native status: `0` success, `-1` recoverable
engine error, and `-2` wrong native thread. This wrapper rejects cross-thread
calls before they reach C with `RuntimeError`.

`error()` returns the current C error text or `None`. `data_pointer()` and
`data_size()` return the packet's borrowed address and byte length for zero-copy
foreign-library integration. That address expires on the next `prepare()`,
`run()`, or `close()` call for the same handle. Use `copy_packet()` when Python
must retain the packet. Each Python thread can create and run its own `CHandle`
concurrently; do not share one handle between threads.

Pass a filesystem path to `CGlobalSim(path)` when you instead need to load a
specific externally built C library.

Create handles only through `CGlobalSim.new()`. Handles and `NativeRace` objects
cannot be copied. Use a context manager or explicitly close them on their owning
thread; automatic garbage collection does not free C handles.
