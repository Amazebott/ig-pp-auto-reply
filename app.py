import os, json, requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

# ALL messages are variables now - you can change them in Render > Edit anytime
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hey! Thanks for DMing 💛")
COMMENT_MESSAGE = os.getenv("COMMENT_MESSAGE", "Thanks so much! 💛")
COMMENT_DM_PROMPT = os.getenv("COMMENT_DM_PROMPT", "Just sent you the link in DMs! 💛")
LINK_DM_TEMPLATE = os.getenv("LINK_DM_TEMPLATE", "Here you go! {LINK}")

POST_LINKS = json.loads(os.getenv("POST_LINKS_JSON", '{"default": "https://your-link.com"}'))

def send_dm(recipient_id, text):
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}})

def reply_to_comment(comment_id, text):
    url = f"https://graph.facebook.com/v20.0/{comment_id}/replies?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"message": text})

@app.route('/posts')
def list_posts():
    url = f"https://graph.facebook.com/v20.0/me/media?fields=id,caption,permalink&access_token={PAGE_ACCESS_TOKEN}"
    return requests.get(url).json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") in ["comments", "feed"]:
                val = change.get("value", {})
                media_id = str(val.get("media_id") or val.get("post_id") or "")
                comment_text = val.get("text", "").lower()
                comment_id = val.get("comment_id") or val.get("id")
                from_id = val.get("from", {}).get("id")

                if "link" in comment_text and comment_id:
                    link_to_send = POST_LINKS.get(media_id) or POST_LINKS.get("default")
                    # Uses your Render variable for public reply
                    reply_to_comment(comment_id, COMMENT_DM_PROMPT)
                    # Uses your Render variable for DM - replaces {LINK}
                    if from_id:
                        send_dm(from_id, LINK_DM_TEMPLATE.replace("{LINK}", link_to_send))
                elif comment_id and val.get("verb") == "add":
                    # Uses your Render variable for normal thanks
                    reply_to_comment(comment_id, COMMENT_MESSAGE)
    return "OK", 200

# ... keep your verify route and home route

# keep your verify, send_dm, reply_to_comment as before
