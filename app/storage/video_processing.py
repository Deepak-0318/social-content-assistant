import json
import math
import shutil
import subprocess
from pathlib import Path

from app.storage.image_analysis import MediaProcessingError


MAX_VIDEO_SECONDS = 600
MAX_FRAMES = 12
MAX_FRAME_DIMENSION = 1024
COMMAND_TIMEOUT_SECONDS = 180


def _run_command(command: list[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaProcessingError(
            "Media processing exceeded its time limit."
        ) from exc
    except OSError as exc:
        raise MediaProcessingError(
            "FFmpeg tools are unavailable."
        ) from exc

    if result.returncode != 0:
        raise MediaProcessingError(
            "Media could not be processed. Check that the file is valid."
        )

    return result.stdout


def process_video(source: Path, output_dir: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    if not ffmpeg or not ffprobe:
        raise MediaProcessingError(
            "FFmpeg and FFprobe must be installed to process videos."
        )

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    probe_output = _run_command(
        [
            ffprobe,
            "-v", "error",
            "-show_entries",
            "format=duration,format_name:"
            "stream=codec_type,width,height,codec_name",
            "-of", "json",
            str(source),
        ]
    )

    try:
        metadata = json.loads(probe_output)
        duration = float(metadata["format"]["duration"])
        streams = metadata.get("streams", [])
    except (ValueError, KeyError, TypeError) as exc:
        raise MediaProcessingError(
            "Unable to read video metadata."
        ) from exc

    if not math.isfinite(duration) or duration <= 0:
        raise MediaProcessingError("Video duration is invalid.")

    if duration > MAX_VIDEO_SECONDS:
        raise MediaProcessingError(
            "Videos longer than 10 minutes are not supported yet."
        )

    video_streams = [
        stream for stream in streams
        if stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream for stream in streams
        if stream.get("codec_type") == "audio"
    ]

    if not video_streams:
        raise MediaProcessingError("No video stream was found.")

    video_stream = video_streams[0]
    width = video_stream.get("width")
    height = video_stream.get("height")

    if not width or not height or width * height > 40_000_000:
        raise MediaProcessingError(
            "Video dimensions are invalid or too large."
        )

    frame_count = min(MAX_FRAMES, max(1, math.ceil(duration / 5)))
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    frame_results = []

    # Sample inside the video duration, avoiding exact endpoints.
    for index in range(frame_count):
        timestamp = duration * (index + 1) / (frame_count + 1)
        frame_path = frame_dir / f"frame-{index + 1:02d}.jpg"

        _run_command(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-ss", f"{timestamp:.3f}",
                "-i", str(source),
                "-map", "0:v:0",
                "-frames:v", "1",
                "-vf",
                "scale=w='min(1024,iw)':h='min(1024,ih)':"
                "force_original_aspect_ratio=decrease",
                "-q:v", "4",
                str(frame_path),
            ],
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        if not frame_path.is_file() or frame_path.stat().st_size == 0:
            raise MediaProcessingError(
                "Failed to extract a video frame."
            )

        frame_results.append({
            "filename": frame_path.name,
            "timestamp_seconds": round(timestamp, 3),
        })

    audio_filename = None

    if audio_streams:
        audio_path = output_dir / "audio.wav"

        _run_command(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-i", str(source),
                "-map", "0:a:0",
                "-vn",
                "-t", str(MAX_VIDEO_SECONDS),
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                str(audio_path),
            ],
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            raise MediaProcessingError(
                "Failed to extract the audio stream."
            )

        audio_filename = audio_path.name

    return {
        "media_type": "video",
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "video_codec": video_stream.get("codec_name"),
        "audio_available": bool(audio_streams),
        "audio_filename": audio_filename,
        "frames": frame_results,
    }
