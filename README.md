# Codex Video Short Maker Skill

A Codex skill for turning local videos into short clips with local captions.

Give Codex a local video and it can remove dead air, cut pauses, export a vertical short, generate local Whisper subtitles, and burn captions into the final MP4. No OpenAI API key required.

## What It Does

- Turns local videos into 30-60s shorts
- Removes dead air and boring pauses
- Supports `light`, `normal`, and `aggressive` cut styles
- Exports vertical 9:16 MP4 for Shorts/Reels/TikTok
- Exports high quality H.264 MP4
- Optionally generates local captions with `whisper.cpp`
- No OpenAI API key required

## Installation

Recommended install with local captions:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions
```

This installs:

- the Codex skill
- `whisper.cpp` for local transcription, if missing
- Pillow for burned-in captions, if missing
- the default local Whisper model `tiny.en`

Base install without captions:

```bash
npx --yes codex-video-short-maker-skill@latest
```

This installs the skill into:

```bash
~/.codex/skills/video-short-maker
```

Then restart Codex so it can discover the skill.

## Captions Setup

English captions work with the default install:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions
```

For Italian or other languages, install the multilingual model:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions --caption-model base
```

This downloads `ggml-base.bin`, which supports language codes such as `it`, `en`, and `auto`.

## Usage

After installation, restart Codex and run:

```text
Use $video-short-maker to create a 30s vertical high quality short with English captions from /Users/me/Desktop/demo.mp4 using aggressive cut style.
```

Italian captions:

```text
Use $video-short-maker to create a 30s vertical high quality short with Italian captions from /Users/me/Desktop/demo.mp4 using aggressive cut style.
```

Without captions:

```text
Use $video-short-maker to create a 45s vertical short from /Users/me/Desktop/demo.mp4.
```

Softer cuts:

```text
Use $video-short-maker to create a 30s vertical short from /Users/me/Desktop/demo.mp4 using light cut style.
```

More aggressive cuts:

```text
Use $video-short-maker to create a 30s vertical short from /Users/me/Desktop/demo.mp4 using aggressive cut style.
```

## Output Formats

Vertical 9:16 for Shorts/Reels/TikTok:

```text
Use $video-short-maker to create a 30s vertical short from /Users/me/Desktop/demo.mp4.
```

Original aspect ratio:

```text
Use $video-short-maker to create a 30s short from /Users/me/Desktop/demo.mp4.
```

## Output

The skill creates files next to the input video:

```text
demo.vertical.short.mp4
demo.vertical.short.srt
demo.vertical.short.captioned.mp4
demo.vertical.short.report.json
```

- `*.short.mp4`: edited short
- `*.srt`: generated subtitles, when captions are used
- `*.captioned.mp4`: final video with burned-in captions
- `*.report.json`: edit report with selected segments and settings

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

- `ffmpeg` and `ffprobe` for base video cutting
- macOS + Homebrew for automatic captions setup
- `whisper.cpp` for local captions
- Pillow for burned-in captions

Base video cutting only requires `ffmpeg`.

If captions setup fails, install dependencies manually:

```bash
brew install ffmpeg whisper-cpp
python3 -m pip install --user Pillow
```

Then reinstall:

```bash
npx --yes codex-video-short-maker-skill@latest --with-captions
```

## Troubleshooting

If Codex does not recognize `$video-short-maker`, restart Codex after installing.

Check that the skill exists:

```bash
ls ~/.codex/skills/video-short-maker
```

You should see:

```text
SKILL.md
agents/
scripts/
```

## License

MIT
