---
name: mineru-extract
description: Use this skill when WebFetch is insufficient and you need the official MinerU API to parse HTML, PDF, Office, or image content into cleaner markdown with artifacts and traceable output.
version: 0.1.0
---

# mineru-extract for Claude Code

Use MinerU as the heavy-duty parsing backend.

## What it does

- Submits a URL to MinerU
- Polls until parsing completes
- Downloads the result archive
- Extracts the best markdown artifact
- Returns structured output paths

## Typical invocation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/mineru-extract/scripts/mineru_parse_documents.py \
  --file-sources "<url>" \
  --model-version MinerU-HTML \
  --emit-markdown --max-chars 20000
```

Or low-level:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/mineru-extract/scripts/mineru_extract.py "<url>" --print
```

## Requirements

- `MINERU_TOKEN` must be configured.
- Keep original URLs and artifact paths in the final response.
- If MinerU fails, surface the concrete failure and suggest the next usable fallback.
