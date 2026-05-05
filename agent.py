import os
import json
import random
import logging
import requests
from datetime import datetime, date, timedelta, timezone
from groq import Groq
from ddgs import DDGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HISTORY_FILE = "post_history.json"
LINKEDIN_API = "https://api.linkedin.com/v2"
UNSPLASH_API = "https://api.unsplash.com"
GITHUB_API = "https://api.github.com"

FALLBACK_TOPICS = [
    "Just deployed my first Python script to automate something and I can't believe it worked",
    "Trying to understand how APIs work — and honestly it's clicking now",
    "Learning Git properly for the first time — why didn't anyone tell me about rebasing earlier",
    "Built my first web scraper this week and the internet is wild",
    "Started learning about AI and machine learning — where do I even begin?",
    "Finally understood recursion after three days of banging my head",
    "My first open source contribution got merged and I'm low-key freaking out",
    "Why everyone keeps saying 'read the docs' — they're actually useful",
    "Debugging for 4 hours only to find a missing comma — classic beginner moment",
    "Just learned what an API is and now I see them everywhere",
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


TRENDING_QUERY_POOLS = {
    "tech": [
        "AI tools students learning 2025",
        "Python beginner projects trending 2025",
        "GitHub trending repositories this week",
        "free coding bootcamp resources 2025",
        "tech layoffs hiring junior developers 2025",
        "open source projects for beginners 2025",
    ],
    "general": [
        "trending news today 2025",
        "what is everyone talking about today",
        "viral story internet this week",
        "biggest news story today",
        "trending topic social media today",
    ],
    "career": [
        "entry level tech jobs 2025",
        "fresher developer salary trends 2025",
        "remote work opportunities students 2025",
        "LinkedIn tips for new graduates 2025",
        "how to get first tech job 2025",
    ],
    "learning": [
        "best free programming courses 2025",
        "learn to code trends beginners",
        "self taught developer success stories 2025",
        "AI helping students learn coding 2025",
    ],
}


def fetch_trending_news():
    # Pick 1 query from each category to keep posts varied across topics
    selected_queries = [
        random.choice(pool) for pool in TRENDING_QUERY_POOLS.values()
    ]
    random.shuffle(selected_queries)

    snippets = []
    try:
        with DDGS() as ddgs:
            for q in selected_queries[:3]:
                for r in ddgs.text(q, max_results=2):
                    title = r.get("title", "")
                    body = r.get("body", "")[:120]
                    if title:
                        snippets.append(f"{title}: {body}")
        logger.info("DuckDuckGo: %d snippets found", len(snippets))
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
    return snippets[:8]


def generate_post_content(commits, news_snippets):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    commit_text = "\n".join(f"- {c}" for c in commits) if commits else "No recent GitHub activity."
    if news_snippets:
        news_text = "\n".join(f"- {s}" for s in news_snippets)
    else:
        sample = random.sample(FALLBACK_TOPICS, min(3, len(FALLBACK_TOPICS)))
        news_text = "\n".join(f"- {t}" for t in sample)

    needs_image_val = "true" if random.random() < 0.5 else "false"

    prompt = f"""You are a fresh graduate and early-career developer who just started learning programming and tech.
You are enthusiastic, curious, and still figuring things out — not an expert.
Write ONE LinkedIn post for today based on the context below.

My recent GitHub commits (last 24h):
{commit_text}

What's trending today (tech, career, general news, learning):
{news_text}

Writing rules:
- 150 to 300 words total
- Sound like a genuine fresher — excited, honest, sometimes confused but pushing through
- Pick the MOST interesting or relatable topic from the trending context above — it does NOT have to be a tech topic
- You can write about career anxiety, job market, a viral story that connects to your learning journey, general life as a student/fresher, or any trending topic you find interesting
- Vary the opening: a relatable struggle, a small win, a "wait this clicked" moment, a reaction to something trending, or a genuine question
- Share one honest lesson, take, or reaction — make it personal and real
- End with a question asking for advice, opinions, or how others dealt with the same thing
- Maximum 3 relevant hashtags at the very end, nothing more
- Do NOT use phrases like "In today's world", "It goes without saying", or anything that sounds senior/expert
- Do NOT claim years of experience or frame yourself as an authority
- needs_image must be exactly {needs_image_val}

Return ONLY valid JSON with no markdown fences:
{{"text": "full post text here", "needs_image": {needs_image_val}, "image_query": "1-2 word search term if needs_image is true else null"}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    logger.info("Groq: post generated, needs_image=%s", result.get("needs_image"))
    return result


def fetch_unsplash_image(query):
    try:
        resp = requests.get(
            f"{UNSPLASH_API}/search/photos",
            params={"query": query, "per_page": 10, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            logger.warning("Unsplash: no results for query '%s'", query)
            return None
        img_url = random.choice(results)["urls"]["regular"]
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
