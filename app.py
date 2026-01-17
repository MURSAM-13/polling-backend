from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

client = MongoClient(os.getenv("MONGO_URI"))
db = client.polling

users_col = db.users
settings_col = db.settings

ADMIN_KEY = "admin123"

OPTION_MAP = {
    0: "Option A",
    1: "Option B",
    2: "Option C",
    3: "Option D"
}

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4

# ---------- ENSURE SINGLE SETTINGS DOC ----------
def get_settings():
    s = settings_col.find_one()
    if not s:
        settings_col.insert_one({"poll_active": False})
        s = settings_col.find_one()
    return s

def is_poll_active():
    return get_settings()["poll_active"]

# ---------- STATUS ----------
@app.route("/status")
def status():
    return jsonify(poll_active=is_poll_active())

# ---------- ADMIN ----------
@app.route("/admin/start", methods=["POST"])
def admin_start():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    settings_col.update_one({}, {"$set": {"poll_active": True}}, upsert=True)
    return jsonify(success=True, msg="Poll started")

@app.route("/admin/end", methods=["POST"])
def admin_end():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    settings_col.update_one({}, {"$set": {"poll_active": False}}, upsert=True)
    return jsonify(success=True, msg="Poll ended")

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if request.json.get("key") != ADMIN_KEY:
        return jsonify(success=False, msg="Unauthorized"), 403

    users_col.delete_many({})
    settings_col.delete_many({})
    settings_col.insert_one({"poll_active": False})

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
    if not is_poll_active():
        return jsonify(success=False, msg="Poll not active")

    username = request.json.get("username")
    option = request.json.get("option")

    if option not in OPTION_MAP:
        return jsonify(success=False, msg="Invalid option")

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    users = list(users_col.find({"option": {"$exists": True}}))

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
    for u in users_col.find({"option": {"$exists": True}}):
        counts[u["option"]] += 1
    return jsonify(counts)

# ---------- USER RESULTS ----------
@app.route("/user-results")
def user_results():
    res = []
    for u in users_col.find({}, {"_id": 0}):
        if "option" in u:
            res.append({
                "username": u["username"],
                "voted": OPTION_MAP[u["option"]]
            })
    return jsonify(res)

# ---------- GROUPED RESULTS ----------
@app.route("/grouped-results")
def grouped_results():
    grouped = {v: [] for v in OPTION_MAP.values()}
    for u in users_col.find({"option": {"$exists": True}}):
        grouped[OPTION_MAP[u["option"]]].append(u["username"])
    return jsonify(grouped)

# ---------- USER FINAL VOTE ----------
@app.route("/my-vote/<username>")
def my_vote(username):
    if is_poll_active():
        return jsonify(success=False, msg="Poll still active")

    u = users_col.find_one({"username": username})
    if not u or "option" not in u:
        return jsonify(success=False, msg="No vote found")

    return jsonify(success=True, voted=OPTION_MAP[u["option"]])

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
