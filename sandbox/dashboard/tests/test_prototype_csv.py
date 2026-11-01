"""現行prototype CSVとBKTの接続確認を全体テストに含める。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromName('sandbox.dashboard.bkt.tests.test_prototype_csv')
