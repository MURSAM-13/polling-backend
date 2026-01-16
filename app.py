from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

# ---------- MongoDB ----------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.polling
votes_col = db.votes
users_col = db.users

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4

# ---------- INIT ----------
if votes_col.count_documents({}) == 0:
    for i in range(4):
        votes_col.insert_one({"option": i, "count": 0})

# ---------- ROUTES ----------
@app.route("/")
def home():
    return "Polling Backend Running (MongoDB) 🚀"

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="User already voted")

    return jsonify(success=True)

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    username = data["username"]
    option = data["option"]

    if users_col.find_one({"username": username}):
        return jsonify(success=False, msg="Already voted")

    total_votes = sum(v["count"] for v in votes_col.find())
    if total_votes >= MAX_VOTES:
        return jsonify(success=False, msg="Total vote limit reached")

    vote_doc = votes_col.find_one({"option": option})
    if vote_doc["count"] >= MAX_PER_OPTION:
        return jsonify(success=False, msg="Option vote limit reached")

    votes_col.update_one(
        {"option": option},
        {"$inc": {"count": 1}}
    )
    users_col.insert_one({"username": username})

    return jsonify(success=True)

@app.route("/results")
def results():
    data = votes_col.find().sort("option", 1)
    return jsonify([v["count"] for v in data])

# ---------- START ----------
if __name__ == "__main__":
    app.run(debug=True)