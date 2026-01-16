from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

MAX_VOTES = 100
MAX_PER_OPTION = MAX_VOTES // 4

votes = [0, 0, 0, 0]
voted_users = set()

# -------- LOGIN --------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data or "username" not in data:
        return jsonify({"success": False, "msg": "Invalid request"}), 400

    username = data["username"]

    if username in voted_users:
        return jsonify({"success": False, "msg": "User already voted"})

    return jsonify({"success": True})


# -------- VOTE --------
@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json(silent=True)

    if not data or "username" not in data or "option" not in data:
        return jsonify({"success": False, "msg": "Invalid request"}), 400

    username = data["username"]
    option = data["option"]

    if username in voted_users:
        return jsonify({"success": False, "msg": "Already voted"})

    if sum(votes) >= MAX_VOTES:
        return jsonify({"success": False, "msg": "Total vote limit reached"})

    if not (0 <= option < 4):
        return jsonify({"success": False, "msg": "Invalid option"}), 400

    if votes[option] >= MAX_PER_OPTION:
        return jsonify({"success": False, "msg": "Option vote limit reached"})

    votes[option] += 1
    voted_users.add(username)

    socketio.emit("update", votes)
    return jsonify({"success": True})


# -------- SOCKET --------
@socketio.on("connect")
def handle_connect():
    socketio.emit("update", votes)


# -------- START --------
if __name__ == "__main__":
    socketio.run(app)

