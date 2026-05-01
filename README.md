# Codex Video Short Maker Skill

A Codex skill for turning local videos into short clips with optional local captions.

Give Codex a local video and it can remove dead air, cut pauses, export a vertical short, generate local Whisper subtitles, and burn captions into the final MP4.

## What It Does

- Turns local videos into 30-60s shorts
- Removes dead air and boring pauses
- Supports `light`, `normal`, and `aggressive` cut styles
- Exports vertical 9:16 MP4 for Shorts/Reels/TikTok
- Exports high quality H.264 MP4
- Optionally generates local captions with `whisper.cpp`
- No OpenAI API key required

## Installation

Base install:

```bash
npx --yes codex-video-short-maker-skill@latest
```

Full install with local captions:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions
```

This installs the skill into:

```bash
~/.codex/skills/video-short-maker
```

Then restart Codex so it can discover the skill.

## Captions Setup

Captions are optional. If you install with:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions
```

the installer will:

- copy the skill into Codex
- install `whisper.cpp` with Homebrew if missing
- install Pillow if missing
- download the default local Whisper model `tiny.en`

For multilingual captions, install a multilingual model:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions --caption-model base
```

## Usage

After installation, restart Codex and run:

```text
Use $video-short-maker to create a 30s vertical high quality short with English captions from /Users/me/Desktop/demo.mp4 using aggressive cut style.
```

Without captions:

```text
Use $video-short-maker to create a 45s vertical short from /Users/me/Desktop/demo.mp4.
```

Italian captions:

```text
Use $video-short-maker to create a 30s vertical high quality short with Italian captions from /Users/me/Desktop/demo.mp4.
```

## Output

The skill creates files next to the input video:

```text
demo.vertical.short.mp4
demo.vertical.short.srt
demo.vertical.short.captioned.mp4
demo.vertical.short.report.json
```

## Cut Styles

- `light`: softer cuts, preserves more pauses
- `normal`: balanced default
- `aggressive`: removes more pauses and dead air

## Manual Installation

Clone the repository:

```bash
git clone https://github.com/Kappaemme-git/codex-video-short-maker-skill.git
```

Copy the skill into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R codex-video-short-maker-skill/video-short-maker ~/.codex/skills/video-short-maker
```

Restart Codex.

## Requirements

- `ffmpeg` and `ffprobe`
- macOS + Homebrew for automatic local captions setup
- `whisper.cpp` for captions
- Pillow for burned-in captions

Base video cutting only requires `ffmpeg`.

## License

MIT
