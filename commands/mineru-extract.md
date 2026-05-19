---
description: Parse a URL with the official MinerU API
argument-hint: <url>
allowed-tools: [Bash, Read]
model: sonnet
---

# mineru-extract command

The user invoked this command with: $ARGUMENTS

## Instructions

1. Treat `$ARGUMENTS` as a URL.
2. Run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/mineru-extract/scripts/mineru_extract.py "$ARGUMENTS" --print`
3. Report whether parsing succeeded and where artifacts were saved.
4. If parsing fails, include the actionable error from stderr.
