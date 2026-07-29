import asyncio
import threading
import unittest
from datetime import datetime
from unittest import mock

from main import Backend
from strings import t
from transcript import TranscriptSession


class _WindowStub:
    def __init__(self):
        self.runtime_events = []

    def push_runtime_state(self, state, message):
        self.runtime_events.append((state, message))


class _FakeThread:
    instances = []

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self._alive = False
        self.__class__.instances.append(self)

    def start(self):
        self._alive = True

    def join(self, timeout=None):
        self._alive = False

    def is_alive(self):
        return self._alive


class BackendControlTests(unittest.TestCase):
    def setUp(self):
        _FakeThread.instances.clear()
        self.window = _WindowStub()
        self.thread_patch = mock.patch("main.threading.Thread", _FakeThread)
        self.thread_patch.start()
        self.backend = Backend(self.window)

    def tearDown(self):
        self.thread_patch.stop()

    def test_start_pause_and_resume(self):
        self.assertTrue(self.backend.start())
        self.assertTrue(self.backend.is_running)
        self.assertEqual(
            self.window.runtime_events[-1],
            ("starting", t("starting_translation")),
        )

        self.assertTrue(self.backend.pause())
        self.assertFalse(self.backend.is_running)
        self.assertEqual(self.backend.state, "paused")
        self.assertEqual(
            self.window.runtime_events[-1], ("paused", t("paused")))

        self.assertTrue(self.backend.resume())
        self.assertTrue(self.backend.is_running)
        self.assertEqual(len(_FakeThread.instances), 2)

    def test_start_is_idempotent_while_active(self):
        self.assertTrue(self.backend.start())
        self.assertFalse(self.backend.start())
        self.assertEqual(len(_FakeThread.instances), 1)

    def test_active_restart_uses_transition_message(self):
        self.backend.start()
        message = "switching target"

        self.assertTrue(self.backend.restart(message))

        self.assertEqual(len(_FakeThread.instances), 2)
        self.assertEqual(
            self.window.runtime_events[-1], ("starting", message))

    def test_restart_preserves_intentional_pause(self):
        self.backend.start()
        self.backend.pause()
        thread_count = len(_FakeThread.instances)

        self.assertFalse(self.backend.restart("should not appear"))

        self.assertEqual(self.backend.state, "paused")
        self.assertEqual(len(_FakeThread.instances), thread_count)
        self.assertEqual(
            self.window.runtime_events[-1], ("paused", t("paused")))

    def test_restart_keeps_the_same_logical_transcript(self):
        recorder = mock.Mock()
        self.backend._recorder = recorder
        self.backend.start()

        self.backend.restart("reconnecting")

        self.assertIs(self.backend._recorder, recorder)
        recorder.close.assert_not_called()

    def test_finish_closes_and_publishes_the_session(self):
        now = datetime.now()
        session = TranscriptSession(
            transcript_path="transcript.md",
            source_text="hello",
            translation_text="",
            started_at=now,
            ended_at=now,
        )
        recorder = mock.Mock()
        recorder.snapshot.return_value = session
        self.backend._recorder = recorder

        result = self.backend.finish_session()

        recorder.close.assert_called_once_with()
        self.assertIs(result, session)
        self.assertIs(self.backend.last_session, session)
        self.assertEqual(self.backend.state, "finished")


class _CancellableBackend(Backend):
    def __init__(self, window):
        super().__init__(window)
        self.pipeline_started = threading.Event()

    async def _pipeline(self):
        with self._state_lock:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()
        self.pipeline_started.set()
        await asyncio.Future()


class BackendThreadLifecycleTests(unittest.TestCase):
    def test_pause_cancels_the_live_pipeline_thread(self):
        backend = _CancellableBackend(_WindowStub())
        backend.start()
        self.assertTrue(backend.pipeline_started.wait(timeout=1))

        self.assertTrue(backend.pause())

        self.assertEqual(backend.state, "paused")
        self.assertIsNone(backend._thread)


if __name__ == "__main__":
    unittest.main()
