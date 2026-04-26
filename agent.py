import os
import json
import random
import logging
import requests
from datetime import datetime, date, timedelta, timezone
from google import genai
from google.genai import types
from ddgs import DDGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HISTORY_FILE = "post_history.json"
LINKEDIN_API = "https://api.linkedin.com/v2"
UNSPLASH_API = "https://api.unsplash.com"
GITHUB_API = "https://api.github.com"

FALLBACK_TOPICS = [
    "The future of AI agents in enterprise software development",
    "Why agentic workflows are reshaping automation in 2025",
    "Python's dominance in the AI/ML engineering stack",
    "Zero-trust security in a world of AI-generated code",
    "The hidden complexity behind simple-looking LLM prompts",
    "How GitHub Copilot changed how I think about code review",
    "Lessons from building my first fully autonomous AI pipeline",
]


def load_post_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_post_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def should_post(history):
    today = date.today().isoformat()
    posts_today = history.get(today, [])
    count = len(posts_today)

    if count >= 5:
        logger.info("Daily cap (5 posts) reached. Exiting.")
        return False

    # 20:00 UTC = last scheduled run of the day
    is_last_run = datetime.now(timezone.utc).hour >= 20
    if is_last_run and count == 0:
        logger.info("Last run of day with 0 posts — forcing post.")
        return True

    decision = random.random() > 0.5
    logger.info("Random decision: %s (posts today: %d)", "POST" if decision else "SKIP", count)
    return decision


def fetch_github_events(username):
    try:
        gh_token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github+json"}
        if gh_token:
            headers["Authorization"] = f"Bearer {gh_token}"
        resp = requests.get(
            f"{GITHUB_API}/users/{username}/events",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        commits = []
        for event in resp.json():
            if event.get("type") != "PushEvent":
                continue
            created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                continue
            for commit in event.get("payload", {}).get("commits", []):
                msg = commit.get("message", "").strip().split("\n")[0]
                if msg and len(msg) > 10:
                    commits.append(msg)
        logger.info("GitHub: %d commits found in last 24h", len(commits))
        return commits[:10]
    except Exception as e:
        logger.warning("GitHub API failed: %s", e)
        return []


def fetch_trending_news():
    queries = [
        "AI agents autonomous 2025",
        "agentic workflow automation trends",
        "cybersecurity Python engineering 2025",
    ]
    snippets = []
    try:
        with DDGS() as ddgs:
            for q in queries[:2]:
                for r in ddgs.text(q, max_results=3):
                    title = r.get("title", "")
                    body = r.get("body", "")[:120]
                    if title:
                        snippets.append(f"{title}: {body}")
        logger.info("DuckDuckGo: %d snippets found", len(snippets))
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
    return snippets[:6]


def generate_post_content(commits, news_snippets):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    commit_text = "\n".join(f"- {c}" for c in commits) if commits else "No recent GitHub activity."
    if news_snippets:
        news_text = "\n".join(f"- {s}" for s in news_snippets)
    else:
        sample = random.sample(FALLBACK_TOPICS, min(3, len(FALLBACK_TOPICS)))
        news_text = "\n".join(f"- {t}" for t in sample)

    needs_image_val = "true" if random.random() < 0.3 else "false"

    prompt = f"""You are a Senior AI Automation Engineer with 8 years of experience.
You build agentic systems, Python automation pipelines, and AI-powered workflows.
Write ONE LinkedIn post for today based on the context below.

My recent GitHub commits (last 24h):
{commit_text}

Trending topics in AI / Cybersecurity / Python:
{news_text}

Writing rules:
- 150 to 300 words total
- Conversational yet insightful — like a smart colleague sharing a real lesson
- Vary the opening: bold statement, personal story, surprising stat, or rhetorical question
- Share one concrete insight, lesson, or prediction
- End with a single thought-provoking question to drive comments
- Maximum 3 relevant hashtags at the very end, nothing more
- Do NOT use generic phrases like "In today's world" or "It goes without saying"
- needs_image must be exactly {needs_image_val}

Return ONLY valid JSON with no markdown fences:
{{"text": "full post text here", "needs_image": {needs_image_val}, "image_query": "1-2 word search term if needs_image is true else null"}}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    result = json.loads(response.text)
    logger.info("Gemini: post generated, needs_image=%s", result.get("needs_image"))
    return result


def fetch_unsplash_image(query):
    try:
        resp = requests.get(
            f"{UNSPLASH_API}/search/photos",
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            logger.warning("Unsplash: no results for query '%s'", query)
            return None
        img_url = results[0]["urls"]["regular"]
        img_resp = requests.get(img_url, timeout=20)
        img_resp.raise_for_status()
        logger.info("Unsplash: downloaded %d bytes for '%s'", len(img_resp.content), query)
        return img_resp.content
    except Exception as e:
        logger.warning("Unsplash fetch failed: %s", e)
        return None


def upload_image_to_linkedin(image_bytes):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    urn = os.environ["LINKEDIN_URN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Step 1: Register upload slot
    register_body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    reg_resp = requests.post(
        f"{LINKEDIN_API}/assets?action=registerUpload",
        headers=headers,
        json=register_body,
        timeout=15,
    )
    reg_resp.raise_for_status()
    value = reg_resp.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = value["asset"]

    # Step 2: Upload binary to the pre-signed URL
    put_resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=image_bytes,
        timeout=30,
    )
    put_resp.raise_for_status()
    logger.info("LinkedIn: image uploaded, asset=%s", asset_urn)
    return asset_urn


def publish_to_linkedin(text, asset_urn=None):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    urn = os.environ["LINKEDIN_URN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    if asset_urn:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {"text": text[:100]},
                    "media": asset_urn,
                }
            ],
        }
    else:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }

    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(f"{LINKEDIN_API}/ugcPosts", headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id", "unknown")
    logger.info("LinkedIn: post published id=%s", post_id)
    return post_id


def main():
    history = load_post_history()

    if not should_post(history):
        logger.info("Skipping this run. No post made.")
        return

    github_username = os.environ.get("GITHUB_USERNAME", "")
    commits = fetch_github_events(github_username) if github_username else []
    news = fetch_trending_news()

    post_data = generate_post_content(commits, news)
    text = post_data["text"]
    needs_image = post_data.get("needs_image", False)
    image_query = post_data.get("image_query")

    asset_urn = None
    if needs_image and image_query:
        image_bytes = fetch_unsplash_image(image_query)
        if image_bytes:
            try:
                asset_urn = upload_image_to_linkedin(image_bytes)
            except Exception as e:
                logger.warning("Image upload failed, downgrading to text-only: %s", e)

    post_id = publish_to_linkedin(text, asset_urn)

    today = date.today().isoformat()
    history.setdefault(today, []).append({
        "time": datetime.utcnow().strftime("%H:%M:%S"),
        "type": "image" if asset_urn else "text",
        "post_id": post_id,
        "snippet": text[:50],
    })
    save_post_history(history)
    logger.info("Done. Posts today: %d", len(history[today]))


if __name__ == "__main__":
    main()
