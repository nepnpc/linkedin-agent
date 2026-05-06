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
    "n8n vs Zapier — n8n wins when you need self-hosted + complex branching logic",
    "LangGraph state persistence changes everything for long-running agents",
    "MCP servers are the cleanest way to expose local tools to LLMs right now",
    "Most automation failures are JSON parsing errors, not logic errors. Validate at the boundary.",
    "Webhook-first design saves hours of polling headaches",
    "Vector stores don't replace SQL — they complement it for unstructured data retrieval",
    "Groq inference speed makes real-time agent loops actually viable in production",
    "90% of 'AI agent' projects are just prompt chaining with if/else dressed up",
    "Rate limiting is the first thing that breaks your automation at scale. Build for it early.",
    "Structured output from LLMs is still unreliable enough that retry + schema validation is not optional",
    "Self-hosting Ollama for dev and swapping to a hosted model for prod is underrated",
    "n8n's HTTP node pagination support saves a lot of custom loop code",
    "Pydantic + instructor library is the cleanest combo for reliable LLM JSON output",
    "GitHub Actions is a perfectly fine automation scheduler for most use cases. You don't need Airflow.",
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
    "ai_agents": [
        "LangGraph agent orchestration patterns 2026",
        "n8n automation new features release 2026",
        "MCP server Claude tools integration 2026",
        "AI agent frameworks comparison LangChain CrewAI AutoGen",
        "OpenAI Assistants API vs custom agent architecture",
        "multi-agent workflow production deployment 2026",
    ],
    "tools": [
        "n8n vs Make vs Zapier automation comparison 2026",
        "self hosted AI automation tools open source",
        "Python automation engineering best practices 2026",
        "vector database production comparison pinecone weaviate",
        "local LLM Ollama automation workflow engineers",
        "Pydantic instructor structured output LLM 2026",
    ],
    "engineering": [
        "webhook integration reliability patterns engineers",
        "LLM JSON structured output reliability production",
        "prompt engineering production system tips 2026",
        "RAG retrieval pipeline optimization techniques",
        "AI automation testing strategies engineers",
        "rate limiting API automation scale patterns",
    ],
    "industry": [
        "AI automation engineer job market 2026",
        "enterprise AI agent adoption trends engineers",
        "no-code vs custom code automation debate developers",
        "AI replacing automation workflow jobs reality 2026",
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

    prompt = f"""You are a mid-level AI automation engineer. You build agents, n8n workflows, LangChain/LangGraph pipelines, and Python automations professionally.

Write ONE LinkedIn post. Target audience: mid-level AI/automation engineers who want signal, not noise.

My recent GitHub commits (last 24h):
{commit_text}

Trending context (AI tools, automation, engineering):
{news_text}

Rules:
- 80 to 200 words
- Pick the most useful or interesting insight from the context above — prefer something specific and practical
- Write like a practitioner sharing a real observation — direct, no corporate speak, no fluff
- VARY the format (pick randomly each time):
  * Plain fact/observation: "n8n's HTTP node now handles pagination natively. Saves a lot of custom loop code."
  * Short tip: "If your LLM agent keeps failing JSON parsing, wrap the output call in a retry loop with schema validation."
  * Comparison or hot take: "LangGraph vs CrewAI — LangGraph wins for anything stateful. CrewAI is better for quick demos."
  * Lesson from a build: what broke, one line on why, one line on the fix
- Do NOT open with: "I think", "In my experience", "As an engineer", "Excited to share"
- Do NOT use: "In today's world", "It goes without saying", "leverage", "dive deep", "game-changer", "unlock"
- No rhetorical opener questions
- No storytelling arc — get to the point immediately
- Ending: a direct peer question OR nothing at all — a plain statement ending is fine
- Hashtags: 0 to 2 only. Zero is fine. Only add if genuinely relevant.
- needs_image must be exactly {needs_image_val}
- For image_query: give a SPECIFIC visual that looks professional and eye-catching — like "glowing neural network nodes dark background", "terminal green code dark screen", "robot arm circuit board close up", "automation flowchart glowing nodes" — NOT generic like "technology" or "computer"

Return ONLY valid JSON, no markdown fences:
{{"text": "post text", "needs_image": {needs_image_val}, "image_query": "specific visual query or null"}}"""

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
        results.sort(key=lambda x: x.get("likes", 0), reverse=True)
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
