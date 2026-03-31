# SocialClipper

AI-powered video-to-social-clips pipeline. Drop in a video (or paste a YouTube URL), and SocialClipper will:

1. **Transcribe** it locally using [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) (Apple Silicon optimized)
2. **Analyze** the transcript with Claude to find the best clip-worthy moments
3. **Extract** video clips with ffmpeg, formatted for each platform (LinkedIn 16:9, Instagram Reels 9:16)
4. **Draft** publish-ready social media posts in the speaker's voice
5. **Serve** everything in a clean web UI with a library of past runs

## Screenshots

![Home page — overview and getting started](docs/screenshot-home.png?v=2)

![Create page — paste a URL or upload a video](docs/screenshot-create.png?v=2)

![Voice Strategy — define your content strategy](docs/screenshot-voice.png?v=2)

![Settings — API key and cost breakdown](docs/screenshot-settings.png?v=2)

## Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4) — MLX Whisper requires it
- **Python 3.12+**
- **ffmpeg** — for video processing
- **yt-dlp** — for downloading videos from URLs
- **Anthropic API key** — for Claude-powered analysis and drafting

> **Warning:** Never commit your API key! You can add it directly in the Settings page, or copy `.env.example` to `.env`. Both are gitignored.

> **Apple Silicon required.** MLX Whisper only runs on Macs with M1/M2/M3/M4 chips.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Shlomog/socialclipper.git
cd socialclipper

# 2. Run the installer (installs ffmpeg, yt-dlp, Python deps)
chmod +x install.sh
./install.sh

# 3. Start the server
./run.sh

# 4. Open http://localhost:8000
# 5. Add your Anthropic API key in Settings
# 6. Set up your Voice Strategy
# 7. Create your first clips!
```

## How It Works

### Pipeline

```
Video/URL → Transcribe (Whisper) → Analyze (Claude) → Draft Posts (Claude) → Extract Clips (ffmpeg)
```

Each run produces:
- `clips/` — MP4 files formatted per platform
- `analysis.json` — Claude's clip recommendations with timestamps
- `transcript.json` — Full timestamped transcript
- `drafts.md` — Ready-to-post social media copy

### Web UI

The app guides you through a simple flow:

1. **Settings** — Add your Anthropic API key (one-time setup)
2. **Voice** — Define your content strategy so the AI knows what to look for
3. **Create** — Paste a URL or upload a video file, optionally enable subtitles
4. **Processing** — Watch progress in real-time with estimated time remaining
5. **Library** — Browse all past runs, play clips, edit drafts, and re-edit clips

### Voice Strategy

Tell SocialClipper what matters to you — your expertise, audience, and topics. Three ways to set it up:
- **Generate from LinkedIn** — paste your profile text and the AI builds your strategy
- **Paste your own** — drop in an existing brand voice doc
- **Use any AI** — copy a ready-made prompt into ChatGPT/Claude to generate one

### Clip Editing

The library includes a built-in editor where you can:
- Trim start/end times with a visual timeline
- Switch aspect ratios (16:9, 1:1, 9:16)
- Adjust crop position for aspect ratio conversions

### Draft Editing

Each clip comes with a publish-ready social post that you can:
- **Edit inline** — tweak the text directly in the library
- **Regenerate** — ask Claude for a completely fresh draft
- **Make Shorter** — condense the post by 30-50% with one click
- **Copy** — one-click copy to clipboard

### Subtitle Overlay

Enable "Burn subtitles onto clips" on the Create page to automatically add captions from the transcript directly onto the video — essential for social media engagement.

## Configuration

### Voice & Brand

Edit `src/socialclipper/config.py` to customize:

- **`VOICE_SYSTEM_PROMPT`** — The writing style and voice rules for draft generation
- **`ANALYSIS_SYSTEM_PROMPT`** — What Claude looks for when selecting clip moments
- **`BRAND_PILLARS`** — Your brand categories (default: Thought Leadership, Innovation, Authenticity)
- **`CONTENT_TYPES`** — Content categories (default: Authority, Story, Commentary, Connection)

Or use the **Voice Strategy** page in the UI to set these without touching code.

### Claude Model

The default model is `claude-sonnet-4-20250514`. Change `CLAUDE_MODEL` in `config.py` to use a different model.

### Platform Specs

Platform video specs (resolution, duration limits, draft length) are configured in `PLATFORM_SPECS` in `config.py`. Currently supports LinkedIn and Instagram Reels.

### Dark Mode

SocialClipper defaults to a dark theme. Click the sun/moon toggle in the header to switch. Your preference is saved in the browser.

## Project Structure

```
socialclipper/
├── src/socialclipper/
│   ├── app.py          # FastAPI server + API routes
│   ├── pipeline.py     # Main orchestration pipeline
│   ├── transcriber.py  # MLX Whisper transcription
│   ├── analyzer.py     # Claude transcript analysis
│   ├── drafter.py      # Claude draft generation
│   ├── clipper.py      # ffmpeg clip extraction + subtitle overlay
│   ├── output.py       # Output folder + markdown rendering
│   └── config.py       # All configuration (voice, platforms, prompts, API key)
├── static/             # Web UI (HTML, CSS, JS)
│   ├── welcome.html    # Home/landing page
│   ├── settings.html   # API key + cost breakdown
│   ├── voice.html      # Voice strategy setup
│   ├── index.html      # Create clips page
│   ├── processing.html # Real-time progress tracking
│   ├── library.html    # Clip library with editing
│   ├── style.css       # Creator Vibrant design system
│   └── theme.js        # Dark/light mode toggle
├── install.sh          # One-command setup
├── run.sh              # Start the server
└── pyproject.toml
```

## License

MIT
