import os
from multiprocessing import Process

from dotenv import load_dotenv
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from backend.server import backend_app

load_dotenv()
CORS(backend_app)

# Get configurable ports from environment with defaults
FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 5000))
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 8000))


frontend_app = Flask(__name__, static_folder='frontend')

@frontend_app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@frontend_app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('frontend', path)

@frontend_app.route('/outputs/<path:path>')
def serve_outputs(path):
    return send_from_directory('outputs', path)

@frontend_app.route('/api/config')
def get_config():
    """Return configuration for frontend including backend port"""
    return jsonify({
        "backendPort": BACKEND_PORT,
        "frontendPort": FRONTEND_PORT
    })


def run_frontend():
    frontend_app.run(host='0.0.0.0', port=FRONTEND_PORT)

def run_backend():
    backend_app.run(host='0.0.0.0', port=BACKEND_PORT)

if __name__ == '__main__':
    # Start the backend server
    backend_process = Process(target=run_backend)
    backend_process.start()

    # Start the frontend server
    frontend_process = Process(target=run_frontend)
    frontend_process.start()

    # Join the processes so that the main process waits for them to complete
    backend_process.join()
    frontend_process.join()
