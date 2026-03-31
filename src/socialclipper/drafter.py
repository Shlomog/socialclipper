"""Generate social media drafts using Claude."""

from .config import CLAUDE_MODEL, PLATFORM_SPECS, VOICE_SYSTEM_PROMPT, get_anthropic_client, load_voice_strategy


def generate_drafts(
    analysis: dict,
    context: str | None = None,
    on_progress=None,
) -> list[dict]:
    """Generate a publish-ready draft for each clip.

    Returns list of dicts with draft_text, platform info, etc.
    """
    if on_progress:
        on_progress("Writing social media drafts...")

    client = get_anthropic_client()
    drafts = []

    voice_strategy = load_voice_strategy()
    system_prompt = VOICE_SYSTEM_PROMPT
    if voice_strategy:
        system_prompt += (
            "\n\nSPEAKER'S VOICE STRATEGY (use this to guide tone, framing, "
            "and what to emphasize in the draft):\n" + voice_strategy
        )

    for i, clip in enumerate(analysis["clips"]):
        if on_progress:
            on_progress(f"Drafting post {i + 1} of {len(analysis['clips'])}...")

        spec = PLATFORM_SPECS.get(clip["platform"], PLATFORM_SPECS["linkedin"])

        user_message = f"""Write a {spec['name']} post based on this video clip.

Clip title: {clip['title']}
Content type: {clip['content_type']}
Brand pillar: {clip['brand_pillar']}
Suggested hook: {clip['hook_suggestion']}

Transcript excerpt from the clip:
\"\"\"{clip['transcript_excerpt']}\"\"\"

{f"Additional context: {context}" if context else ""}

PLATFORM REQUIREMENTS:
- Format: {spec['name']}
- Word count: {spec['draft_word_range'][0]}-{spec['draft_word_range'][1]} words
- Hashtags: {spec['hashtag_count'][0]}-{spec['hashtag_count'][1]}
{"- Hook in first line. Line breaks between paragraphs. End with a question or clear takeaway." if clip['platform'] == 'linkedin' else ""}
{"- Warm, conversational tone." if 'instagram' in clip['platform'] else ""}

Write the post directly. No commentary, no labels, no "here's your post." \
Just the publish-ready text followed by hashtags on a new line."""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        draft_text = response.content[0].text.strip()

        drafts.append({
            "clip_title": clip["title"],
            "platform": clip["platform"],
            "platform_name": spec["name"],
            "content_type": clip["content_type"],
            "brand_pillar": clip["brand_pillar"],
            "start_time": clip["start_time"],
            "end_time": clip["end_time"],
            "draft_text": draft_text,
            "reasoning": clip.get("reasoning", ""),
        })

    return drafts
