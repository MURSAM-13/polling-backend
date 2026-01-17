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
settings_col = db.settings

ADMIN_KEY = "admin123"

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4

OPTION_MAP = {
    0: "Option A",
    1: "Option B",
    2: "Option C",
    3: "Option D"
}

# ---------------- HELPER ----------------
def poll_active():
    s = settings_col.find_one({})
    return s and s.get("poll_active", False)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "Polling Backend with Admin Control 🚀"

# ---------- ADMIN START ----------
@app.route("/admin/start", methods=["POST"])
def admin_start():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    settings_col.update_one({}, {"$set": {"poll_active": True}})
    return jsonify(success=True, msg="Poll started")

# ---------- ADMIN END ----------
@app.route("/admin/end", methods=["POST"])
def admin_end():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    settings_col.update_one({}, {"$set": {"poll_active": False}})
    return jsonify(success=True, msg="Poll ended")

# ---------- ADMIN RESET ----------
@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    users_col.delete_many({})
    settings_col.update_one({}, {"$set": {"poll_active": False}})
    return jsonify(success=True, msg="Poll reset")

# ---------- LOGIN ----------
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    return jsonify(success=True)

# ---------- VOTE ----------
@app.route("/vote", methods=["POST"])
def vote():
    if not poll_active():
        return jsonify(success=False, msg="Poll not active")

    username = request.json.get("username")
    option = request.json.get("option")

    if option not in OPTION_MAP:
        return jsonify(success=False, msg="Invalid option")

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    users = list(users_col.find({}, {"option": 1}))

    if len(users) >= MAX_VOTES:
        return jsonify(success=False, msg="Total vote limit reached")

    if sum(1 for u in users if u["option"] == option) >= MAX_PER_OPTION:
        return jsonify(success=False, msg="Option limit reached")

    users_col.insert_one({
        "username": username,
        "option": option
    })

    return jsonify(success=True)

# ---------- RESULTS ----------
@app.route("/results")
def results():
    counts = [0, 0, 0, 0]
    for u in users_col.find({}, {"option": 1}):
        counts[u["option"]] += 1
    return jsonify(counts)

# ---------- USER VOTE AFTER END ----------
@app.route("/my-vote/<username>")
def my_vote(username):
    if poll_active():
        return jsonify(success=False, msg="Poll still active")

    user = users_col.find_one({"username": username})
    if not user:
        return jsonify(success=False, msg="No vote")

    return jsonify(
        success=True,
        voted=OPTION_MAP[user["option"]]
    )

# ---------- GROUPED RESULTS ----------
@app.route("/grouped-results")
def grouped_results():
    grouped = {v: [] for v in OPTION_MAP.values()}
    for u in users_col.find({}, {"username": 1, "option": 1}):
        grouped[OPTION_MAP[u["option"]]].append(u["username"])
    return jsonify(grouped)

# ---------------- START ----------------
if __name__ == "__main__":
    app.run()
