import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock


SCAN_MODULE_PATH = Path("/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py")


def load_scan_module():
    spec = importlib.util.spec_from_file_location("daily_press_scan", SCAN_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScanWrapperTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_main_delegates_to_extract_main(self):
        extract_main = mock.Mock(return_value=0)

        with mock.patch.object(self.scan, "load_extract_module", return_value=mock.Mock(main=extract_main)):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = self.scan.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("deprecated", stderr.getvalue().lower())
        extract_main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
