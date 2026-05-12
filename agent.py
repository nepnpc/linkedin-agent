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
    "Half of automation engineering is error handling, not automation logic. The edges are the whole job.",
    "The engineers good at AI automation know how to debug systems they didn't build, not just which models exist.",
    "Everyone builds AI copilots for internal tools. Most get abandoned in 6 months because nobody defined 'helpful' before building.",
    "LLM output validation with Pydantic + instructor gives typed objects back instead of dicts — same result, less boilerplate.",
    "Vendor APIs silently changing response schemas has broken more pipelines than any logic bug.",
    "Conditional edges in LangGraph without a proper end condition will loop forever. Found out the hard way.",
    "MCP is just REST but the server decides what tools to expose. Cleaner than hacking tool definitions into every prompt.",
    "n8n sub-workflows for isolated retries — the main retry node resets the whole branch, not just the failed node.",
    "The difference between a demo agent and a prod agent is entirely in how it handles failures.",
    "Most 'agentic AI' in production: one LLM call, some if/else, maybe a loop. Works fine. Stop calling it architecture.",
]


POST_ARCHETYPES = [
    {
        "name": "raw_observation",
        "instruction": (
            "Write 1-2 tight paragraphs. No lists. No headers. A direct observation from actual work. "
            "Read like something typed on a phone while waiting for a build. Casual but specific."
        ),
        "example": (
            "Spent three hours debugging a LangGraph agent that kept looping. "
            "Issue wasn't the logic — I forgot to add an end condition to the conditional edge. "
            "One line. Three hours. That's agents in 2026."
        ),
    },
    {
        "name": "hot_take",
        "instruction": (
            "Lead with the controversial or counterintuitive claim. Back it up in 2-3 sentences. "
            "No hedging. Own the opinion. Don't soften it."
        ),
        "example": (
            "Most 'AI agents' in production are just LLM calls with if/else wrapped around them. "
            "That's not a diss — it works. "
            "But stop calling it an agent architecture when it's a decision tree with a language model in one branch."
        ),
    },
    {
        "name": "quick_lesson",
        "instruction": (
            "Something specific you learned or discovered. Not a generic tip — "
            "a concrete detail: a specific error, a named tool, a version, a number. Under 100 words."
        ),
        "example": (
            "n8n's retry-on-fail node resets the entire branch, not just the failed node. "
            "Found this when a webhook listener kept re-firing on every retry. "
            "Use a sub-workflow if you need isolated retries."
        ),
    },
    {
        "name": "before_after",
        "instruction": (
            "What you used to do vs what you do now, or what broke vs how you fixed it. "
            "Two short paragraphs or one paragraph with a clear pivot. No bullet lists."
        ),
        "example": (
            "Used to validate LLM JSON output with try/except around json.loads. "
            "Now I use Pydantic with instructor and let it retry automatically. "
            "Same result, less boilerplate, and I get typed objects back instead of dicts."
        ),
    },
    {
        "name": "comparison",
        "instruction": (
            "Compare two tools, approaches, or concepts. Be specific about when each wins. "
            "No 'it depends' cop-out — give an actual recommendation for actual scenarios."
        ),
        "example": (
            "LangGraph vs CrewAI: LangGraph when you need fine control over state and conditional routing. "
            "CrewAI when you want agents that feel like teammates and you're okay with less visibility. "
            "For anything going to prod, LangGraph."
        ),
    },
    {
        "name": "industry_take",
        "instruction": (
            "Observation about where the industry is heading, what's overhyped, what's underrated. "
            "Can be a bit ranty. Sounds like talking to a peer at a conference, not a blog post."
        ),
        "example": (
            "Everyone's building AI copilots for their internal tools right now. "
            "Most will get abandoned in 6 months. "
            "Not because the tech is bad — because nobody defined what 'helpful' actually means for their workflow before building."
        ),
    },
    {
        "name": "unglamorous_reality",
        "instruction": (
            "The boring, frustrating, or invisible part of this work. "
            "The thing that doesn't show up in tutorials or success posts. Raw and specific. "
            "No inspirational spin."
        ),
        "example": (
            "Half my automation engineering time is error handling and logging, not the automation logic. "
            "Rate limits, API timeouts, malformed webhooks, schema changes nobody documented. "
            "The pipelines are easy. The edges are the whole job."
        ),
    },
    {
        "name": "numbered_list",
        "instruction": (
            "3 to 5 numbered points. Each point is ONE concrete sentence — no sub-explanations. "
            "No intro sentence. No CTA at the end. Full post reads in under 20 seconds."
        ),
        "example": (
            "Things that silently break automation pipelines:\n"
            "1. Vendor API changes response schema without versioning\n"
            "2. Webhook payload arrives faster than the handler processes\n"
            "3. LLM returns valid JSON but wrong field names\n"
            "4. Token expires mid-run with no refresh logic\n"
            "5. Someone edits the workflow while it's running"
        ),
    },
    {
        "name": "career_observation",
        "instruction": (
            "Something noticed about being an AI/automation engineer — the work, the career, "
            "what people get wrong about the job. Personal but not navel-gazing. No life lessons."
        ),
        "example": (
            "The engineers actually good at AI automation aren't the ones who know the most models. "
            "They're the ones who can debug systems they didn't build "
            "and read an API error and know exactly where to look."
        ),
    },
    {
        "name": "single_insight",
        "instruction": (
            "One paragraph, one idea, fully explained. No preamble, no conclusion, no CTA. "
            "Dense with specific detail. If it could be a tweet, make it longer and more useful."
        ),
        "example": (
            "Structured output from LLMs breaks in production not because the model is bad "
            "but because response_format enforcement varies by model and provider. "
            "Groq + llama-3.3 is strict. GPT-4o occasionally drifts on nested schemas. "
            "Build your retry + validation layer against the strictest behavior you expect, "
            "not the average."
        ),
    },
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
        sample = random.sample(FALLBACK_TOPICS, min(4, len(FALLBACK_TOPICS)))
        news_text = "\n".join(f"- {t}" for t in sample)

    needs_image_val = "true" if random.random() < 0.5 else "false"

    archetype = random.choice(POST_ARCHETYPES)

    prompt = f"""You are a working AI automation engineer. You build agents, n8n workflows, LangGraph pipelines, and Python automations. You have real opinions. You've been burned by bad abstractions and stupid bugs. You share what you actually know, not what sounds impressive.

Write ONE LinkedIn post for other engineers. Signal only — no noise, no inspiration porn.

## Your raw material (use ONE angle from this, not all of it):

Recent GitHub commits:
{commit_text}

What's happening in the space:
{news_text}

## Format for this post: {archetype["name"]}

Instructions: {archetype["instruction"]}

Example of this format (DO NOT copy — use as structural reference only):
"{archetype["example"]}"

## Hard rules — violation = failure:

FORBIDDEN OPENERS (never start with these or any variation):
- "I've been", "I just", "I recently", "As I", "In my experience", "I think"
- "What if", "Have you ever", "Did you know", "Imagine if"
- "I stumbled upon", "I came across", "I've been scrolling"
- "In today's world", "In the age of", "As we move toward"
- "Excited to share", "Thrilled to announce", "Happy to share"
- Any question as the opening line

FORBIDDEN PHRASES (anywhere in post):
- "game-changer", "game changer", "unlock", "leverage", "dive deep", "deep dive"
- "it goes without saying", "needless to say", "at the end of the day"
- "rapidly evolving", "ever-evolving", "fast-paced", "revolutionary"
- "paradigm shift", "move the needle", "touch base", "circle back"
- "as an AI language model", "as a practitioner", "as an engineer"
- "the future of", "the power of", "the importance of"

STRUCTURE RULES:
- No motivational or inspirational framing whatsoever
- No "Here's what I learned:" or "Key takeaway:" or "TLDR:" headers
- No ending with "What do you think?" or "Drop a comment below" or "Would love to hear your thoughts"
- No emojis used as bullet points
- Ending: plain statement, peer question on the specific topic, or nothing — all fine
- Hashtags: 0 to 2 max. Zero is preferred. Only if genuinely useful for discovery.

LENGTH: 60–180 words. Shorter is fine if the idea is complete.

IMAGE:
- needs_image must be exactly {needs_image_val}
- image_query: specific professional visual — e.g. "glowing neural network nodes dark background", "terminal green code dark screen", "circuit board macro close up", "server rack data center blue light" — NOT "technology" or "AI" or "computer"

Return ONLY valid JSON, no markdown fences:
{{"text": "post text here", "needs_image": {needs_image_val}, "image_query": "specific query or null"}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    logger.info("Groq: post generated, archetype=%s needs_image=%s", archetype["name"], result.get("needs_image"))
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
