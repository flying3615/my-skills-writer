#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_extract_module():
    module_path = Path(__file__).with_name("extract.py")
    spec = importlib.util.spec_from_file_location("daily_press_extract", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    print("scan.py is deprecated; delegating to extract.py", file=sys.stderr)
    module = load_extract_module()
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
