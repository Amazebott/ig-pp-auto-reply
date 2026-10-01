import os, json, requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "").strip()
IG_TOKEN = os.getenv("IG_ACCESS_TOKEN","").strip()  # IGAA token for parentingpulse.pp - ME IS

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hey! Thanks for DMing 💛")
COMMENT_MESSAGE = os.getenv("COMMENT_MESSAGE", "Thanks so much! 💛")
COMMENT_DM_PROMPT = os.getenv("COMMENT_DM_PROMPT", "Just sent you the link in DMs! 💛")
LINK_DM_TEMPLATE = os.getenv("LINK_DM_TEMPLATE", "Here you go! {LINK}")
POST_LINKS = json.loads(os.getenv("POST_LINKS_JSON", '{"default": "https://your-link.com"}'))

def send_dm(recipient_id, text):
    if not recipient_id:
        return None
    rid = str(recipient_id).strip("{}'\" ")
    if rid in ["0", "23245", "12334"]:
        print(f"Skipping fake test ID {rid}", flush=True)
        return None
    print(f"Sending DM to {rid}: {text}", flush=True)
    url = f"https://graph.instagram.com/v20.0/me/messages"
    payload = {
        "access_token": IG_TOKEN,
        "recipient": json.dumps({"id": rid}),
        "message": json.dumps({"text": text})
    }
    r = requests.post(url, data=payload)
    print(f"Send DM result: {r.status_code} {r.text}", flush=True)
    return r

def reply_to_comment(comment_id, text):
    print(f"Replying to comment {comment_id}: {text}", flush=True)
    url = f"https://graph.instagram.com/v20.0/{comment_id}/replies"
    r = requests.post(url, data={"access_token": IG_TOKEN, "message": text})
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

@app.route('/debug-subscription')
def debug_sub():
    r = requests.post(
        f"https://graph.instagram.com/v20.0/me/subscribed_apps",
        data={"access_token": IG_TOKEN, "subscribed_fields": "messages"}
    )
    return r.text

@app.route('/debug-status')
def debug_status():
    r = requests.get(f"https://graph.instagram.com/v20.0/me/subscribed_apps", params={"access_token": IG_TOKEN})
    r2 = requests.get(f"https://graph.instagram.com/v20.0/me?fields=id,username", params={"access_token": IG_TOKEN})
    return f"SUBSCRIBED: {r.text}<br><br>ME IS: {r2.text}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received webhook: {json.dumps(data)[:3000]}", flush=True)
    if not data:
        return "OK", 200
    for entry in data.get("entry", []):
        if str(entry.get("id","")) == "0":
            print("Meta TEST id=0 ignore", flush=True)
            continue
        for msg in entry.get("messaging", []):
            if msg.get("message", {}).get("is_echo"):
                continue
            sender_id = msg.get("sender", {}).get("id")
            text = msg.get("message", {}).get("text", "")
            print(f"DM from {sender_id}: {text}", flush=True)
            if sender_id:
                send_dm(sender_id, WELCOME_MESSAGE)
        for change in entry.get("changes", []):
            field = change.get("field")
            val = change.get("value", {})
            if field == "messages":
                sender_obj = val.get("sender", {})
                sender_id = sender_obj.get("id") if isinstance(sender_obj, dict) else sender_obj
                if sender_id:
                    send_dm(str(sender_id).strip("{}'\" "), WELCOME_MESSAGE)
            elif field in ["comments","feed"]:
                comment_text = val.get("text","").lower()
                comment_id = val.get("comment_id") or val.get("id")
                from_id = val.get("from", {}).get("id")
                media_id = str(val.get("media_id") or val.get("post_id") or "")
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
