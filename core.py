import os
import sys
import subprocess
import shutil
import time
from config import MODEL_NAME, SAMPLE_RATE


# ---------------- BASE DIR ---------------- #

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)


# ---------------- Extract Audio ---------------- #

def extract_audio(input_path, tmp_wav):

    ffmpeg_path = os.path.join(BASE_DIR, "ffmpeg.exe")

    cmd = [
        ffmpeg_path, "-y",
        "-i", input_path,
        "-ac", "2",
        "-ar", str(SAMPLE_RATE),
        tmp_wav
    ]

    process = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if process.returncode != 0:
        raise RuntimeError("FFmpeg failed while extracting audio.")


# ---------------- Run Demucs ---------------- #

def run_demucs(audio_path, out_dir,
               progress_callback=None,
               cancel_check=None):

    cmd = [
        sys.executable, "-m", "demucs",
        "-n", MODEL_NAME,
        "--two-stems", "vocals",
        "-o", out_dir,
        audio_path
    ]

    process = subprocess.Popen(cmd)

    while process.poll() is None:

        if cancel_check and cancel_check():
            process.terminate()
            process.wait()
            raise RuntimeError("Processing cancelled")

        time.sleep(0.1)

    if process.returncode != 0:
        raise RuntimeError("Demucs failed during separation.")

    if progress_callback:
        progress_callback(100)


# ---------------- Main Pipeline ---------------- #

def process_input(input_path,
                  output_dir,
                  progress_callback=None,
                  cancel_check=None):

    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(
        os.path.basename(input_path)
    )[0]

    workdir = os.path.join(output_dir, "_tmp")
    os.makedirs(workdir, exist_ok=True)

    tmp_audio = os.path.join(workdir, "input.wav")

    try:

        extract_audio(input_path, tmp_audio)

        run_demucs(
            tmp_audio,
            workdir,
            progress_callback,
            cancel_check
        )

        stem_dir = os.path.join(workdir, MODEL_NAME, "input")

        vocals_src = os.path.join(stem_dir, "vocals.wav")
        instrumental_src = os.path.join(stem_dir, "no_vocals.wav")

        if not os.path.exists(vocals_src) or not os.path.exists(instrumental_src):
            raise RuntimeError("Separated files not found.")

        vocals_dst = os.path.join(
            output_dir,
            f"{base_name}_vocals.wav"
        )

        instrumental_dst = os.path.join(
            output_dir,
            f"{base_name}_instrumental.wav"
        )

        shutil.copy(vocals_src, vocals_dst)
        shutil.copy(instrumental_src, instrumental_dst)

        return instrumental_dst

    finally:
        shutil.rmtree(workdir, ignore_errors=True)