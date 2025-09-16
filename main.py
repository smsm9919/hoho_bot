# main.py
from flask import Flask, jsonify
from diag_bingx import auth_and_balance

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/balance")
def balance():
    res = auth_and_balance()
    return (jsonify(res), 200 if res.get("ok") else 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
