import os
import json
import requests
import urllib.parse

HISTORY_FILE = "post_history.json"
LINKEDIN_API = "https://api.linkedin.com/v2"

token = os.environ["LINKEDIN_ACCESS_TOKEN"]
headers = {
    "Authorization": f"Bearer {token}",
    "X-Restli-Protocol-Version": "2.0.0",
}

with open(HISTORY_FILE) as f:
    history = json.load(f)

post_ids = []
for day, posts in history.items():
    for p in posts:
        pid = p.get("post_id", "")
        if pid and pid != "unknown":
            post_ids.append(pid)

print(f"Found {len(post_ids)} posts to delete")
deleted, failed = 0, 0

for pid in post_ids:
    encoded = urllib.parse.quote(pid, safe="")
    try:
        r = requests.delete(f"{LINKEDIN_API}/ugcPosts/{encoded}", headers=headers, timeout=10)
        if r.status_code in (200, 204):
            print(f"Deleted: {pid}")
            deleted += 1
        else:
            print(f"Failed ({r.status_code}): {pid} - {r.text[:100]}")
            failed += 1
    except Exception as e:
        print(f"Error: {pid} - {e}")
        failed += 1

print(f"Done. Deleted: {deleted}, Failed: {failed}")
