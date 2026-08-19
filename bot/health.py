import os
from threading import Thread

from flask import Flask


app = Flask(__name__)


@app.route("/")
def home():
    return "RSS-Sky-Mvz Bot is running.", 200


@app.route("/health")
def health():
    return "OK", 200


def run_health_server():
    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )


def start_health_server():
    thread = Thread(
        target=run_health_server,
        daemon=True,
    )

    thread.start()
