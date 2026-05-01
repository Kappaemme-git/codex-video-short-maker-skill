#!/usr/bin/env python3
import argparse
import bisect
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, *, capture=False):
    kwargs = {
        "text": True,
        "check": False,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    result = subprocess.run(command, **kwargs)
    if result.returncode != 0:
        if capture:
            sys.stderr.write(result.stdout or "")
            sys.stderr.write(result.stderr or "")
        raise SystemExit(f"Command failed: {' '.join(command)}")
    return result


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(
            f"{name} is required. Install ffmpeg first, for example: brew install ffmpeg"
        )


def probe_duration(path):
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture=True,
    )
    return float(result.stdout.strip())


def probe_video_info(path):
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    fps_value = stream["r_frame_rate"]
    numerator, denominator = [int(part) for part in fps_value.split("/")]
    fps = numerator / denominator if denominator else numerator
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": fps,
    }


def detect_silences(path, threshold, min_silence):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={threshold}:d={min_silence}",
            "-f",
            "null",
            "-",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    log = (result.stdout or "") + "\n" + (result.stderr or "")
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", log)]

    silences = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else None
        silences.append({"start": start, "end": end})
    return silences, log


def non_silent_segments(duration, silences, keep_silence):
    segments = []
    cursor = 0.0

    for silence in silences:
        silence_start = max(0.0, silence["start"])
        silence_end = silence["end"]
        if silence_end is None:
            silence_end = duration
        silence_end = min(duration, silence_end)

        # Keep a handle on both sides of each pause so speech cuts do not feel abrupt.
        midpoint = (silence_start + silence_end) / 2
        cut_start = min(silence_start + keep_silence, midpoint)
        cut_end = max(silence_end - keep_silence, midpoint)

        if cut_end <= cut_start:
            continue

        if cut_start > cursor:
            segments.append({"start": cursor, "end": cut_start})
        cursor = max(cursor, cut_end)

    if cursor < duration:
        segments.append({"start": cursor, "end": duration})

    return segments


def select_segments(segments, target_duration, min_segment):
    selected = []
    total = 0.0

    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        length = end - start
        if length < min_segment:
            continue

        remaining = target_duration - total
        if remaining <= 0:
            break

        if length > remaining:
            end = start + remaining
            length = remaining

        selected.append({"start": round(start, 3), "end": round(end, 3)})
        total += length

    return selected


QUALITY_PRESETS = {
    "high": {"crf": "18", "preset": "slow", "audio_bitrate": "192k"},
    "balanced": {"crf": "20", "preset": "veryfast", "audio_bitrate": "160k"},
    "small": {"crf": "24", "preset": "veryfast", "audio_bitrate": "128k"},
}

CUT_STYLE_PRESETS = {
    "light": {
        "silence_threshold": "-40dB",
        "min_silence": 0.9,
        "keep_silence": 0.7,
    },
    "normal": {
        "silence_threshold": "-35dB",
        "min_silence": 0.6,
        "keep_silence": 0.5,
    },
    "aggressive": {
        "silence_threshold": "-30dB",
        "min_silence": 0.3,
        "keep_silence": 0.2,
    },
}

DEFAULT_MODEL_PATH = (
    Path.home() / ".cache" / "video-short-maker" / "models" / "ggml-tiny.en.bin"
)


def render_output(input_path, segments, output_path, vertical, quality):
    quality_options = QUALITY_PRESETS[quality]
    filters = []
    concat_inputs = []

    for index, segment in enumerate(segments):
        start = segment["start"]
        end = segment["end"]
        filters.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]"
        )
        concat_inputs.append(f"[v{index}][a{index}]")

    filters.append(
        f"{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[vcat][acat]"
    )

    if vertical:
        filters.append(
            "[vcat]split=2[vbg][vfg]"
        )
        filters.append(
            "[vbg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=32,eq=brightness=-0.08:saturation=1.12[bg]"
        )
        filters.append(
            "[vfg]scale=1080:1920:force_original_aspect_ratio=decrease[fg]"
        )
        filters.append(
            "[bg][fg]overlay=(W-w)/2:(H-h)*0.34,format=yuv420p[vout]"
        )
    else:
        filters.append("[vcat]format=yuv420p[vout]")

    filter_complex = ";".join(filters)

    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[acat]",
            "-c:v",
            "libx264",
            "-preset",
            quality_options["preset"],
            "-crf",
            quality_options["crf"],
            "-c:a",
            "aac",
            "-b:a",
            quality_options["audio_bitrate"],
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def extract_audio(video_path, audio_path):
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ]
    )


def run_whisper(audio_path, srt_path, model_path, language):
    whisper_cli = shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    if whisper_cli is None:
        raise SystemExit(
            "whisper.cpp is required for captions. Run: "
            "python3 /Users/francescomistero/.codex/skills/video-short-maker/scripts/setup_captions.py"
        )

    if not model_path.exists():
        raise SystemExit(
            f"Whisper model not found: {model_path}\n"
            "Run: python3 /Users/francescomistero/.codex/skills/video-short-maker/scripts/setup_captions.py"
        )

    with tempfile.TemporaryDirectory(prefix="video-short-maker-captions-") as temp:
        output_base = Path(temp) / "captions"
        command = [
            whisper_cli,
            "-m",
            str(model_path),
            "-f",
            str(audio_path),
            "-osrt",
            "-of",
            str(output_base),
        ]
        if language:
            command.extend(["-l", language])
        run(command)

        generated = output_base.with_suffix(".srt")
        if not generated.exists():
            raise SystemExit("Whisper did not generate an SRT file.")
        shutil.copyfile(generated, srt_path)


def escape_subtitle_path(path):
    value = str(path)
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "\\'")
    value = value.replace(":", "\\:")
    return value


def parse_srt_timestamp(value):
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def parse_srt(srt_path):
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())
    captions = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        time_line = lines[1]
        match = re.match(
            r"(\d\d:\d\d:\d\d,\d\d\d)\s+-->\s+(\d\d:\d\d:\d\d,\d\d\d)",
            time_line,
        )
        if not match:
            continue
        captions.append(
            {
                "start": parse_srt_timestamp(match.group(1)),
                "end": parse_srt_timestamp(match.group(2)),
                "text": " ".join(lines[2:]),
            }
        )

    return captions


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def load_caption_font(size):
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def burn_captions(video_path, srt_path, output_path, quality):
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise SystemExit(
            "Pillow is required to burn captions. Install it with: "
            "python3 -m pip install --user Pillow"
        ) from error

    quality_options = QUALITY_PRESETS[quality]
    info = probe_video_info(video_path)
    width = info["width"]
    height = info["height"]
    fps = info["fps"]
    frame_size = width * height * 3
    captions = parse_srt(srt_path)
    starts = [caption["start"] for caption in captions]
    font = load_caption_font(max(24, int(height * 0.035)))

    decoder = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            f"{fps}",
            "-i",
            "-",
            "-i",
            str(video_path),
            "-map",
            "0:v",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            quality_options["preset"],
            "-crf",
            quality_options["crf"],
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        stdin=subprocess.PIPE,
    )

    frame_index = 0
    try:
        while True:
            raw_frame = decoder.stdout.read(frame_size)
            if len(raw_frame) < frame_size:
                break

            timestamp = frame_index / fps
            image = Image.frombytes("RGB", (width, height), raw_frame)
            draw = ImageDraw.Draw(image, "RGBA")

            caption_text = None
            caption_index = bisect.bisect_right(starts, timestamp) - 1
            if caption_index >= 0:
                caption = captions[caption_index]
                if caption["start"] <= timestamp <= caption["end"]:
                    caption_text = caption["text"]

            if caption_text:
                max_width = int(width * 0.82)
                lines = wrap_text(draw, caption_text, font, max_width)
                line_height = int(font.size * 1.25)
                text_height = line_height * len(lines)
                margin_x = int(width * 0.06)
                padding_x = int(width * 0.025)
                padding_y = int(height * 0.018)
                box_width = min(max_width + padding_x * 2, width - margin_x * 2)
                box_height = text_height + padding_y * 2
                x0 = (width - box_width) // 2
                y0 = height - box_height - int(height * 0.075)
                x1 = x0 + box_width
                y1 = y0 + box_height

                draw.rounded_rectangle(
                    (x0, y0, x1, y1),
                    radius=int(height * 0.012),
                    fill=(0, 0, 0, 180),
                )

                y = y0 + padding_y
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    x = (width - line_width) // 2
                    draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                    y += line_height

            encoder.stdin.write(image.tobytes())
            frame_index += 1
    finally:
        if decoder.stdout:
            decoder.stdout.close()
        if encoder.stdin:
            encoder.stdin.close()
        decoder_return = decoder.wait()
        encoder_return = encoder.wait()

    if decoder_return != 0:
        raise SystemExit("Failed to decode video frames for captions.")
    if encoder_return != 0:
        raise SystemExit("Failed to encode captioned video.")


def default_output_path(input_path, vertical):
    suffix = ".vertical.short.mp4" if vertical else ".short.mp4"
    return input_path.with_name(f"{input_path.stem}{suffix}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a short video by removing silence with ffmpeg."
    )
    parser.add_argument("input", help="Input video path")
    parser.add_argument("--output", help="Output MP4 path")
    parser.add_argument("--duration", type=float, default=45.0, help="Target seconds")
    parser.add_argument("--vertical", action="store_true", help="Export 9:16 MP4")
    parser.add_argument(
        "--quality",
        choices=sorted(QUALITY_PRESETS.keys()),
        default="high",
        help="Export quality preset: high, balanced, or small",
    )
    parser.add_argument(
        "--captions",
        action="store_true",
        help="Generate local Whisper subtitles and burn them into a captioned MP4",
    )
    parser.add_argument(
        "--caption-model",
        default=str(DEFAULT_MODEL_PATH),
        help="Path to whisper.cpp ggml model file",
    )
    parser.add_argument(
        "--caption-language",
        default="en",
        help="Whisper language code, e.g. en, it, auto. Use auto to let Whisper detect.",
    )
    parser.add_argument(
        "--cut-style",
        choices=sorted(CUT_STYLE_PRESETS.keys()),
        default="normal",
        help="Cut aggressiveness preset: light, normal, or aggressive",
    )
    parser.add_argument(
        "--silence-threshold",
        default=None,
        help="ffmpeg silencedetect threshold, e.g. -35dB",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=None,
        help="Minimum silence duration to cut, in seconds",
    )
    parser.add_argument(
        "--keep-silence",
        type=float,
        default=None,
        help="Seconds of silence to keep on each side of a cut",
    )
    parser.add_argument(
        "--min-segment",
        type=float,
        default=0.45,
        help="Drop non-silent fragments shorter than this many seconds",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    require_tool("ffmpeg")
    require_tool("ffprobe")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input video not found: {input_path}")

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else default_output_path(input_path, args.vertical)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cut_style = CUT_STYLE_PRESETS[args.cut_style]
    silence_threshold = args.silence_threshold or cut_style["silence_threshold"]
    min_silence = args.min_silence
    if min_silence is None:
        min_silence = cut_style["min_silence"]
    keep_silence = args.keep_silence
    if keep_silence is None:
        keep_silence = cut_style["keep_silence"]

    duration = probe_duration(input_path)
    silences, _ = detect_silences(input_path, silence_threshold, min_silence)
    candidates = non_silent_segments(duration, silences, keep_silence)
    selected = select_segments(candidates, args.duration, args.min_segment)

    if not selected:
        raise SystemExit("No usable non-silent segments found.")

    render_output(input_path, selected, output_path, args.vertical, args.quality)

    srt_path = None
    captioned_path = None
    if args.captions:
        caption_model = Path(args.caption_model).expanduser().resolve()
        caption_language = None if args.caption_language == "auto" else args.caption_language
        srt_path = output_path.with_suffix(".srt")
        captioned_path = output_path.with_name(f"{output_path.stem}.captioned.mp4")
        with tempfile.TemporaryDirectory(prefix="video-short-maker-audio-") as temp:
            audio_path = Path(temp) / "audio.wav"
            extract_audio(output_path, audio_path)
            run_whisper(audio_path, srt_path, caption_model, caption_language)
        burn_captions(output_path, srt_path, captioned_path, args.quality)

    selected_duration = sum(segment["end"] - segment["start"] for segment in selected)
    report_path = output_path.with_suffix(".report.json")
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "source_duration": round(duration, 3),
        "target_duration": args.duration,
        "selected_duration": round(selected_duration, 3),
        "vertical": args.vertical,
        "quality": args.quality,
        "quality_options": QUALITY_PRESETS[args.quality],
        "captions": args.captions,
        "srt": str(srt_path) if srt_path else None,
        "captioned_output": str(captioned_path) if captioned_path else None,
        "cut_style": args.cut_style,
        "silence_threshold": silence_threshold,
        "min_silence": min_silence,
        "keep_silence": keep_silence,
        "segments": selected,
        "silences_detected": len(silences),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Created short: {output_path}")
    print(f"Report: {report_path}")
    print(f"Source duration: {duration:.1f}s")
    print(f"Selected duration: {selected_duration:.1f}s")
    print(f"Segments kept: {len(selected)}")
    print(f"Vertical: {'yes' if args.vertical else 'no'}")
    print(f"Quality: {args.quality}")
    print(f"Cut style: {args.cut_style}")
    if srt_path and captioned_path:
        print(f"Subtitles: {srt_path}")
        print(f"Captioned video: {captioned_path}")


if __name__ == "__main__":
    main()
