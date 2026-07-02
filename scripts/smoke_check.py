from youtube_transcript_mcp.server import extract_video_id

CASES = {
    "dQw4w9WgXcQ": "dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ": "dQw4w9WgXcQ",
}

for raw, expected in CASES.items():
    got = extract_video_id(raw)
    assert got == expected, f"{raw!r} -> {got!r}, expected {expected!r}"

print("ok")
