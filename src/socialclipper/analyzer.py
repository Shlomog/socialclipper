"""Analyze transcript with Claude to find clip-worthy moments."""

import json
import anthropic

from .config import (
    ANALYSIS_SYSTEM_PROMPT,
    CLAUDE_MODEL,
    PLATFORM_SPECS,
    CONTENT_TYPES,
    BRAND_PILLARS,
    format_time,
)


def analyze_transcript(
    transcript: dict,
    platforms: list[str],
    max_clips: int = 4,
    context: str | None = None,
    on_progress=None,
) -> dict:
    """Use Claude to identify the best clip-worthy moments.

    Returns dict with:
        - "clips": list of clip recommendations
        - "full_summary": short summary of the full video
        - "key_themes": list of themes
    """
    if on_progress:
        on_progress("Analyzing transcript for the best moments...")

    client = anthropic.Anthropic()

    # Build timestamped transcript text — use raw seconds so Claude returns seconds
    segments_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}"
        for s in transcript["segments"]
    )

    platform_descriptions = "\n".join(
        f"- {PLATFORM_SPECS[p]['name']}: "
        f"{PLATFORM_SPECS[p]['min_duration_sec']}-{PLATFORM_SPECS[p]['max_duration_sec']}s, "
        f"{PLATFORM_SPECS[p]['video_format']} ({PLATFORM_SPECS[p]['aspect_ratio']}), "
        f"draft {PLATFORM_SPECS[p]['draft_word_range'][0]}-"
        f"{PLATFORM_SPECS[p]['draft_word_range'][1]} words"
        for p in platforms
    )

    system = (
        ANALYSIS_SYSTEM_PROMPT
        + f"\n\nTarget platforms:\n{platform_descriptions}\n"
        f"Content types: {', '.join(CONTENT_TYPES)}\n"
        f"Brand pillars: {', '.join(BRAND_PILLARS)}"
    )

    user_message = f"""Analyze this video transcript and identify the {max_clips} best \
clip-worthy moments for social media.

{f"Additional context: {context}" if context else ""}

TRANSCRIPT:
{segments_text}

IMPORTANT: All timestamps in the transcript above are in SECONDS from the start of \
the video (e.g. 867.0s means 14 minutes 27 seconds in). Your start_time and end_time \
values MUST also be in seconds. A typical clip should be 15-120 seconds long.

Respond ONLY with valid JSON (no markdown fences) in this exact structure:
{{
  "clips": [
    {{
      "title": "short descriptive title for this clip",
      "start_time": 867.0,
      "end_time": 919.0,
      "transcript_excerpt": "the exact text spoken in this segment",
      "platform": "linkedin or instagram-reel",
      "content_type": "Authority or Story or Commentary or Connection",
      "brand_pillar": "Thought Leadership or Innovation or Authenticity",
      "reasoning": "why this moment works as a clip",
      "hook_suggestion": "suggested opening line for the social post"
    }}
  ],
  "full_summary": "2-3 sentence summary of the full video",
  "key_themes": ["theme1", "theme2", "theme3"]
}}

NOTE: start_time and end_time are in SECONDS (not minutes). Match them to the \
[Xs - Ys] timestamps in the transcript above."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Claude returned invalid JSON. Response:\n{text[:500]}")
