"""Configuration: voice rules, platform specs, prompt templates."""

import os
from pathlib import Path

CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_VOICE_PROFILE_PATH = _BASE_DIR / "voice_profile.txt"
_API_KEY_PATH = _BASE_DIR / "api_key.txt"


# ---------------------------------------------------------------------------
# API key — stored in file, falls back to env var
# ---------------------------------------------------------------------------
def load_api_key() -> str | None:
    """Load Anthropic API key from file, falling back to ANTHROPIC_API_KEY env var."""
    if _API_KEY_PATH.exists():
        key = _API_KEY_PATH.read_text(encoding="utf-8").strip()
        if key:
            return key
    return os.environ.get("ANTHROPIC_API_KEY")


def save_api_key(key: str) -> None:
    """Save API key to api_key.txt."""
    _API_KEY_PATH.write_text(key.strip(), encoding="utf-8")


def delete_api_key() -> None:
    """Delete the stored API key file (reverts to env var)."""
    if _API_KEY_PATH.exists():
        _API_KEY_PATH.unlink()


def get_anthropic_client():
    """Create an Anthropic client using the configured API key."""
    import anthropic
    key = load_api_key()
    if not key:
        raise RuntimeError(
            "No Anthropic API key configured. Add one in Settings or set ANTHROPIC_API_KEY."
        )
    return anthropic.Anthropic(api_key=key)


# ---------------------------------------------------------------------------
# Voice strategy — user-defined content strategy loaded from file
# ---------------------------------------------------------------------------


def load_voice_strategy() -> str | None:
    """Load the user's voice strategy from voice_profile.txt, or None if not set."""
    if _VOICE_PROFILE_PATH.exists():
        text = _VOICE_PROFILE_PATH.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def save_voice_strategy(text: str) -> None:
    """Save the user's voice strategy to voice_profile.txt."""
    _VOICE_PROFILE_PATH.write_text(text.strip(), encoding="utf-8")


def delete_voice_strategy() -> None:
    """Delete the voice strategy file, reverting to defaults."""
    if _VOICE_PROFILE_PATH.exists():
        _VOICE_PROFILE_PATH.unlink()

# ---------------------------------------------------------------------------
# Platform specifications
# ---------------------------------------------------------------------------
PLATFORM_SPECS = {
    "linkedin": {
        "name": "LinkedIn",
        "video_format": "landscape",
        "aspect_ratio": "16:9",
        "resolution": "1920x1080",
        "max_duration_sec": 600,
        "min_duration_sec": 30,
        "draft_word_range": (200, 400),
        "hashtag_count": (2, 3),
        "ffmpeg_vf": (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
        ),
    },
    "instagram-reel": {
        "name": "Instagram Reel",
        "video_format": "vertical",
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "max_duration_sec": 60,
        "min_duration_sec": 15,
        "draft_word_range": (50, 150),
        "hashtag_count": (5, 8),
        "ffmpeg_vf": (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        ),
    },
}

CONTENT_TYPES = ["Authority", "Story", "Commentary", "Connection"]
BRAND_PILLARS = ["Thought Leadership", "Innovation", "Authenticity"]

# ---------------------------------------------------------------------------
# Voice profile — customize this for your brand/personal voice
# ---------------------------------------------------------------------------
VOICE_SYSTEM_PROMPT = """\
You are a social media content writer. You write publish-ready social media \
posts that capture the speaker's authentic voice from their video content.

VOICE RULES:
- Warm but direct. Evidence over opinion. Accessible but not dumbed down.
- First-person, real experiences.
- Match the speaker's tone and vocabulary from the transcript.
- NEVER uses: "Excited to announce," "Game-changer," em dashes, \
"leverage/synergy/paradigm," or overly promotional language.
- No em dashes. Use periods, commas, or line breaks instead.

QUALITY CHECKLIST (apply to every draft):
- Does the first line hook immediately?
- Is every sentence earning its place?
- No em dashes anywhere?
- Does it sound like the actual speaker, not a PR team?
- Is it evidence-based where claims are made?
- No corporate filler?
"""

# ---------------------------------------------------------------------------
# Analysis prompt template
# ---------------------------------------------------------------------------
ANALYSIS_SYSTEM_PROMPT = """\
You are a content strategist analyzing a video transcript to identify \
the best moments for social media clips.

Selection criteria for clip-worthy moments:
1. Strong emotional hooks (personal stories, surprising stats, relatable moments)
2. Clear, standalone insights that work without extra context
3. Moments that showcase the speaker's expertise or personal experience
4. Quotable statements or memorable takeaways
5. Content that fits naturally within platform duration limits
6. Moments where the speaker speaks with conviction or passion

For Instagram Reels, prioritize moments that are:
- Conversational and warm
- One clear tip or insight
- 15-60 seconds of natural speech

For LinkedIn, prioritize moments that are:
- Substantive and thought-provoking
- Data-driven or experience-backed
- Discussion-worthy for professionals

Content types: Authority, Story, Commentary, Connection
Brand pillars: Thought Leadership, Innovation, Authenticity
"""


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
