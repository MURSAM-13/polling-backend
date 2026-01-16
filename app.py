from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import threading
import os

app = Flask(__name__)
CORS(app)

DB_FILE = "poll.db"
LOCK = threading.Lock()

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4

# ---------- DATABASE INIT ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            option_id INTEGER PRIMARY KEY,
            count INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY
        )
    """)

    for i in range(4):
        cur.execute(
            "INSERT OR IGNORE INTO votes (option_id, count) VALUES (?, ?)",
            (i, 0)
        )

    conn.commit()
    conn.close()

init_db()

# ---------- HELPERS ----------
def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# ---------- ROUTES ----------
@app.route("/")
def home():
    return "Polling Backend Running (SQLite) 🚀"

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data or "username" not in data:
        return jsonify(success=False, msg="Invalid request"), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=?", (data["username"],))
    exists = cur.fetchone()
    conn.close()

    if exists:
        return jsonify(success=False, msg="User already voted")

    return jsonify(success=True)

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json(silent=True)
    username = data["username"]
    option = data["option"]

    with LOCK:
        conn = get_db()
        cur = conn.cursor()

        # Check user
        cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if cur.fetchone():
            conn.close()
            return jsonify(success=False, msg="Already voted")

        # Total votes
        cur.execute("SELECT SUM(count) FROM votes")
        total = cur.fetchone()[0]

        if total >= MAX_VOTES:
            conn.close()
            return jsonify(success=False, msg="Total vote limit reached")

        # Option limit
        cur.execute("SELECT count FROM votes WHERE option_id=?", (option,))
        count = cur.fetchone()[0]

        if count >= MAX_PER_OPTION:
            conn.close()
            return jsonify(success=False, msg="Option vote limit reached")

        # Update
        cur.execute(
            "UPDATE votes SET count=count+1 WHERE option_id=?",
            (option,)
        )
        cur.execute(
            "INSERT INTO users VALUES (?)",
            (username,)
        )

        conn.commit()
        conn.close()

    return jsonify(success=True)

@app.route("/results")
def results():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT count FROM votes ORDER BY option_id")
    votes = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(votes)

# ---------- START ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
