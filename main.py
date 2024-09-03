from flask import Flask, jsonify, request

app = Flask(__name__)

# Home route
@app.route('/')
def home():
    return "Welcome to the Flask app!"

# Example route that returns a JSON response
@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message="Hello, World!")

# Example route with a dynamic parameter
@app.route('/api/greet/<name>', methods=['GET'])
def greet(name):
    return jsonify(message=f"Hello, {name}!")

# Example route that accepts POST requests
@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.json
    return jsonify(received=data)

if __name__ == '__main__':
    app.run(debug=True)
