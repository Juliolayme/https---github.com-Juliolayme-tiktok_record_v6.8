import os
import subprocess
import shutil

SEGMENT_DURATION = 120  # 2 phút
OUTPUT_DIR = "output"


def check_ffmpeg():
    return shutil.which("ffmpeg") is not None


def install_ffmpeg():
    print("Đang cài FFmpeg...")

    try:
        subprocess.run(
            ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
            check=True
        )
        return True
    except:
        pass

    try:
        subprocess.run(
            ["choco", "install", "ffmpeg", "-y"],
            check=True
        )
        return True
    except:
        pass

    print("Không cài được FFmpeg tự động.")
    return False


def split_video(file):
    filename = os.path.splitext(file)[0]

    cmd = [
        "ffmpeg",
        "-i", file,
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(SEGMENT_DURATION),
        "-reset_timestamps", "1",
        os.path.join(OUTPUT_DIR, f"{filename}_part_%03d.mp4")
    ]

    subprocess.run(cmd)


def main():
    if not check_ffmpeg():
        if not install_ffmpeg():
            return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [f for f in os.listdir() if f.endswith(".mp4")]

    if not files:
        print("Không có file mp4 nào.")
        return

    for f in files:
        print(f"Đang xử lý: {f}")
        split_video(f)

    print(f"Hoàn tất! File nằm trong thư mục '{OUTPUT_DIR}'")


if __name__ == "__main__":
    main()
