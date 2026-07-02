# YouTube Transcript MCP

A minimal Model Context Protocol server for retrieving YouTube transcripts.

## Features

- `list_transcripts(video_id)`
- `get_transcript(video_id, language_code=None)`
- `get_transcript_from_url(url, language_code=None)`

The transcript tools now return Markdown and also save a `.md` file under `./transcripts/`.
Supports standard YouTube watch URLs, shorts URLs, and `youtu.be` links.

## Setup

```bash
cd ~/youtube-transcript-mcp
uv sync
```

## Run

```bash
uv run youtube-transcript-mcp
```

The server uses stdio transport, so it is suitable for MCP clients that launch local tools.

## GitHub readiness

This repository includes:

- packaging via `pyproject.toml`
- a `LICENSE`
- `.gitignore` for virtualenvs, build artifacts, caches, and generated transcripts
- GitHub Actions CI in `.github/workflows/ci.yml`
- unit tests and a build step

## Example MCP client config

```json
{
  "mcpServers": {
    "youtube-transcript-mcp": {
      "command": "uv",
      "args": ["run", "youtube-transcript-mcp"],
      "cwd": "/home/enrico/youtube-trancscript-mcp"
    }
  }
}
```

## Example usage

- `list_transcripts("dQw4w9WgXcQ")`
- `get_transcript("dQw4w9WgXcQ", "en")`
- `get_transcript_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")`
