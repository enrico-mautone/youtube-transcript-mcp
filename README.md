# youtube-transcript-mcp

A minimal Model Context Protocol server for retrieving YouTube transcripts.

## Features

- `list_transcripts(video_id)`
- `get_transcript(video_id, language_code=None)`
- `get_transcript_from_url(url, language_code=None)`

The transcript tools return Markdown and save a `.md` file under `./transcripts/`.
Markdown rendering is handled with `markdown-it-py` (`MarkdownIt`).
Supports standard YouTube watch URLs, shorts URLs, and `youtu.be` links.

## Setup

```bash
git clone https://github.com/enrico-mautone/youtube-transcript-mcp.git
cd youtube-transcript-mcp
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
      "cwd": "/path/to/youtube-transcript-mcp"
    }
  }
}
```

## Example usage

- `list_transcripts("dQw4w9WgXcQ")`
- `get_transcript("dQw4w9WgXcQ", "en")`
- `get_transcript_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")`
