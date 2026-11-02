"""N2全領域モックを使い始める起動入口（01）。既定ポート8058。

python -m sandbox.dashboard.bkt.n2_learning_dashboard_01 --check
python -m sandbox.dashboard.bkt.n2_learning_dashboard_01
画面は検証済みの全領域版を再利用し、既存8055〜8057と併用できる。
"""
import argparse

from .n2_learning_data_01 import load_records, make_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='データ確認だけ行い、サーバーを起動しない')
    parser.add_argument('--port', type=int, default=8058)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('ポートは1〜65535で指定してください。')
    try:
        report = make_summary(load_records())
    except (OSError, ValueError) as error:
        parser.exit(2, f'データを読み込めません: {error}\n')
    total = report['overall']
    print(f"N2全領域モック: {total['Sessions']}回・{total['Answered']:,}回答", flush=True)
    for row in report['domains']:
        print(f"  {row['Domain']}: {row['Correct']}正解 / {row['Answered']}回答", flush=True)
    if args.check:
        return
    from .full_learning_dashboard import app
    app.run(host='127.0.0.1', port=args.port, debug=False)


if __name__ == '__main__':
    main()
