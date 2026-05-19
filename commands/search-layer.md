---
description: Run multi-source search-layer search for a query
argument-hint: <query>
allowed-tools: [Bash, Read]
model: sonnet
---

# search-layer command

The user invoked this command with: $ARGUMENTS

## Instructions

1. Treat `$ARGUMENTS` as the search query.
2. Run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/search-layer/scripts/search.py "$ARGUMENTS" --mode deep --num 5`
3. Summarize the most relevant results.
4. If the command output includes URLs, present them clearly.
5. If the user asked for current information gathered from web tools in your final answer, include a `Sources:` section.
