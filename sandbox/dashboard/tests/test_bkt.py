"""互換入口。実体はbkt/tests/test_bkt.py。全体検証の従来コマンドを維持する。"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromName("sandbox.dashboard.bkt.tests.test_bkt")
