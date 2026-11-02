"""N2全領域モックを使うための読込・集計入口（01）。標準ライブラリのみ。

リポジトリルートから python -m sandbox.dashboard.bkt.n2_learning_data_01
新しい画面からは load_records / make_summary を呼び出す。
"""
import argparse
import json
from pathlib import Path

from .dashboard_data import filter_records, load_learning_data, summarize
from .full_mock_dataset import DATABASE

DOMAINS = ('言語知識', '読解', '聴解')


def load_records(database=DATABASE):
    """ローカルSQLiteを読み取り専用で開く。生成・上書きは行わない。"""
    return load_learning_data(database=Path(database))


def make_summary(records, *, domain='__all__', group='__all__', skill='__all__',
                 session='__all__', start=None, end=None):
    """全体・領域・実施回の集計。元の回答を変更しない。"""
    selected = filter_records(records, domain=domain, group=group, skill=skill,
                              session=session, start=start, end=end)
    sessions = dict.fromkeys(r['SessionID'] for r in selected)
    return {
        'filters': dict(domain=domain, group=group, skill=skill, session=session, start=start, end=end),
        'overall': summarize(selected),
        'domains': [{'Domain':name, **summarize([r for r in selected if r['CategoryLevel1']==name])}
                    for name in DOMAINS],
        'sessions': [{'SessionID':sid, 'SessionNumber':rows[0]['SessionNumber'],
                      'Date':rows[0]['SessionDate'], **summarize(rows)}
                     for sid in sessions
                     for rows in [[r for r in selected if r['SessionID']==sid]]],
        'notes': ['架空データ。公式尺度得点や合否判定ではありません。',
                  '自信度は1高〜4低。解説後理解度は自己申告0低〜3高。',
                  'モデル試算は独立回答・手動仮定で、累積習得率ではありません。'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DATABASE)
    parser.add_argument('--domain', choices=DOMAINS, help='省略すると全領域')
    parser.add_argument('--start', help='開始日 YYYY-MM-DD')
    parser.add_argument('--end', help='終了日 YYYY-MM-DD')
    args = parser.parse_args(argv)
    try:
        report = make_summary(load_records(args.database), domain=args.domain or '__all__',
                              start=args.start, end=args.end)
    except (OSError, ValueError) as error:
        parser.exit(2, f'読み込めません: {error}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
