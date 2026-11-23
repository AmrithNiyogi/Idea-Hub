---
name: idea-hub-code-review-graph
description: Build, update, and query the KonnektIdea code-review-graph MCP for call graphs, blast radius, and reviews. Use when exploring relationships, reviewing diffs, or after major structural changes.
---

# code-review-graph for KonnektIdea

## MCP

Project config: `.cursor/mcp.json` runs `uvx code-review-graph serve` (stdio).

In Cursor the tools appear under namespace **`user-code-review-graph`**.

## First-time / after major changes

```bash
cd /home/nakula/Desktop/DotKonnekt/REPOS/Idea-Hub
uvx code-review-graph register .
uvx code-review-graph build
uvx code-review-graph status
```

Incremental: `uvx code-review-graph update` or MCP `build_or_update_graph_tool`.

## Agent workflow (token-efficient)

1. `get_minimal_context_tool` or `list_graph_stats_tool` — confirm graph is built
2. Prefer `query_graph_tool` with a specific symbol over broad list calls
3. Reviews → `detect_changes_tool` / `get_review_context_tool`
4. Impact → `get_impact_radius_tool`
5. Keep ≤5 graph calls when possible; use `detail_level="minimal"` when available

## Verify connected

- Cursor Settings → MCP → `code-review-graph` shows green / connected
- Or ask the agent to call `list_graph_stats_tool` and expect node/edge counts
- Graph DB: `.code-review-graph/` (local; do not commit secrets — DB is derived from source)

## Not for

Plain-text / env-key / comment searches — use Grep.
