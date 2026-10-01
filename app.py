import os, json, requests, sys
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hey! Thanks for DMing 💛")
COMMENT_MESSAGE = os.getenv("COMMENT_MESSAGE", "Thanks so much! 💛")
COMMENT_DM_PROMPT = os.getenv("COMMENT_DM_PROMPT", "Just sent you the link in DMs! 💛")
LINK_DM_TEMPLATE = os.getenv("LINK_DM_TEMPLATE", "Here you go! {LINK}")
POST_LINKS = json.loads(os.getenv("POST_LINKS_JSON", '{"default": "https://your-link.com"}'))

def send_dm(recipient_id, text):
    print(f"Sending DM to {recipient_id}: {text}", flush=True)
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    r = requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}})
    print(f"Send DM result: {r.status_code} {r.text}", flush=True)
    return r

def reply_to_comment(comment_id, text):
    print(f"Replying to comment {comment_id}: {text}", flush=True)
    url = f"https://graph.facebook.com/v20.0/{comment_id}/replies?access_token={PAGE_ACCESS_TOKEN}"
    r = requests.post(url, json={"message": text})
    print(f"Reply result: {r.status_code} {r.text}", flush=True)
    return r

@app.route('/')
def home():
    return "Bot is running - webhook ready"

@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        return challenge
    return "Verification failed", 403

@app.route('/posts')
def list_posts():
    url = f"https://graph.facebook.com/v20.0/me/media?fields=id,caption,permalink&access_token={PAGE_ACCESS_TOKEN}"
    return requests.get(url).json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received webhook: {data}", flush=True)

    if not data:
        return "OK", 200

    for entry in data.get("entry", []):
        # DM HANDLER - THIS WAS MISSING
        for msg in entry.get("messaging", []):
            sender_id = msg.get("sender", {}).get("id")
            text = msg.get("message", {}).get("text", "")
            print(f"DM from {sender_id}: {text}", flush=True)
            if sender_id and text:
                send_dm(sender_id, WELCOME_MESSAGE)

        # COMMENT HANDLER
        for change in entry.get("changes", []):
           # if change.get("field") in ["comments", "feed"]:
            if change.get("field") in ["comments", "feed", "messages"]:
                val = change.get("value", {})
                media_id = str(val.get("media_id") or val.get("post_id") or "")
                comment_text = val.get("text", "").lower()
                comment_id = val.get("comment_id") or val.get("id")
                from_id = val.get("from", {}).get("id")
                print(f"Comment '{comment_text}' on {media_id}", flush=True)

                if "link" in comment_text and comment_id:
                    link_to_send = POST_LINKS.get(media_id) or POST_LINKS.get("default")
                    reply_to_comment(comment_id, COMMENT_DM_PROMPT)
                    if from_id:
                        send_dm(from_id, LINK_DM_TEMPLATE.replace("{LINK}", link_to_send))
                elif comment_id and val.get("verb") == "add":
                    reply_to_comment(comment_id, COMMENT_MESSAGE)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
