import os
import zipfile
import time

SCAN_INTERVAL = 10  # số giây giữa mỗi lần quét (có thể chỉnh)

def unzip_all_files_recursive(root_dir):
    for foldername, subfolders, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(".zip"):
                zip_path = os.path.join(foldername, filename)
                extract_dir = os.path.join(foldername, os.path.splitext(filename)[0])

                if not os.path.exists(extract_dir):
                    try:
                        os.makedirs(extract_dir)
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)

                        print(f"[OK] Giải nén: {zip_path}")
                        os.remove(zip_path)
                        print(f"[DEL] Đã xóa ZIP: {zip_path}")

                    except Exception as e:
                        print(f"[ERROR] {zip_path}: {e}")
                else:
                    print(f"[SKIP] Đã tồn tại: {extract_dir}")

if __name__ == "__main__":
    root_directory = os.getcwd()
    print(f"Đang theo dõi thư mục: {root_directory}")

    while True:
        unzip_all_files_recursive(root_directory)
        time.sleep(SCAN_INTERVAL)
