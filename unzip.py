import os
import sys
import subprocess
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH ---
SCAN_INTERVAL = 10 
MAX_WORKERS = 4  # Số luồng chạy song song (Nên để bằng số nhân CPU hoặc 4-8 luồng)

def run_cmd(command):
    """Chạy lệnh hệ thống"""
    return subprocess.run(command, shell=True, capture_output=True, text=True)

def install_tools():
    """Kiểm tra và cài đặt FFmpeg qua Choco"""
    print("--- [1] KIỂM TRA HỆ THỐNG ---")
    if run_cmd("ffmpeg -version").returncode == 0:
        print("[OK] FFmpeg đã sẵn sàng.")
        return

    print("[!] Không tìm thấy FFmpeg. Đang tiến hành cài đặt...")
    # Kiểm tra Choco
    if run_cmd("choco -v").returncode != 0:
        print("[*] Đang cài đặt Chocolatey...")
        install_choco = ("powershell -NoProfile -ExecutionPolicy Bypass -Command "
                         "\"iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))\"")
        run_cmd(install_choco)
        os.environ["PATH"] += os.pathsep + os.path.join(os.environ["ALLUSERSPROFILE"], 'chocolatey', 'bin')

    print("[*] Đang cài đặt FFmpeg qua Choco...")
    run_cmd("choco install ffmpeg --yes")
    print("[OK] Cài đặt xong. Nếu lỗi lệnh 'ffmpeg', hãy khởi động lại CMD Admin.")

def fix_audio_copyright(file_path):
    """Hàm xử lý lách bản quyền cho 1 file duy nhất"""
    temp_output = file_path + "_fixed.mp4"
    base_name = os.path.basename(file_path)
    
    print(f"    [XỬ LÝ] Đang bắt đầu: {base_name}")
    
    # Công thức lách âm thanh
    cmd = f'ffmpeg -y -i "{file_path}" -af "asetrate=44100*1.03,aresample=44100,atempo=1.0/1.03" -vcodec copy "{temp_output}"'
    
    try:
        # Sử dụng subprocess.run không capture_output để tránh tốn RAM khi chạy đa luồng
        res = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if res.returncode == 0:
            os.replace(temp_output, file_path)
            print(f"    [DONE] Thành công: {base_name}")
        else:
            print(f"    [ERROR] Thất bại: {base_name}")
    except Exception as e:
        print(f"    [CRITICAL] Lỗi file {base_name}: {e}")

def process_zip(zip_path, foldername):
    """Giải nén và đưa các video vào hàng chờ xử lý song song"""
    extract_dir = os.path.join(foldername, os.path.splitext(os.path.basename(zip_path))[0])
    print(f"\n[PHÁT HIỆN ZIP] {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"  -> Đã giải nén xong: {os.path.basename(extract_dir)}")
        
        # Tìm danh sách video sau khi giải nén
        video_files = []
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.lower().endswith(".mp4"):
                    video_files.append(os.path.join(root, f))
        
        # Chạy đa luồng cho danh sách video vừa tìm thấy
        if video_files:
            print(f"  -> Đang xử lý song song {len(video_files)} video...")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                executor.map(fix_audio_copyright, video_files)
        
        # Xóa ZIP sau khi tất cả luồng xử lý video bên trong hoàn tất
        os.remove(zip_path)
        print(f"[OK] Hoàn tất toàn bộ ZIP và đã xóa file gốc: {os.path.basename(zip_path)}")
        
    except Exception as e:
        print(f"[LỖI ZIP] {zip_path}: {e}")

def main():
    install_tools()
    root_dir = os.getcwd()
    print(f"\n--- [2] ĐANG QUÉT ĐA LUỒNG TẠI: {root_dir} ---")
    print(f"Số luồng xử lý cùng lúc: {MAX_WORKERS}")

    while True:
        # Duyệt thư mục A và tất cả thư mục con (B, C...)
        for foldername, subfolders, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.lower().endswith(".zip"):
                    # Không đụng vào zip cài đặt
                    if "ffmpeg" in filename.lower(): continue
                    
                    zip_path = os.path.join(foldername, filename)
                    process_zip(zip_path, foldername)

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n--- ĐÃ DỪNG TOOL ---")
