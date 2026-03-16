import os
import sys
import subprocess
import zipfile
import time

# --- CẤU HÌNH ---
SCAN_INTERVAL = 10 

def run_cmd(command):
    """Chạy lệnh hệ thống"""
    return subprocess.run(command, shell=True, capture_output=True, text=True)

def install_tools():
    """Tự động cài FFmpeg qua Choco nếu chưa có"""
    print("--- [1] KIỂM TRA HỆ THỐNG ---")
    if run_cmd("ffmpeg -version").returncode == 0:
        print("[OK] FFmpeg đã sẵn sàng.")
        return

    print("[!] Không tìm thấy FFmpeg. Đang kiểm tra Chocolatey...")
    if run_cmd("choco -v").returncode != 0:
        print("[*] Đang cài đặt Chocolatey...")
        install_choco = (
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            "\"iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))\""
        )
        run_cmd(install_choco)
        # Cập nhật môi trường tạm thời để dùng choco ngay
        os.environ["PATH"] += os.pathsep + os.path.join(os.environ["ALLUSERSPROFILE"], 'chocolatey', 'bin')

    print("[*] Đang cài đặt FFmpeg qua Choco (Vui lòng đợi)...")
    run_cmd("choco install ffmpeg --yes")
    print("[OK] Cài đặt hoàn tất. Nếu lệnh 'ffmpeg' lỗi, hãy chạy lại CMD bằng quyền Admin.")

def fix_audio_copyright(file_path):
    """Lách bản quyền âm thanh bằng FFmpeg"""
    temp_output = file_path + "_fixed.mp4"
    print(f"    [FFMPEG] Đang xử lý: {os.path.basename(file_path)}")
    
    # Công thức lách: Đổi pitch 3% và giữ nguyên tốc độ video
    cmd = f'ffmpeg -y -i "{file_path}" -af "asetrate=44100*1.03,aresample=44100,atempo=1.0/1.03" -vcodec copy "{temp_output}"'
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True)
        if res.returncode == 0:
            os.replace(temp_output, file_path)
            print(f"    [DONE] Đã fix xong: {os.path.basename(file_path)}")
        else:
            print(f"    [ERROR] FFmpeg lỗi: {res.stderr}")
    except Exception as e:
        print(f"    [CRITICAL] Lỗi hệ thống: {e}")

def scan_and_process():
    """Quét thư mục A và tất cả thư mục con (B, C...)"""
    root_dir = os.getcwd()
    print(f"\n--- [2] ĐANG THEO DÕI TOÀN BỘ THƯ MỤC: {root_dir} ---")

    while True:
        # os.walk sẽ đi sâu vào mọi thư mục con (như thư mục B của bạn)
        for foldername, subfolders, filenames in os.walk(root_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)

                # 1. Phát hiện file ZIP
                if filename.lower().endswith(".zip"):
                    # Không giải nén các file zip của hệ thống/ffmpeg nếu lỡ tay để vào
                    if "ffmpeg" in filename.lower(): continue

                    extract_dir = os.path.join(foldername, os.path.splitext(filename)[0])
                    print(f"\n[PHÁT HIỆN ZIP] Tại: {foldername}")
                    
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        print(f"  -> Giải nén thành công vào: {os.path.basename(extract_dir)}")

                        # 2. Quét MP4 bên trong thư mục vừa giải nén
                        for sub_root, _, sub_files in os.walk(extract_dir):
                            for f in sub_files:
                                if f.lower().endswith(".mp4"):
                                    fix_audio_copyright(os.path.join(sub_root, f))
                        
                        # 3. Xóa file ZIP sau khi xử lý xong
                        os.remove(file_path)
                        print(f"[OK] Đã xóa file ZIP gốc: {filename}")
                    except Exception as e:
                        print(f"[LOI] Không thể xử lý file ZIP {filename}: {e}")

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    # Nhắc nhở chạy quyền Admin
    print("LƯU Ý: Vui lòng chạy CMD/PowerShell bằng quyền ADMINISTRATOR.")
    install_tools()
    try:
        scan_and_process()
    except KeyboardInterrupt:
        print("\n--- ĐÃ DỪNG TOOL ---")
