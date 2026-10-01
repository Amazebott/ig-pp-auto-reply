import os, json, requests, sys
from flask import Flask, request

app = Flask(__name__)

#@app.route('/debug-subscription')
#def debug_sub():
#    import requests
 #   IG_USER_ID = os.environ.get('IG_USER_ID')
 #   TOKEN = os.environ.get('IG_ACCESS_TOKEN')
  #  r = requests.post(
  #      f"https://graph.instagram.com/v20.0/{IG_USER_ID}/subscribed_apps",
  #      data={"access_token": TOKEN}
  #  )
  #  return r.text

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "").strip()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "").strip()

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hey! Thanks for DMing 💛")
COMMENT_MESSAGE = os.getenv("COMMENT_MESSAGE", "Thanks so much! 💛")
COMMENT_DM_PROMPT = os.getenv("COMMENT_DM_PROMPT", "Just sent you the link in DMs! 💛")
LINK_DM_TEMPLATE = os.getenv("LINK_DM_TEMPLATE", "Here you go! {LINK}")
POST_LINKS = json.loads(os.getenv("POST_LINKS_JSON", '{"default": "https://your-link.com"}'))

def send_dm(recipient_id, text):
    if not recipient_id:
        print("send_dm skipped - no recipient_id", flush=True)
        return None
    # skip fake Meta test ids
    if str(recipient_id) in ["0", "23245", "12334"]:
        print(f"Skipping send to fake test ID {recipient_id}", flush=True)
        return None

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
        # --- FIX: Ignore Meta dashboard test button ---
        entry_id = str(entry.get("id", ""))
        if entry_id == "0":
            print("✅ Meta dashboard TEST event (id=0) - returning 200 OK without sending", flush=True)
            continue

        # DM HANDLER - real DMs via messaging array
        for msg in entry.get("messaging", []):
            sender_id = msg.get("sender", {}).get("id")
            text = msg.get("message", {}).get("text", "")
            print(f"DM from {sender_id}: {text}", flush=True)
            if sender_id and text:
                send_dm(sender_id, WELCOME_MESSAGE)

        # COMMENT + DM via changes HANDLER
        for change in entry.get("changes", []):
            field = change.get("field")
            if field not in ["comments", "feed", "messages"]:
                continue

            # --- DM HANDLER (Meta test + real DMs as field=messages) ---
            if field == "messages":
                val = change.get("value", {})
                sender_obj = val.get("sender", {})
                if isinstance(sender_obj, dict):
                    sender_id = sender_obj.get("id") or next(iter(sender_obj.keys()), None)
                else:
                    sender_id = sender_obj
                
                msg_obj = val.get("message", {})
                msg_text = msg_obj.get("text", "") if isinstance(msg_obj, dict) else ""
                
                print(f"DM (via changes) from {sender_id}: {msg_text}", flush=True)
                if sender_id:
                    clean_id = str(sender_id).strip("{}'\" ")
                    send_dm(clean_id, WELCOME_MESSAGE)
                continue

            # --- COMMENT HANDLER ---
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

