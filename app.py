from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading

app = Flask(__name__)
CORS(app)

LOCK = threading.Lock()

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4
VOTES_FILE = "votes.json"
USERS_FILE = "users.json"

def read_votes():
    with open(VOTES_FILE, "r") as f:
        return json.load(f)

def write_votes(votes):
    with open(VOTES_FILE, "w") as f:
        json.dump(votes, f)

def read_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def write_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

@app.route("/")
def home():
    return "Polling Backend Running 🚀"

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify(success=False, msg="Invalid request"), 400

    users = read_users()
    if data["username"] in users:
        return jsonify(success=False, msg="User already voted")

    return jsonify(success=True)

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    username = data["username"]
    option = data["option"]

    with LOCK:
        votes = read_votes()
        users = read_users()

        if username in users:
            return jsonify(success=False, msg="Already voted")

        if sum(votes) >= MAX_VOTES:
            return jsonify(success=False, msg="Total vote limit reached")

        if votes[option] >= MAX_PER_OPTION:
            return jsonify(success=False, msg="Option limit reached")

        votes[option] += 1
        users.add(username)

        write_votes(votes)
        write_users(users)

    return jsonify(success=True)

@app.route("/results")
def results():
    return jsonify(read_votes())
