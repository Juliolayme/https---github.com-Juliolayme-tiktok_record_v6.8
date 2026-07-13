import os
import subprocess

# --- Cấu hình ---
CHUNK_DURATION = 300  # thời lượng mỗi đoạn (giây)
OUTPUT_DIR = "output_ffmpeg"

def run_ffmpeg(cmd):
    """Chạy lệnh FFmpeg và in log lỗi nếu có."""
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg lỗi:")
        print(e.stderr.decode())
        raise

def split_video_ffmpeg(video_path, output_dir, chunk_duration=CHUNK_DURATION):
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🎬 Đang xử lý video: {video_name}")

    # Lấy độ dài video
    cmd_get_length = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    duration = float(subprocess.check_output(cmd_get_length))

    print(f"⏱  Tổng thời gian video: {duration:.2f} giây")

    # Tính số đoạn
    total_parts = int(duration // chunk_duration) + 1

    for part in range(total_parts):
        start_time = part * chunk_duration
        out_file = os.path.join(output_dir, f"{video_name}_part{part+1:02d}.mp4")

        print(f"  ➜ Cắt đoạn {part+1}/{total_parts}: từ {start_time}s → {start_time + chunk_duration}s")

        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(chunk_duration),
            "-c:v", "copy",        # giữ nguyên video
            "-c:a", "copy",        # giữ nguyên âm thanh
            out_file,
            "-y"
        ]

        run_ffmpeg(cmd)
        print(f"  ✅ Đã lưu: {out_file}")

    print(f"🎉 Hoàn tất video: {video_name}\n")


def process_videos_in_current_dir(output_dir=OUTPUT_DIR):
    print("🔍 Đang tìm video trong thư mục hiện tại...\n")
    current_dir = os.getcwd()

    for file in os.listdir(current_dir):
        if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')):
            split_video_ffmpeg(os.path.join(current_dir, file), output_dir)


if __name__ == "__main__":
    process_videos_in_current_dir()
