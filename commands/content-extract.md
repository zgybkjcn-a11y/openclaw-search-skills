---
description: Extract a URL to markdown with MinerU fallback
argument-hint: <url>
allowed-tools: [Bash, Read]
model: sonnet
---

# content-extract command

The user invoked this command with: $ARGUMENTS

## Instructions

1. Treat `$ARGUMENTS` as a URL.
2. Run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/content-extract/scripts/content_extract.py --url "$ARGUMENTS"`
3. Parse the JSON output.
4. Report whether extraction succeeded, which engine was used, and any artifact paths or source URLs.
