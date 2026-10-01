
from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Render will inject these secretly, not in GitHub
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "parentingpulse123")
ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
REPLY_MESSAGE = os.environ.get("WELCOME_MESSAGE", "Hey! Welcome to Parenting Pulse 💛 Thanks for your message!")

GRAPH_URL = "https://graph.facebook.com/v20.0"

@app.route('/')
def home():
    # Support verification on root too
    if request.args.get("hub.mode") == "subscribe":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Failed", 403
    return "IG Bot is running! Use /webhook as Callback URL"

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        print("WEBHOOK VERIFIED")
        return request.args.get("hub.challenge"), 200
    return "Failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for msg in entry.get("messaging", []):
                sender_id = msg.get("sender", {}).get("id")
                if msg.get("message") and not msg["message"].get("is_echo") and sender_id:
                    print(f"DM from {sender_id}")
                    try:
                        requests.post(
                            f"{GRAPH_URL}/me/messages",
                            params={"access_token": ACCESS_TOKEN},
                            json={
                                "recipient": {"id": sender_id},
                                "message": {"text": REPLY_MESSAGE}
                            }
                        )
                    except Exception as e:
                        print(e)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
