from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# ---------------- SETUP ----------------
load_dotenv()

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client.polling
users_col = db.users

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4  # 25 per option

OPTION_MAP = {
    0: "Option A",
    1: "Option B",
    2: "Option C",
    3: "Option D"
}

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "Polling Backend Running (MongoDB – Dynamic Count) 🚀"

# ---------- LOGIN ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify(success=False, msg="Username required"), 400

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="User already voted")

    return jsonify(success=True)

# ---------- VOTE ----------
@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    username = data.get("username")
    option = data.get("option")

    if username is None or option is None:
        return jsonify(success=False, msg="Invalid request"), 400

    if option not in OPTION_MAP:
        return jsonify(success=False, msg="Invalid option")

    # One vote per user
    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    # Get all votes dynamically
    users = list(users_col.find({}, {"option": 1}))
    total_votes = len(users)

    if total_votes >= MAX_VOTES:
        return jsonify(success=False, msg="Total vote limit reached")

    # Count votes per option
    option_count = sum(1 for u in users if u.get("option") == option)
    if option_count >= MAX_PER_OPTION:
        return jsonify(success=False, msg="Option vote limit reached")

    # Store vote
    users_col.insert_one({
        "username": username,
        "option": option
    })

    return jsonify(success=True)

# ---------- TOTAL RESULTS (DYNAMIC) ----------
@app.route("/results")
def results():
    counts = [0, 0, 0, 0]

    users = users_col.find({}, {"option": 1})
    for u in users:
        if "option" in u:
            counts[u["option"]] += 1

    return jsonify(counts)

# ---------- USER-WISE RESULTS ----------
@app.route("/user-results")
def user_results():
    users = users_col.find({}, {"_id": 0})
    result = []

    for u in users:
        voted = OPTION_MAP[u["option"]] if "option" in u else "Not recorded"
        result.append({
            "username": u["username"],
            "voted": voted
        })

    return jsonify(result)

# ---------- GROUPED RESULTS ----------
@app.route("/grouped-results")
def grouped_results():
    grouped = {
        "Option A": [],
        "Option B": [],
        "Option C": [],
        "Option D": []
    }

    users = users_col.find({}, {"_id": 0})

    for u in users:
        if "option" in u:
            grouped[OPTION_MAP[u["option"]]].append(u["username"])

    for k in grouped:
        grouped[k].sort()

    return jsonify(grouped)

# ---------------- START ----------------
if __name__ == "__main__":
    app.run()
