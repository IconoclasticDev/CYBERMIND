import time
import unittest

from app.services.scenario_runner import ScenarioService


class ScenarioThreadLifecycleTest(unittest.TestCase):
    def test_completed_and_stopped_threads_allow_health_status_and_restart(self):
        service = ScenarioService(lambda _id, _tick, _events: None, lambda _message: None)
        self.assertEqual(service.start("benign_baseline", interval=0.3, speed=100)["status"], "started")
        service.runner.join(timeout=5)
        self.assertFalse(service.runner.is_alive())
        self.assertFalse(service.status()["running"])
        self.assertEqual(service.start("benign_baseline", interval=0.3, speed=1)["status"], "started")
        time.sleep(0.05)
        self.assertEqual(service.stop()["status"], "stopped")
        self.assertFalse(service.status()["running"])


if __name__ == "__main__":
    unittest.main()
