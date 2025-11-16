from flask import Flask, jsonify, request
from backend.langgraph_agent import MasterAgent

backend_app = Flask(__name__)

@backend_app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Running"}), 200

@backend_app.route('/generate_newspaper', methods=['POST'])
def generate_newspaper():
    data = request.json
    master_agent = MasterAgent()
    language = data.get("language", "english")  # Default to English if not specified
    length = data.get("length", "standard")  # Default to standard if not specified
    newspaper = master_agent.run(data["topics"], data["layout"], language, length)
    return jsonify({"path": newspaper}), 200

