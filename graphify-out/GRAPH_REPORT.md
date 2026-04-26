# Graph Report - C:\Users\User\Documents\linkedin-agent  (2026-04-27)

## Corpus Check
- Corpus is ~926 words - fits in a single context window. You may not need a graph.

## Summary
- 15 nodes · 24 edges · 2 communities detected
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Agent Pipeline Functions|Agent Pipeline Functions]]
- [[_COMMUNITY_Python Dependencies|Python Dependencies]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 10 edges
2. `requests` - 3 edges
3. `LinkedIn Agent Project` - 3 edges
4. `load_post_history()` - 2 edges
5. `save_post_history()` - 2 edges
6. `should_post()` - 2 edges
7. `fetch_github_events()` - 2 edges
8. `fetch_trending_news()` - 2 edges
9. `generate_post_content()` - 2 edges
10. `fetch_unsplash_image()` - 2 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Hyperedges (group relationships)
- **LinkedIn Agent Python Dependencies** — requirements_linkedin_agent, requirements_google_generativeai, requirements_duckduckgo_search, requirements_requests [EXTRACTED 1.00]

## Communities

### Community 0 - "Agent Pipeline Functions"
Cohesion: 0.35
Nodes (10): fetch_github_events(), fetch_trending_news(), fetch_unsplash_image(), generate_post_content(), load_post_history(), main(), publish_to_linkedin(), save_post_history() (+2 more)

### Community 1 - "Python Dependencies"
Cohesion: 0.83
Nodes (4): duckduckgo-search, google-generativeai, LinkedIn Agent Project, requests

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Are the 2 inferred relationships involving `requests` (e.g. with `google-generativeai` and `duckduckgo-search`) actually correct?**
  _`requests` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LinkedIn Agent Project` (e.g. with `google-generativeai` and `duckduckgo-search`) actually correct?**
  _`LinkedIn Agent Project` has 2 INFERRED edges - model-reasoned connections that need verification._