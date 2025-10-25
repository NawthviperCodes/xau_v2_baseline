from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow requests from your frontend

@app.route('/')
def home():
    return jsonify({"message": "Backend is running!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    api_token = data.get("token")
    server = data.get("server")

    if not api_token or not server:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    # TODO: Here you can connect this with your Deriv API logic
    return jsonify({
        "success": True,
        "message": "Login successful!",
        "account": "Demo Account",
        "balance": 1000.50
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
