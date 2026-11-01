"""リポジトリルートで python -m sandbox.dashboard.bkt を実行する。"""
from .alp_app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8054, debug=False)
