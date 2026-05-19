---
name: content-extract
description: Use this skill when the user wants to extract, summarize, or convert a webpage into clean markdown, especially when the page is messy, partially blocked, or likely to need MinerU fallback.
version: 0.1.0
---

# content-extract for Claude Code

This skill turns a URL into traceable markdown output.

## Preferred flow

1. Try Claude Code `WebFetch` first for low-cost extraction.
2. If the content is blocked, incomplete, or obviously low quality, call the local fallback script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/content-extract/scripts/content_extract.py --url "<url>"
```

3. Return the result contract with:
   - `source_url`
   - `engine`
   - `markdown`
   - artifact paths
   - `sources`
   - notes / next steps

## Use MinerU fallback when

- The page is on a known anti-bot domain
- WebFetch returns incomplete or noisy content
- The user explicitly wants higher-fidelity extraction

## Requirements

- Do not invent sources.
- Preserve source URLs and artifact paths in your response.
- If both probe and fallback fail, explain the actionable next step.
