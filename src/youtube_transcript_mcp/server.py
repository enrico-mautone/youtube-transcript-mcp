from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from markdown_it import MarkdownIt
from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("youtube_transcript_mcp")

mcp = FastMCP("youtube-transcript-mcp")
api = YouTubeTranscriptApi()
# Markdown rendering uses markdown-it-py (MarkdownIt).
md = MarkdownIt("commonmark")

VIDEO_ID_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
DEFAULT_OUTPUT_DIR = Path("transcripts")


@dataclass(frozen=True)
class TranscriptInfo:
    language_code: str
    language: str
    is_generated: bool
    is_translatable: bool


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    duration: float


def _normalize_host(netloc: str) -> str:
    host = netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _slugify_filename_part(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "untitled"


def fetch_video_title(source_url: str, default: str = "untitled") -> str:
    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": source_url, "format": "json"},
            timeout=20,
        )
        response.raise_for_status()
        title = response.json().get("title", "")
        if isinstance(title, str) and title.strip():
            return title.strip()
    except Exception:
        logger.exception("Failed to fetch video title for %s", source_url)
    return default


def _format_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, int(round(seconds * 100)))
    total_seconds, centiseconds = divmod(total_centiseconds, 100)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    return f"{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _render_and_validate_markdown(markdown: str) -> str:
    # MarkdownIt is used here to validate the generated markdown structure.
    md.render(markdown)
    return markdown


def extract_video_id(value: str) -> str:
    """Extract a YouTube video ID from a raw ID or a supported URL."""

    candidate = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate

    parsed = urlparse(candidate)
    host = _normalize_host(parsed.netloc)

    if host in {"youtu.be"}:
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            candidate = path_parts[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        else:
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
                candidate = path_parts[1]
            else:
                match = VIDEO_ID_RE.search(candidate)
                if match:
                    candidate = match.group(1)
    else:
        match = VIDEO_ID_RE.search(candidate)
        if match:
            candidate = match.group(1)

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        raise ValueError(f"Could not parse a YouTube video ID from: {value}")

    return candidate


def _segments_to_dicts(segments: Any) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            text=str(getattr(segment, "text", "")).strip(),
            start=float(getattr(segment, "start", 0.0)),
            duration=float(getattr(segment, "duration", 0.0)),
        )
        for segment in segments
    ]


def _transcript_list_info(video_id: str) -> dict[str, Any]:
    transcript_list = api.list(video_id)
    manual = [
        TranscriptInfo(
            language_code=transcript.language_code,
            language=transcript.language,
            is_generated=transcript.is_generated,
            is_translatable=transcript.is_translatable,
        )
        for transcript in transcript_list._manually_created_transcripts.values()
    ]
    generated = [
        TranscriptInfo(
            language_code=transcript.language_code,
            language=transcript.language,
            is_generated=transcript.is_generated,
            is_translatable=transcript.is_translatable,
        )
        for transcript in transcript_list._generated_transcripts.values()
    ]
    translation_languages = [
        {"language_code": language.language_code, "language": language.language}
        for language in transcript_list._translation_languages
    ]

    return {
        "video_id": video_id,
        "manual_transcripts": [asdict(item) for item in manual],
        "generated_transcripts": [asdict(item) for item in generated],
        "translation_languages": translation_languages,
    }


def _pick_transcript(video_id: str, language_code: str | None):
    transcript_list = api.list(video_id)
    if language_code:
        return transcript_list.find_transcript([language_code])

    preferred_codes = list(transcript_list._manually_created_transcripts.keys()) + list(
        transcript_list._generated_transcripts.keys()
    )
    if not preferred_codes:
        raise NoTranscriptFound(video_id)
    return transcript_list.find_transcript(preferred_codes)


def build_transcript_markdown(
    *,
    video_id: str,
    source_url: str,
    language_code: str,
    language: str,
    is_generated: bool,
    segments: list[TranscriptSegment],
) -> str:
    transcript_lines = []
    for segment in segments:
        timestamp = _format_timestamp(segment.start)
        transcript_lines.append(f"**[{timestamp}]** {segment.text}")

    markdown = "\n".join(
        [
            "# YouTube transcript",
            "",
            f"- **Video ID:** `{video_id}`",
            f"- **Source:** {source_url}",
            f"- **Language:** `{language}` (`{language_code}`)",
            f"- **Generated:** {'Yes' if is_generated else 'No'}",
            "",
            "## Transcript",
            "",
            *transcript_lines,
            "",
        ]
    )
    return _render_and_validate_markdown(markdown)


def save_transcript_markdown(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    video_title: str | None = None,
    video_id: str,
    source_url: str,
    language_code: str,
    language: str,
    is_generated: bool,
    segments: list[TranscriptSegment],
) -> Path:
    markdown = build_transcript_markdown(
        video_id=video_id,
        source_url=source_url,
        language_code=language_code,
        language=language,
        is_generated=is_generated,
        segments=segments,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "generated" if is_generated else "manual"
    safe_language = _slugify_filename_part(language_code or "unknown")
    safe_title = _slugify_filename_part(video_title or fetch_video_title(source_url))
    path = output_dir / f"{safe_title}.{video_id}.{safe_language}.{suffix}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


@mcp.tool()
def list_transcripts(video_id: str) -> str:
    """List available transcripts for a YouTube video."""

    normalized_video_id = extract_video_id(video_id)
    payload = _transcript_list_info(normalized_video_id)

    lines = ["# Available transcripts", "", f"- **Video ID:** `{normalized_video_id}`", ""]
    if payload["manual_transcripts"]:
        lines.extend(["## Manual", ""])
        for item in payload["manual_transcripts"]:
            lines.append(
                f"- `{item['language_code']}` — {item['language']}"
                f"{' (translatable)' if item['is_translatable'] else ''}"
            )
        lines.append("")
    if payload["generated_transcripts"]:
        lines.extend(["## Generated", ""])
        for item in payload["generated_transcripts"]:
            lines.append(
                f"- `{item['language_code']}` — {item['language']}"
                f"{' (translatable)' if item['is_translatable'] else ''}"
            )
        lines.append("")
    if payload["translation_languages"]:
        lines.extend(["## Translation languages", ""])
        lines.append(
            ", ".join(
                f"`{language['language_code']}` ({language['language']})"
                for language in payload["translation_languages"]
            )
        )
        lines.append("")

    return _render_and_validate_markdown("\n".join(lines))


@mcp.tool()
def get_transcript(video_id: str, language_code: str | None = None) -> str:
    """Fetch a transcript for a YouTube video.

    Args:
        video_id: A raw YouTube video ID or URL.
        language_code: Optional transcript language code (e.g. en, en-US).
    """

    normalized_video_id = extract_video_id(video_id)
    source_url = f"https://www.youtube.com/watch?v={normalized_video_id}"
    video_title = fetch_video_title(source_url, default=normalized_video_id)
    try:
        transcript = _pick_transcript(normalized_video_id, language_code)
        segments = transcript.fetch()
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as exc:
        return _render_and_validate_markdown(
            "\n".join(
                [
                    "# YouTube transcript",
                    "",
                    f"> **Error:** {type(exc).__name__}",
                    f"> {str(exc)}",
                    "",
                ]
            )
        )

    segment_models = _segments_to_dicts(segments)
    markdown = build_transcript_markdown(
        video_id=normalized_video_id,
        source_url=source_url,
        language_code=transcript.language_code,
        language=transcript.language,
        is_generated=transcript.is_generated,
        segments=segment_models,
    )
    save_transcript_markdown(
        video_title=video_title,
        video_id=normalized_video_id,
        source_url=source_url,
        language_code=transcript.language_code,
        language=transcript.language,
        is_generated=transcript.is_generated,
        segments=segment_models,
    )
    return markdown


@mcp.tool()
def get_transcript_from_url(url: str, language_code: str | None = None) -> str:
    """Fetch a transcript from a YouTube URL."""

    video_id = extract_video_id(url)
    return get_transcript(video_id, language_code)


def main() -> None:
    logger.info("Starting youtube-transcript-mcp on stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
