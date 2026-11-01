"""全体テストから、BKTの補助項目モデルのテストを読み込む互換入口。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromName('sandbox.dashboard.bkt.tests.test_assisted_model')
