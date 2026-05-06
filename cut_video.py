import os
import subprocess
import shutil
from pathlib import Path

SEGMENT_DURATION = 120  # 2 phút
OUTPUT_DIR = "output"


def get_ffmpeg():
    # Tìm trong PATH trước
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    print("Đang cài FFmpeg...")

    # Cài bằng winget
    try:
        subprocess.run(
            ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
            check=True
        )
    except:
        pass

    # Kiểm tra lại PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    # Tìm thủ công các vị trí phổ biến
    possible_paths = [
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]

    # Tìm trong AppData winget
    local_app = os.environ.get("LOCALAPPDATA", "")
    winget_path = Path(local_app) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"

    possible_paths.append(str(winget_path))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def split_video(ffmpeg_path, file):
    filename = os.path.splitext(file)[0]

    # Mỗi video 1 folder riêng
    video_output_dir = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(video_output_dir, exist_ok=True)

    output_pattern = os.path.join(
        video_output_dir,
        f"{filename}_part_%03d.mp4"
    )

    cmd = [
        ffmpeg_path,
        "-i", file,
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(SEGMENT_DURATION),
        "-reset_timestamps", "1",
        output_pattern
    ]

    subprocess.run(cmd, check=True)


def main():
    ffmpeg_path = get_ffmpeg()

    if not ffmpeg_path:
        print("Không tìm thấy FFmpeg.")
        return

    print("FFmpeg:", ffmpeg_path)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [f for f in os.listdir() if f.lower().endswith(".mp4")]

    if not files:
        print("Không có file mp4 nào.")
        return

    for f in files:
        print(f"Đang xử lý: {f}")

        try:
            split_video(ffmpeg_path, f)
            print(f"Hoàn tất: {f}")
        except Exception as e:
            print(f"Lỗi khi xử lý {f}: {e}")

    print(f"\nXong toàn bộ! File nằm trong thư mục '{OUTPUT_DIR}'")


if __name__ == "__main__":
    main()
