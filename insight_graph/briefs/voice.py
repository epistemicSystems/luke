"""
Voice readout generation for briefs.

Converts daily/weekly briefs to TTS-optimized scripts and generates audio.
"""

import os
from pathlib import Path
from typing import Optional

from openai import OpenAI


class VoiceGenerator:
    """
    Generates voice readouts of briefs.

    Uses OpenAI TTS to create audio summaries for hands-free consumption.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_from_brief(
        self,
        brief_text: str,
        output_filename: str = "daily_brief.mp3",
        voice: str = "alloy",
    ) -> Path:
        """
        Generate TTS audio from a brief.

        Args:
            brief_text: Brief text content
            output_filename: Output file name
            voice: OpenAI TTS voice (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            Path to generated audio file
        """
        # Clean text for TTS (remove markdown, emojis, etc.)
        tts_text = self._prepare_for_tts(brief_text)

        # Generate audio
        response = self.openai.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=tts_text,
        )

        # Save to file
        output_path = self.output_dir / output_filename
        response.stream_to_file(output_path)

        return output_path

    def _prepare_for_tts(self, text: str) -> str:
        """
        Prepare text for TTS.

        Removes:
        - Markdown formatting
        - Emojis
        - Special characters
        - Multiple newlines

        Returns:
            Cleaned text optimized for speech
        """
        import re

        # Remove markdown headers
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove markdown bold/italic
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)

        # Remove markdown lists (keep content)
        text = re.sub(r"^[\*\-•]\s+", "", text, flags=re.MULTILINE)

        # Remove emojis (basic pattern)
        text = re.sub(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
            "",
            text,
        )

        # Remove special formatting characters
        text = text.replace("_", " ")
        text = text.replace("`", "")

        # Collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Add natural pauses for TTS
        text = text.replace("\n\n", ". ")
        text = text.replace("\n", ", ")

        # Clean up extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def generate_60s_summary(
        self,
        full_brief: str,
        output_filename: str = "brief_60s.mp3",
    ) -> Path:
        """
        Generate a 60-second summary version.

        Uses LLM to condense the brief to ~150 words (60s at normal pace).

        Args:
            full_brief: Full brief text
            output_filename: Output file name

        Returns:
            Path to generated audio file
        """
        # Condense with LLM
        response = self.openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You condense dev briefs to 60-second voice summaries (~150 words). "
                    "Focus on top blockers and actionable items. Use natural speech patterns.",
                },
                {
                    "role": "user",
                    "content": f"Condense this brief to ~150 words for a 60-second voice readout:\n\n{full_brief}",
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )

        condensed = response.choices[0].message.content

        # Generate TTS
        return self.generate_from_brief(condensed, output_filename)


# CLI
def main():
    """Generate voice readout from a brief file."""
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m insight_graph.briefs.voice <brief_file.txt>")
        sys.exit(1)

    brief_path = Path(sys.argv[1])
    if not brief_path.exists():
        print(f"Error: {brief_path} not found")
        sys.exit(1)

    brief_text = brief_path.read_text()

    # Generate voice
    output_dir = Path("./data/voice")
    generator = VoiceGenerator(output_dir)

    # Full version
    full_audio = generator.generate_from_brief(brief_text, "daily_brief_full.mp3")
    print(f"Generated full audio: {full_audio}")

    # 60s version
    short_audio = generator.generate_60s_summary(brief_text, "daily_brief_60s.mp3")
    print(f"Generated 60s audio: {short_audio}")


if __name__ == "__main__":
    main()
