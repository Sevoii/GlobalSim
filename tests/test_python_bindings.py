"""Integration tests: install with Maturin, then run unittest discovery on this file."""
from concurrent.futures import ThreadPoolExecutor
import io
import copy
import threading
import json
from pathlib import Path
import unittest

from globalsim import CGlobalSim, CHandle, FIELDS, NativeRace, PreparedRace, RaceRequest, decode, read_reply, read_wire
from globalsim import _native


class PreparedRaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((Path(__file__).resolve().parents[1] /
                               'examples/v77-race.jsonl').read_text(encoding='utf-8'))
        with PreparedRace(cls.spec) as race:
            cls.reference = race.run_wire(100003)

    def test_matches_c_abi_across_seeds_and_frame_modes(self):
        # The extension also exports the C ABI: compare independent binding paths
        # against exactly the same engine build, without requiring a second DLL.
        for dense in (False, True):
            spec = dict(self.spec, retainAllFrames=dense)
            with PreparedRace(spec) as python, NativeRace(_native.__file__, spec) as c:
                for seed in (100003, 107922, 100003):
                    with self.subTest(dense=dense, seed=seed):
                        self.assertEqual(python.run_wire(seed), c.run_wire(seed))

    def test_typed_request_roundtrip_and_frames(self):
        request = RaceRequest.from_dict(self.spec)
        self.assertEqual(request.to_dict(), self.spec)
        for factory in (lambda: PreparedRace(request), lambda: NativeRace(spec=request)):
            with factory() as race:
                replay = race.run(100003)
                self.assertEqual(race.run_wire(100003), self.reference)
                frame = replay.typed_frame(0)
                time, values = replay.frame(0)
                self.assertEqual(frame.time, time)
                self.assertEqual(frame.horses[0].position, values[0])
                self.assertEqual(frame.horses[0].block_front_horse_index, values[5])
                with self.assertRaises(IndexError):
                    replay.typed_frame(replay.count)

    def test_direct_c_api_status_packet_and_recovery(self):
        # Omitting a library uses the extension bundled in the installed wheel.
        engine = CGlobalSim()
        with engine.new() as handle:
            self.assertEqual(handle.prepare(json.dumps(self.spec)), 0)
            self.assertEqual(handle.run(100003), 0)
            self.assertEqual(handle.data_size(), len(self.reference))
            self.assertIsInstance(handle.data_pointer(), int)
            self.assertEqual(handle.copy_packet(), self.reference)
            self.assertIsNone(handle.error())
            self.assertEqual(handle.run(1 << 31), -1)
            self.assertIn('signed 32-bit', handle.error())
            self.assertEqual(handle.data_size(), 0)
            self.assertIsNone(handle.data_pointer())
            self.assertEqual(handle.run(100003), 0)
            self.assertEqual(handle.copy_packet(), self.reference)

    def test_c_input_validation_and_ownership(self):
        with self.assertRaises(TypeError):
            CHandle(None, 123)
        with CGlobalSim().new() as handle:
            for invalid in (1000000, True, [123, 125], {}, None):
                with self.subTest(value=invalid), self.assertRaises(TypeError):
                    handle.prepare(invalid)
            wire = json.dumps(self.spec).encode()
            for value in (wire, bytearray(wire), memoryview(wire)):
                self.assertEqual(handle.prepare(value), 0)
            for duplicate in (copy.copy, copy.deepcopy):
                with self.assertRaises(TypeError):
                    duplicate(handle)
            self.assertEqual(handle.run(100003), 0)

    def test_native_race_default_library_and_input_forms(self):
        text = json.dumps(self.spec)
        for spec in (self.spec, text, text.encode()):
            with NativeRace(spec=spec) as race:
                self.assertEqual(race.run_wire(100003), self.reference)
                for duplicate in (copy.copy, copy.deepcopy):
                    with self.assertRaises(TypeError):
                        duplicate(race)

    def test_c_backends_parallel_results(self):
        barrier = threading.Barrier(2)
        def run(case, direct, parallel):
            spec = dict(self.spec, retainAllFrames=bool(case))
            if direct:
                with CGlobalSim().new() as handle:
                    self.assertEqual(handle.prepare(json.dumps(spec)), 0)
                    if parallel:
                        barrier.wait(timeout=30)
                    packets = []
                    for seed in (100003, 107922, 100003):
                        self.assertEqual(handle.run(seed), 0)
                        packets.append(handle.copy_packet())
                    return packets
            with NativeRace(spec=spec) as race:
                if parallel:
                    barrier.wait(timeout=30)
                return [race.run_wire(seed) for seed in (100003, 107922, 100003)]
        for direct in (False, True):
            expected = [run(case, direct, False) for case in (0, 1)]
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(run, case, direct, True) for case in (0, 1)]
                self.assertEqual([future.result(timeout=30) for future in futures], expected)

    def test_c_backends_reject_cross_thread_access(self):
        with CGlobalSim().new() as handle, NativeRace(spec=self.spec) as race:
            self.assertEqual(handle.prepare(json.dumps(self.spec)), 0)
            operations = (lambda: handle.prepare('{}'), lambda: handle.run(1),
                          handle.error, handle.data_pointer, handle.data_size,
                          handle.copy_packet, handle.close, handle.__enter__,
                          lambda: race.prepare({}), lambda: race.run(1),
                          race.close, race.__enter__)
            with ThreadPoolExecutor(1) as pool:
                for operation in operations:
                    with self.assertRaisesRegex(RuntimeError, 'creating thread'):
                        pool.submit(operation).result(timeout=30)
            self.assertEqual(handle.run(100003), 0)
            self.assertEqual(handle.copy_packet(), self.reference)
            self.assertEqual(race.run_wire(100003), self.reference)

    def test_direct_c_api_preparation_failure_and_closed_handle(self):
        engine = CGlobalSim(_native.__file__)
        handle = engine.new()
        self.assertEqual(handle.prepare(json.dumps(self.spec)), 0)
        self.assertEqual(handle.prepare(b'{}'), -1)
        self.assertIsNotNone(handle.error())
        self.assertEqual(handle.run(100003), -1)
        self.assertEqual(handle.close(), 0)
        self.assertEqual(handle.close(), 0)
        for method in (lambda: handle.error(), lambda: handle.data_size(),
                       lambda: handle.prepare(self.spec), lambda: handle.run(1)):
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                method()

    def test_request_dictionary_string_and_bytes(self):
        text = json.dumps(self.spec)
        for spec in (self.spec, text, text.encode('utf-8')):
            with self.subTest(kind=type(spec).__name__), PreparedRace(spec) as race:
                self.assertEqual(race.run_wire(100003), self.reference)

    def test_reprepare_changes_setup_and_matches_fresh_handle(self):
        changed = dict(self.spec, retainAllFrames=True)
        with PreparedRace(self.spec) as race, PreparedRace(changed) as fresh:
            race.prepare(changed)
            self.assertEqual(race.run_wire(100003), fresh.run_wire(100003))
            race.prepare(self.spec)
            self.assertEqual(race.run_wire(100003), self.reference)

    def test_invalid_preparation_preserves_previous_race(self):
        with PreparedRace(self.spec) as race:
            for spec in ({}, '{', b'\xff', {'bad': object()}):
                with self.subTest(spec=repr(spec)):
                    with self.assertRaises((ValueError, TypeError)):
                        race.prepare(spec)
                    self.assertEqual(race.run_wire(100003), self.reference)

    def test_invalid_constructor(self):
        for spec in ({}, '{', b'\xff'):
            with self.subTest(spec=repr(spec)), self.assertRaises(ValueError):
                PreparedRace(spec)

    def test_seed_validation_and_recovery(self):
        with PreparedRace(self.spec) as race:
            for seed in (True, False, 1.5, '1', None, -(1 << 63) - 1, 1 << 63,
                         -(1 << 31) - 1, 1 << 31):
                with self.subTest(seed=seed), self.assertRaises(ValueError):
                    race.run(seed)
            self.assertEqual(race.run_wire(100003), self.reference)
            for seed in (-(1 << 31), (1 << 31) - 1):
                with self.subTest(seed=seed):
                    self.assertIsInstance(race.run_wire(seed), bytes)

    def test_owned_replay_survives_runs_preparation_and_close(self):
        with PreparedRace(self.spec) as race:
            replay = race.run(100003)
            expected = replay.to_json_value()
            self.assertGreater(replay.count, 0)
            first = replay.frame(0)
            race.run(107922)
            race.prepare(dict(self.spec, retainAllFrames=True))
            race.run(115841)
        self.assertEqual(replay.to_json_value(), expected)
        self.assertEqual(replay.frame(0), first)
        self.assertTrue(replay.frames.readonly)
        with self.assertRaises(TypeError):
            replay.frames[0] = 0

    def test_context_exception_closes_handle(self):
        race = PreparedRace(self.spec)
        with self.assertRaisesRegex(LookupError, 'sentinel'):
            with race:
                raise LookupError('sentinel')
        race.close()
        for operation in (lambda: race.run(1), lambda: race.run_wire(1),
                          lambda: race.prepare(self.spec), race.__enter__):
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                operation()

    def test_cross_thread_operations_rejected_and_owner_still_works(self):
        with PreparedRace(self.spec) as race, ThreadPoolExecutor(1) as pool:
            for operation in (lambda: race.run(1), lambda: race.run_wire(1),
                              lambda: race.prepare(self.spec), race.close, race.__enter__):
                with self.assertRaisesRegex(RuntimeError, 'creating thread'):
                    pool.submit(operation).result(timeout=30)
            self.assertEqual(race.run_wire(100003), self.reference)

    def test_independent_thread_handles(self):
        def run(seed):
            with PreparedRace(self.spec) as race:
                return race.run_wire(seed)
        seeds = (100003, 107922)
        with ThreadPoolExecutor(2) as pool:
            actual = list(pool.map(run, seeds))
        self.assertEqual(actual, [run(seed) for seed in seeds])

    def test_public_replay_helpers_and_frame_layout(self):
        replay = decode(self.reference)
        self.assertEqual(read_wire(io.BytesIO(self.reference)), self.reference)
        read_reply(io.BytesIO(self.reference)).assert_matches(replay.to_json_value())
        self.assertEqual(len(replay.frames), replay.count * replay.stride)
        frame = replay.to_json_value()['frames'][0]
        time, values = replay.frame(0)
        self.assertEqual(time, frame['t'])
        self.assertEqual(len(values), 6 * replay.horse_count)
        self.assertEqual(dict(zip(FIELDS, values[:6])), frame['horses'][0])
        for index in (-1, replay.count):
            with self.assertRaises(IndexError):
                replay.frame(index)


if __name__ == '__main__':
    unittest.main()
