---
name: search-layer
description: Use this skill when the user asks for web research, factual lookups, comparisons, recent status checks, finding official resources, or broader search synthesis. It combines Claude Code web tools with the bundled multi-source Python search script for Exa, Tavily, and Grok, then merges and ranks results.
version: 0.1.0
---

# search-layer for Claude Code

Use this skill for broad web lookup tasks that benefit from more than one source.

## When to use

- Factual lookups
- Status / latest updates
- Comparisons
- Tutorial/resource discovery
- Exploratory research
- GitHub issue / PR thread follow-up after search

## Execution model

1. Classify intent: `factual`, `status`, `comparison`, `tutorial`, `exploratory`, `news`, or `resource`.
2. Use Claude Code `WebSearch` for broad web coverage when current web results are needed.
3. Use the bundled script for Exa/Tavily/Grok aggregation when API keys are configured:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/search-layer/scripts/search.py "<query>" --mode deep --intent <intent> --num 5
```

4. Merge sources by URL, prioritize authority/freshness by intent, then answer.
5. If you used Claude Code `WebSearch` in the final answer, include a `Sources:` section.

## Notes

- The bundled Python script cannot call Claude Code web tools directly; those stay at the agent layer.
- Credentials may be supplied via environment variables or `credentials/search.json`.
- For deeper follow-up on GitHub/forum threads, use `search-layer/scripts/fetch_thread.py` after identifying a promising URL.
