"""旧起動方法の互換入口。新しい入口は python -m sandbox.dashboard.bkt。

旧ポート8051を維持する。bike_app.pyと同じポートなので同時起動しない。
"""
from bkt.alp_app import app, csv_text, import_uploads

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8051, debug=False)
