import os, json, requests, time, threading
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- ENV VARS ---
def clean_token(t):
    if not t: return ""
    return t.strip().strip('"').strip("'").strip()

# --- ENV VARS ---
FOLLOW_MESSAGE = os.getenv("FOLLOW_MESSAGE", "Welcome! 🎙 Enjoy our podcast on 【entity-Apple¦canonical_name=Apple】, 【entity-Spotify¦canonical_name=Spotify】, and 【entity-YouTube Music¦canonical_name=YouTube Music】! 🎧😊 Happy Listening!")
DM_MESSAGE = os.getenv("DM_MESSAGE", "Thanks for reaching out! 💛")
APPLE_URL = os.getenv("APPLE_URL", "https://podcasts.apple.com/")
SPOTIFY_URL = os.getenv("SPOTIFY_URL", "https://open.spotify.com/")
YOUTUBE_MUSIC_URL = os.getenv("YOUTUBE_MUSIC_URL", "https://music.youtube.com/")

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hey! Thanks for DMing 💛")
COMMENT_MESSAGE = os.getenv("COMMENT_MESSAGE", "Thanks so much! 💛")
COMMENT_DM_PROMPT = os.getenv("COMMENT_DM_PROMPT", "Just sent you the link in DMs! 💛")
LINK_DM_TEMPLATE = os.getenv("LINK_DM_TEMPLATE", "Here you go! {LINK}")
POST_LINKS = json.loads(os.getenv("POST_LINKS_JSON", '{"default": "https://your-link.com"}'))

VERIFY_TOKEN = clean_token(os.getenv("VERIFY_TOKEN", ""))
IG_TOKEN = clean_token(os.getenv("IG_ACCESS_TOKEN",""))
PAGE_ACCESS_TOKEN = clean_token(os.getenv("PAGE_ACCESS_TOKEN", ""))
IG_USER_ID = clean_token(os.getenv("IG_USER_ID", "17841405822304914"))
FOLLOWERS_FILE = "/tmp/followers.json"

# --- HELPERS ---
def load_followers():
    try:
        if os.path.exists(FOLLOWERS_FILE):
            with open(FOLLOWERS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"followers": [], "unfollowers": [], "last_check": None}

def save_followers(data):
    try:
        with open(FOLLOWERS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Save error: {e}", flush=True)

def send_dm(recipient_id, text):
    if not recipient_id:
        return None
    rid = str(recipient_id).strip("{}'\" ")
    if rid in ["0", "23245", "12334"]:
        return None
    url = f"https://graph.instagram.com/v25.0/me/messages"
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"recipient": {"id": rid}, "message": {"text": text}}, timeout=10)
    print(f"Send DM to {rid}: {r.status_code} {r.text}", flush=True)
    return r

def send_podcast_menu(recipient_id):
    if not recipient_id:
        return None
    rid = str(recipient_id).strip("{}'\" ")
    if rid in ["0", "23245", "12334"]:
        return None
    url = f"https://graph.instagram.com/v25.0/me/messages"
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    r1 = requests.post(url, headers=headers, json={"recipient": {"id": rid}, "message": {"text": FOLLOW_MESSAGE}}, timeout=15)
    print(f"Follow msg to {rid}: {r1.status_code} {r1.text}", flush=True)
    carousel = {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {"title": " 【entity-Apple¦canonical_name=Apple】 Podcasts", "subtitle": "Listen on 【entity-Apple¦canonical_name=Apple】", "image_url": "https://cdn-icons-png.flaticon.com/512/831/831276.png", "default_action": {"type": "web_url", "url": APPLE_URL}, "buttons": [{"type": "web_url", "url": APPLE_URL, "title": " 【entity-Apple¦canonical_name=Apple】 Podcasts"}]},
                    {"title": " 【entity-Spotify¦canonical_name=Spotify】", "subtitle": "Listen on 【entity-Spotify¦canonical_name=Spotify】", "image_url": "https://cdn-icons-png.flaticon.com/512/2111/2111624.png", "default_action": {"type": "web_url", "url": SPOTIFY_URL}, "buttons": [{"type": "web_url", "url": SPOTIFY_URL, "title": "Open 【entity-Spotify¦canonical_name=Spotify】"}]},
                    {"title": " 【entity-YouTube Music¦canonical_name=YouTube Music】", "subtitle": "Listen on 【entity-YouTube Music¦canonical_name=YouTube Music】", "image_url": "https://cdn-icons-png.flaticon.com/512/1384/1384060.png", "default_action": {"type": "web_url", "url": YOUTUBE_MUSIC_URL}, "buttons": [{"type": "web_url", "url": YOUTUBE_MUSIC_URL, "title": " 【entity-YouTube Music¦canonical_name=YouTube Music】"}]}
                ]
            }
        }
    }
    r2 = requests.post(url, headers=headers, json={"recipient": {"id": rid}, "message": carousel}, timeout=15)
    print(f"Carousel to {rid}: {r2.status_code} {r2.text}", flush=True)
    return r2

def reply_to_comment(comment_id, text):
    url = f"https://graph.instagram.com/v25.0/{comment_id}/replies"
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"message": text}, timeout=10)
    print(f"Reply {comment_id}: {r.status_code} {r.text}", flush=True)
    return r

# --- FOLLOWER POLLING LIKE MANYCHAT ---
def fetch_current_followers():
    try:
        url = f"https://graph.instagram.com/v25.0/{IG_USER_ID}"
        params = {"fields": "followers_count", "access_token": IG_TOKEN}
        r = requests.get(url, params=params, timeout=10)
        print(f"Followers count check: {r.text[:500]}", flush=True)
    except Exception as e:
        print(f"Count error: {e}", flush=True)

    token_for_followers = PAGE_ACCESS_TOKEN or IG_TOKEN
    print(f"Using token for followers edge: PAGE_TOKEN length {len(PAGE_ACCESS_TOKEN)} / IG_TOKEN length {len(IG_TOKEN)} -> using len {len(token_for_followers)}", flush=True)
    
    try:
        url = f"https://graph.facebook.com/v25.0/{IG_USER_ID}/followers"
        params = {"access_token": token_for_followers, "limit": 50}
        r = requests.get(url, params=params, timeout=15)
        print(f"Followers edge: {r.status_code} {r.text[:1500]}", flush=True)
        if r.status_code == 200:
            data = r.json()
            return [str(f.get("id")) for f in data.get("data", [])]
        return None
    except Exception as e:
        print(f"Followers edge error: {e}", flush=True)
        return None


def check_followers_loop():
    print("Follower checker started (every 120s)", flush=True)
    while True:
        try:
            stored = load_followers()
            old_followers = set(stored.get("followers", []))
            current = fetch_current_followers()
            if current is None:
                print("Followers edge not available - using DM history proxy", flush=True)
                time.sleep(120)
                continue
            new_followers = set(current) - old_followers
            unfollowed = old_followers - set(current)
            if new_followers:
                print(f"NEW FOLLOWERS: {new_followers}", flush=True)
                for fid in new_followers:
                    send_podcast_menu(fid)
            if unfollowed:
                print(f"UNFOLLOWED: {unfollowed}", flush=True)
                stored["unfollowers"] = list(set(stored.get("unfollowers", [])) | unfollowed)
            stored["followers"] = current
            stored["last_check"] = datetime.now().isoformat()
            save_followers(stored)
        except Exception as e:
            print(f"Follower loop error: {e}", flush=True)
        time.sleep(120)

threading.Thread(target=check_followers_loop, daemon=True).start()

@app.route("/privacy")
def privacy():
    return """
    <html><head><title>Privacy Policy</title></head><body>
    <h1>Privacy Policy - Parenting Pulse</h1>
    <p>Effective Date: 2026</p>
    <p>We use Instagram permissions instagram_manage_comments and instagram_business_manage_messages solely to auto-reply to comments containing the keyword 'link' and send the requested link via DM.</p>
    <p>We do not store, share, or sell personal data. Data is processed transiently to fulfill the DM request.</p>
    <p>To request deletion: email amazebot@outlook.com and we will delete any stored comment IDs within 48 hours.</p>
    <p>Contact: amazebot@outlook.com</p>
    </body></html>
    """, 200, {'Content-Type': 'text/html'}

@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route('/')
def home():
    return "Bot is running - webhook ready - follower checker active"

@app.route('/followers')
def list_followers_route():
    data = load_followers()
    return jsonify(data)

@app.route('/unfollowers')
def list_unfollowers_route():
    data = load_followers()
    return jsonify({"unfollowers": data.get("unfollowers", []), "count": len(data.get("unfollowers", [])), "last_check": data.get("last_check")})

@app.route('/followers/reset')
def reset_followers():
    save_followers({"followers": [], "unfollowers": [], "last_check": None})
    return "Followers list reset - will rebuild on next check"

# --- DEBUG CODE KEPT BUT COMMENTED OUT ---
# @app.route('/debug-subscription')
# def debug_sub():
#     TOKEN = os.environ.get('IG_ACCESS_TOKEN')
#     headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
#     payload = {"subscribed_fields": "messages,messaging_seen,messaging_postbacks,messaging_referral"}
#     r = requests.post(f"https://graph.instagram.com/v25.0/me/subscribed_apps", headers=headers, json=payload)
#     return r.text
#
# @app.route('/debug-status')
# def debug_status():
#     TOKEN = os.environ.get('IG_ACCESS_TOKEN')
#     headers = {"Authorization": f"Bearer {TOKEN}"}
#     r = requests.get(f"https://graph.instagram.com/v25.0/me/subscribed_apps", headers=headers)
#     r2 = requests.get(f"https://graph.instagram.com/v25.0/me?fields=id,username", headers=headers)
#     return f"SUBSCRIBED: {r.text}<br><br>ME IS: {r2.text}"
#
# # --- ADDITIONAL DEBUG HELPERS (kept commented) ---
# @app.route('/debug-token')
# def debug_token():
#     TOKEN = os.environ.get('IG_ACCESS_TOKEN')
#     r = requests.get(f"https://graph.instagram.com/v25.0/me?fields=id,username", headers={"Authorization": f"Bearer {TOKEN}"})
#     return f"Token check: {r.status_code} {r.text}"
#
# @app.route('/debug-send-test')
# def debug_send_test():
#     to = request.args.get("to")
#     TOKEN = os.environ.get('IG_ACCESS_TOKEN')
#     url = f"https://graph.instagram.com/v25.0/me/messages"
#     headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
#     payload = {"recipient": {"id": to}, "message": {"text": "Test from debug-send-test 💛"}}
#     r = requests.post(url, headers=headers, json=payload)
#     return f"{r.status_code} {r.text}"
# --- END DEBUG CODE ---

@app.route('/debug-fix-sub-live')
def debug_fix_sub_live():
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    results = ""
    payload_ig = {"subscribed_fields": "messages,messaging_seen,messaging_postbacks,comments"}
    r1 = requests.post(f"https://graph.instagram.com/v25.0/29124672473803420/subscribed_apps", headers=headers, json=payload_ig, timeout=10)
    results += f"IG sub 29124...: {r1.status_code} {r1.text}<br><br>"
    r2 = requests.post(f"https://graph.instagram.com/v25.0/17907894192554821/subscribed_apps", headers=headers, json=payload_ig, timeout=10)
    results += f"Page sub 17907...: {r2.status_code} {r2.text}<br><br>"
    r3 = requests.get(f"https://graph.instagram.com/v25.0/me/subscribed_apps", headers={"Authorization": f"Bearer {IG_TOKEN}"}, timeout=10)
    results += f"CURRENT STATUS: {r3.text}"
    return results, 200, {'Content-Type': 'text/html'}
    
@app.route('/debug-status-live')
def debug_status_live():
    headers = {"Authorization": f"Bearer {IG_TOKEN}"}
    r = requests.get(f"https://graph.instagram.com/v25.0/me/subscribed_apps", headers=headers, timeout=10)
    r2 = requests.get(f"https://graph.instagram.com/v25.0/me?fields=id,username", headers=headers, timeout=10)
    return f"SUBSCRIBED: {r.text}<br><br>ME IS: {r2.text}", 200, {'Content-Type': 'text/html'}

@app.route('/debug-subscription-live')
def debug_sub_live():
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    payload = {"subscribed_fields": "messages,messaging_seen,messaging_postbacks,messaging_referral"}
    r = requests.post(f"https://graph.instagram.com/v25.0/me/subscribed_apps", headers=headers, json=payload, timeout=10)
    return r.text, 200, {'Content-Type': 'text/html'}

@app.route('/debug-send-test-live')
def debug_send_test_live():
    to = request.args.get("to")
    if not to:
        return "Add ?to=IG_ID - like /debug-send-test-live?to=YOUR_ID"
    url = f"https://graph.instagram.com/v25.0/me/messages"
    headers = {"Authorization": f"Bearer {IG_TOKEN}", "Content-Type": "application/json"}
    payload = {"recipient": {"id": to}, "message": {"text": "Test DM from bot 💛 works!"}}
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    return f"{r.status_code} {r.text}"

@app.route('/debug-followers-live')
def debug_followers_live():
    current = fetch_current_followers()
    stored = load_followers()
    return jsonify({"current_api_result": current, "stored": stored})

@app.route('/posts')
def list_posts():
    url = f"https://graph.instagram.com/v25.0/me/media?fields=id,caption,permalink&access_token={IG_TOKEN}"
    return requests.get(url).json()

@app.route('/webhook', methods=['POST'])
def webhook():
    raw = request.get_data(as_text=True)
    print(f"RAW WEBHOOK HIT: {raw[:4000]}", flush=True)
    data = request.get_json(silent=True) or {}
    print(f"Received webhook: {json.dumps(data)[:3000]}", flush=True)
    if not data:
        return "OK", 200
    for entry in data.get("entry", []):
        entry_id = str(entry.get("id", ""))
        if entry_id == "0":
            print("✅ 【entity-Meta¦canonical_name=Meta】 dashboard TEST event (id=0) - returning 200 OK without sending", flush=True)
            continue
        for msg in entry.get("messaging", []):
            if msg.get("message", {}).get("is_echo"):
                continue
            sender_id = msg.get("sender", {}).get("id")
            text = msg.get("message", {}).get("text", "")
            print(f"DM from {sender_id}: {text}", flush=True)
            if sender_id and text:
                send_dm(sender_id, DM_MESSAGE)
        for change in entry.get("changes", []):
            field = change.get("field")
            if field not in ["comments", "feed", "messages"]:
                continue
            if field == "messages":
                val = change.get("value", {})
                sender_obj = val.get("sender", {})
                if isinstance(sender_obj, dict):
                    sender_id = sender_obj.get("id") or next(iter(sender_obj.keys()), None)
                else:
                    sender_id = sender_obj
                print(f"DM (via changes) from {sender_id} - treating as FOLLOW", flush=True)
                if sender_id:
                    clean_id = str(sender_id).strip("{}'\" ")
                    send_podcast_menu(clean_id)
                continue
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
