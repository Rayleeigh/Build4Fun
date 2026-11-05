import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'api' / 'server.py'
spec = importlib.util.spec_from_file_location('teaching_api', PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class MetricTests(unittest.TestCase):
    def test_missing_cgroups_does_not_leak_host_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            value = api.Measurements(directory).metrics()
            self.assertIsNone(value['cpu_percent'])
            self.assertIsNone(value['memory_used_bytes'])
            self.assertIsNone(value['memory_limit_bytes'])
            self.assertGreaterEqual(value['uptime_seconds'], 0)

    def test_cpu_normalizes_to_quota_and_cpuset_and_memory_reports_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in {'cpu.stat': 'usage_usec 1000000', 'cpu.max': '50000 100000',
                                'cpuset.cpus.effective': '0-3', 'memory.current': '1234', 'memory.max': '4096'}.items():
                (root / name).write_text(value)
            with patch.object(api.time, 'monotonic', side_effect=[0, 1, 3]):
                measurements = api.Measurements(directory)
                self.assertIsNone(measurements.metrics()['cpu_percent'])
                (root / 'cpu.stat').write_text('usage_usec 1500000')
                value = measurements.metrics()
            self.assertEqual(value['cpu_percent'], 50)
            self.assertEqual(value['memory_used_bytes'], 1234)
            self.assertEqual(value['memory_limit_bytes'], 4096)
            self.assertEqual(value['uptime_seconds'], 3)
            (root / 'memory.max').write_text('max')
            self.assertIsNone(measurements.metrics()['memory_limit_bytes'])

    def test_cpuset_limits_capacity_when_quota_is_larger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in {'cpu.stat': 'usage_usec 0', 'cpu.max': '400000 100000', 'cpuset.cpus.effective': '0,2'}.items():
                (root / name).write_text(value)
            with patch.object(api.time, 'monotonic', side_effect=[0, 1, 2]):
                measurements = api.Measurements(directory)
                measurements.metrics()
                (root / 'cpu.stat').write_text('usage_usec 1000000')
                self.assertEqual(measurements.metrics()['cpu_percent'], 50)
