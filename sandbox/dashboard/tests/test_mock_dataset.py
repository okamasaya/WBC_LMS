"""全体テストからJLPT N2のモックデータ検証を読み込む。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromName('sandbox.dashboard.bkt.tests.test_mock_dataset')
