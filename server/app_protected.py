from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import math

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute", "30 per second"],
    storage_uri="memory://",
)


@app.route("/")
@limiter.limit("100 per minute")
def index():
    return jsonify({"status": "ok", "message": "Server is running (protected)"})


@app.route("/compute")
@limiter.limit("30 per minute")
def compute():
    result = sum(math.sqrt(i) for i in range(50_000))
    return jsonify({"result": result})


@app.route("/data")
@limiter.limit("60 per minute")
def data():
    time.sleep(0.05)
    payload = {"items": list(range(100)), "count": 100}
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
