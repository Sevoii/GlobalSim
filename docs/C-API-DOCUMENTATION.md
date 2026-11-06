# GlobalSim C API

The C API prepares one race request and runs it repeatedly with different seeds.
It is useful for native applications that need to avoid process startup and JSON
serialization of every result. The public declarations are in
[`include/globalsim.h`](../include/globalsim.h).

## Build and link

Build the shared library from the repository root:

```sh
cargo build --release --locked
```

The library is `target/release/globalsim.dll` on Windows,
`target/release/libglobalsim.so` on Linux, and
`target/release/libglobalsim.dylib` on macOS. Compile with `include` on the
header path, then link the resulting shared library using your platform's normal
dynamic-library mechanism. At runtime, the library directory must be discoverable
by the OS loader; on Windows, placing `globalsim.dll` beside the executable is a
common choice.

Example commands for a source file named `race.c`:

```powershell
cl /I include race.c /link /LIBPATH:target\release globalsim.lib
```

```sh
cc -Iinclude race.c -Ltarget/release -lglobalsim -o race
```

On macOS, add `-Wl,-rpath,@loader_path` when the dylib will live beside your
executable. On Linux, use an rpath or deploy the `.so` in an OS library path.

## Lifetime and threading

`globalsim_new()` creates an opaque `GlobalSimHandle`. Create, prepare, run, read
and free that handle on one thread, without concurrent calls. Separate threads
may each own separate handles. Every successful `globalsim_new()` must eventually
be paired with `globalsim_free()` on that same thread.

`globalsim_data()` and `globalsim_error()` return borrowed pointers. Their values
expire when the handle is prepared again, run again, or freed. Copy the packet
before performing another operation if it must outlive that call.

## Complete example

This program reads a JSON request from `race.json`, prepares it once, and prints
the packet size for three independent seeds. Use the request format documented in
[the interface reference](INTERFACE.md); `examples/v77-race.jsonl` is a
valid starting point.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "globalsim.h"

static void fail(GlobalSimHandle *race, const char *operation) {
    const char *message = globalsim_error(race);
    fprintf(stderr, "%s: %s\n", operation,
            message != NULL ? message : "unknown GlobalSim error");
}

int main(void) {
    FILE *file = fopen("race.json", "rb");
    if (file == NULL) return 1;
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    rewind(file);
    if (length < 0) { fclose(file); return 1; }

    uint8_t *json = malloc((size_t)length);
    if (json == NULL || fread(json, 1, (size_t)length, file) != (size_t)length) {
        free(json); fclose(file); return 1;
    }
    fclose(file);

    GlobalSimHandle *race = globalsim_new();
    if (race == NULL) { free(json); return 1; }
    if (globalsim_prepare(race, json, (size_t)length) != 0) {
        fail(race, "prepare");
        globalsim_free(race);
        free(json);
        return 1;
    }
    free(json); /* GlobalSim has decoded the request. */

    int64_t seeds[] = {100003, 107922, 115841};
    for (size_t i = 0; i < sizeof(seeds) / sizeof(seeds[0]); ++i) {
        if (globalsim_run(race, seeds[i]) != 0) {
            fail(race, "run");
            continue; /* A later valid seed may still be run. */
        }
        size_t size = globalsim_size(race);
        const uint8_t *packet = globalsim_data(race);
        if (packet == NULL || size == 0) {
            fprintf(stderr, "GlobalSim returned an empty packet\n");
            continue;
        }
        /* Consume or copy `packet[0..size)` before the next prepare, run, or free. */
        printf("seed %lld: %zu replay bytes\n", (long long)seeds[i], size);
    }
    globalsim_free(race);
    return 0;
}
```

## Functions and errors

| Function | Result |
|---|---|
| `globalsim_new()` | New handle, or `NULL` if allocation fails. |
| `globalsim_prepare(handle, json, length)` | Decode a UTF-8 JSON request. |
| `globalsim_run(handle, seed)` | Simulate an independent signed 64-bit seed. The retail runtime further requires a signed 32-bit seed. |
| `globalsim_data(handle)` / `globalsim_size(handle)` | Pointer and byte length of the most recent binary replay packet. |
| `globalsim_error(handle)` | NUL-terminated UTF-8 message for the most recent recoverable error. |
| `globalsim_free(handle)` | Release the handle; `NULL` is accepted. |

Status `0` means success. Status `-1` means a recoverable error; use
`globalsim_error()` on a live handle for the description. Status `-2` means the
wrong thread used the handle. A failed preparation clears the preceding prepared
race, and a failed run clears the preceding packet. A later valid `prepare` or
`run` can recover. Do not call the pointer-returning functions with `NULL` or
after `globalsim_free()`.

## Reading a replay packet

`globalsim_run()` returns binary replay format version `GSIMRP01`. It is a
little-endian packet with a 32-byte fixed header, UTF-8 JSON metadata, and packed
float64 frame records:

| Offset | Size | Field |
|---|---:|---|
| 0 | 8 | ASCII `GSIMRP01` |
| 8 | 8 | Metadata byte length (`uint64_t`) |
| 16 | 4 | Frame count (`uint32_t`) |
| 20 | 4 | Runner count (`uint32_t`) |
| 24 | 8 | Payload byte length (`uint64_t`) |

After the header, read exactly the metadata length, then the payload length.
Each frame is one float64 timestamp followed by six float64 values per runner:
position, speed, HP, lane, rushing mode, and front-blocker index. The stride is
`8 + 48 * runner_count` bytes and the payload length must equal
`frame_count * stride`. The metadata is the conventional JSON reply with its
`frames` member omitted. The full [binary replay reference](BINARY-REPLAY.md)
includes wire-level semantics and error packet details.

Avoid casting the packet to a C struct: compilers can add padding and the host
may not be little-endian. Decode integer and float fields explicitly from bytes
or use a protocol reader that validates lengths before allocating or indexing.

## Related APIs

The [Python binding guide](PYTHON-DOCUMENTATION.md) includes `NativeRace`, a
standard-library `ctypes` wrapper over this same C API. Rust applications can use
the prepared Rust API described in [IN-PROCESS.md](IN-PROCESS.md).
