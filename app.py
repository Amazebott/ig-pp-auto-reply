Python
from flask import Flask, request
import requests

app = Flask(__name__)

ACCESS_TOKEN ="need to fin"              # YOUR_PAGE_ACCESS_TOKEN_HERE
VERIFY_TOKEN = "mysecret123"               # WHAT ELSE TO INCLUDE IN MESSAGE
REPLY_MESSAGE = "Thanks! Check your DM 😊"

GRAPH_URL = "https://graph.facebook.com/v20.0"

@app.route('/')
def home():
    return "IG Bot is running!"

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'entry' in data:
        for entry in data['entry']:
            for change in entry.get('changes', []):
                if change.get('field') == 'comments':
                    comment_id = change['value'].get('id')
                    if comment_id:
                        requests.post(f"{GRAPH_URL}/{comment_id}/replies", data={"message": REPLY_MESSAGE, "access_token": ACCESS_TOKEN})
    return "OK", 200

