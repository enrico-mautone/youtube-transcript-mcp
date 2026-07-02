import tempfile
import unittest
from pathlib import Path

from youtube_transcript_mcp import server


class MarkdownBehaviorTests(unittest.TestCase):
    def test_build_transcript_markdown_contains_core_sections(self) -> None:
        markdown = server.build_transcript_markdown(
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            language_code="en",
            language="English",
            is_generated=False,
            segments=[
                server.TranscriptSegment(text="Hello world", start=1.0, duration=2.0),
            ],
        )

        self.assertIn("# YouTube transcript", markdown)
        self.assertIn("- **Video ID:** `dQw4w9WgXcQ`", markdown)
        self.assertIn("- **Language:** `English` (`en`)", markdown)
        self.assertIn("## Transcript", markdown)
        self.assertIn("**[00:01.00]** Hello world", markdown)

    def test_save_transcript_markdown_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            path = server.save_transcript_markdown(
                output_dir=output_dir,
                video_title="Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
                video_id="dQw4w9WgXcQ",
                source_url="https://youtu.be/dQw4w9WgXcQ",
                language_code="en",
                language="English",
                is_generated=False,
                segments=[
                    server.TranscriptSegment(text="Hello world", start=1.0, duration=2.0),
                ],
            )

            self.assertTrue(path.exists())
            self.assertEqual(
                path.name,
                "Rick-Astley-Never-Gonna-Give-You-Up-Official-Video-4K-Remaster.dQw4w9WgXcQ.en.manual.md",
            )
            self.assertTrue(path.read_text(encoding="utf-8").startswith("# YouTube transcript"))


if __name__ == "__main__":
    unittest.main()
