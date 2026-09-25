from flask import Flask, jsonify
import time
import math

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Server is running"})


@app.route("/compute")
def compute():
    # CPU-intensive
    result = sum(math.sqrt(i) for i in range(50_000))
    return jsonify({"result": result})


@app.route("/data")
def data():
    # Simulate a DB query with small delay
    time.sleep(0.05)
    payload = {"items": list(range(100)), "count": 100}
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
