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
votes_col = db.votes
users_col = db.users

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4   # 25 each

# ---------------- INITIALIZE VOTES ----------------
if votes_col.count_documents({}) == 0:
    for i in range(4):
        votes_col.insert_one({
            "option": i,
            "count": 0
        })

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "Polling Backend Running (MongoDB) 🚀"

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

    if not (0 <= option < 4):
        return jsonify(success=False, msg="Invalid option")

    # Check if user already voted
    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    # Total vote limit
    total_votes = sum(v["count"] for v in votes_col.find())
    if total_votes >= MAX_VOTES:
        return jsonify(success=False, msg="Total vote limit reached")

    # Per-option limit
    vote_doc = votes_col.find_one({"option": option})
    if vote_doc["count"] >= MAX_PER_OPTION:
        return jsonify(success=False, msg="Option vote limit reached")

    # Increment vote
    votes_col.update_one(
        {"option": option},
        {"$inc": {"count": 1}}
    )

    # Store user + vote
    users_col.insert_one({
        "username": username,
        "option": option
    })

    return jsonify(success=True)

# ---------- TOTAL RESULTS ----------
@app.route("/results")
def results():
    data = votes_col.find().sort("option", 1)
    return jsonify([v["count"] for v in data])

# ---------- USER-WISE RESULTS ----------
@app.route("/user-results")
def user_results():
    option_map = ["Option A", "Option B", "Option C", "Option D"]

    users = users_col.find({}, {"_id": 0})
    result = []

    for u in users:
        if "option" in u:
            voted = option_map[u["option"]]
        else:
            voted = "Not recorded (old data)"

        result.append({
            "username": u["username"],
            "voted": voted
        })

    return jsonify(result)


# ---------------- START ----------------
if __name__ == "__main__":
    app.run()