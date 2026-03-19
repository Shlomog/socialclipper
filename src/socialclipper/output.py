"""Create output folder and render drafts markdown."""

import json
from datetime import datetime
from pathlib import Path

from .config import format_time


def create_output_folder(base_dir: Path, source_name: str) -> Path:
    """Create a timestamped output folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean = "".join(c for c in source_name if c.isalnum() or c in "-_ ")[:50].strip()
    folder = base_dir / f"{timestamp}_{clean}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "clips").mkdir(exist_ok=True)
    return folder


def save_results(
    output_dir: Path,
    analysis: dict,
    drafts: list[dict],
    transcript: dict,
    source_name: str,
) -> Path:
    """Save analysis, transcript, and drafts to the output folder."""
    # Save raw JSON files
    (output_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "transcript.json").write_text(
        json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Render drafts.md
    md = render_drafts_markdown(drafts, analysis, source_name)
    drafts_path = output_dir / "drafts.md"
    drafts_path.write_text(md, encoding="utf-8")

    return drafts_path


def render_drafts_markdown(
    drafts: list[dict],
    analysis: dict,
    source_name: str,
) -> str:
    """Render all drafts into a markdown file."""
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    lines = [
        f"# SocialClipper Output: {source_name}",
        f"*Generated {now}*",
        "",
        "## Video Summary",
        analysis.get("full_summary", ""),
        "",
        f"**Key themes:** {', '.join(analysis.get('key_themes', []))}",
        "",
        "---",
        "",
    ]

    for i, draft in enumerate(drafts, 1):
        clip_file = f"clip_{i}_{draft['platform']}.mp4"
        lines.extend([
            f"## Clip {i}: {draft['clip_title']}",
            "",
            f"**Platform:** {draft['platform_name']}  ",
            f"**Content Type:** {draft['content_type']}  ",
            f"**Brand Pillar:** {draft['brand_pillar']}  ",
            f"**Timestamp:** {format_time(draft['start_time'])} - "
            f"{format_time(draft['end_time'])}  ",
            f"**Video file:** `{clip_file}`",
            "",
            "### Draft Post",
            "",
            draft["draft_text"],
            "",
            "---",
            "",
        ])

    return "\n".join(lines)
