#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


MODELS = {
    "tiny.en": {
        "file": "ggml-tiny.en.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    },
    "base.en": {
        "file": "ggml-base.en.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
    },
    "tiny": {
        "file": "ggml-tiny.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    },
    "base": {
        "file": "ggml-base.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    },
}


def run(command):
    result = subprocess.run(command, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(command)}")


def ensure_pillow():
    try:
        import PIL  # noqa: F401
        return
    except ImportError:
        pass

    print("Installing Pillow for burned-in captions...")
    run([sys.executable, "-m", "pip", "install", "--user", "Pillow"])


def install_whisper_cpp():
    if shutil.which("whisper-cli") or shutil.which("whisper-cpp"):
        return

    if shutil.which("brew") is None:
        raise SystemExit(
            "Homebrew is required to install whisper.cpp automatically.\n"
            "Install Homebrew or install whisper.cpp manually."
        )

    print("Installing whisper.cpp with Homebrew...")
    run(["brew", "install", "whisper-cpp"])


def download_model(model_name, models_dir):
    model = MODELS[model_name]
    models_dir.mkdir(parents=True, exist_ok=True)
    destination = models_dir / model["file"]

    if destination.exists():
        print(f"Model already exists: {destination}")
        return destination

    print(f"Downloading Whisper model {model_name}...")
    print(f"Destination: {destination}")
    urllib.request.urlretrieve(model["url"], destination)
    return destination


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install local whisper.cpp captions support for video-short-maker."
    )
    parser.add_argument(
        "--model",
        choices=sorted(MODELS.keys()),
        default="tiny.en",
        help="Whisper model to download",
    )
    parser.add_argument(
        "--models-dir",
        default=str(Path.home() / ".cache" / "video-short-maker" / "models"),
        help="Directory for Whisper model files",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    install_whisper_cpp()
    ensure_pillow()
    model_path = download_model(args.model, Path(args.models_dir).expanduser())

    print("")
    print("Captions setup complete.")
    print(f"Whisper CLI: {shutil.which('whisper-cli') or shutil.which('whisper-cpp')}")
    print(f"Model: {model_path}")
    print("")
    print("Try:")
    print(
        "python3 /Users/francescomistero/.codex/skills/video-short-maker/scripts/"
        "make_short.py INPUT_VIDEO --duration 30 --vertical --captions"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
