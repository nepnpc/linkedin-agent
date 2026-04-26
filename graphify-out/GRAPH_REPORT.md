# Graph Report - C:\Users\User\Documents\linkedin-agent  (2026-04-27)

## Corpus Check
- 3 files · ~1,200 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 26 nodes · 36 edges · 3 communities detected
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Agent Pipeline Functions|Agent Pipeline Functions]]
- [[_COMMUNITY_Graph Report Concepts|Graph Report Concepts]]
- [[_COMMUNITY_Dependencies and Trending|Dependencies and Trending]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 10 edges
2. `main()` - 9 edges
3. `LinkedIn Agent Project` - 4 edges
4. `requests` - 3 edges
5. `load_post_history()` - 2 edges
6. `save_post_history()` - 2 edges
7. `should_post()` - 2 edges
8. `fetch_github_events()` - 2 edges
9. `fetch_trending_news()` - 2 edges
10. `generate_post_content()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `generate_post_content()` --references--> `google-generativeai`  [INFERRED]
  graphify-out/GRAPH_REPORT.md → requirements.txt
- `fetch_trending_news()` --references--> `duckduckgo-search (ddgs)`  [INFERRED]
  graphify-out/GRAPH_REPORT.md → requirements.txt
- `fetch_github_events()` --references--> `requests`  [INFERRED]
  graphify-out/GRAPH_REPORT.md → requirements.txt
- `fetch_unsplash_image()` --references--> `requests`  [INFERRED]
  graphify-out/GRAPH_REPORT.md → requirements.txt
- `LinkedIn Agent Project` --conceptually_related_to--> `Python Dependencies`  [EXTRACTED]
  requirements.txt → graphify-out/GRAPH_REPORT.md

## Hyperedges (group relationships)
- **LinkedIn Agent Python Dependencies** — requirements_linkedin_agent, requirements_google_generativeai, requirements_duckduckgo_search, requirements_requests [EXTRACTED 1.00]

## Communities

### Community 0 - "Agent Pipeline Functions"
Cohesion: 0.35
Nodes (10): fetch_github_events(), fetch_trending_news(), fetch_unsplash_image(), generate_post_content(), load_post_history(), main(), publish_to_linkedin(), save_post_history() (+2 more)

### Community 1 - "Graph Report Concepts"
Cohesion: 0.25
Nodes (5): Agent Pipeline Functions, fetch_github_events(), fetch_unsplash_image(), main(), requests

### Community 2 - "Dependencies and Trending"
Cohesion: 0.33
Nodes (6): Python Dependencies, fetch_trending_news(), generate_post_content(), duckduckgo-search (ddgs), google-generativeai, LinkedIn Agent Project

## Knowledge Gaps
- **2 isolated node(s):** `Agent Pipeline Functions`, `Python Dependencies`
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Graph Report Concepts` to `Dependencies and Trending`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Why does `LinkedIn Agent Project` connect `Dependencies and Trending` to `Graph Report Concepts`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `requests` (e.g. with `fetch_github_events()` and `fetch_unsplash_image()`) actually correct?**
  _`requests` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Agent Pipeline Functions`, `Python Dependencies` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._