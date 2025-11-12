from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": True})  # boolean True pour correspondre au test

if __name__ == "__main__":
    # Écoute sur le port 8888 pour Jenkins
    app.run(host="127.0.0.1", port=8888)
