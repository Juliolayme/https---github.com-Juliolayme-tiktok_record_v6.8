import os
import shutil

# Thư mục hiện tại (chỗ bạn đang đứng khi chạy lệnh)
destination = os.getcwd()

# Duyệt tất cả thư mục con
for root, dirs, files in os.walk(destination):
    for file in files:
        if file.lower().endswith(".mp4"):
            src = os.path.join(root, file)
            dst = os.path.join(destination, file)

            # Bỏ qua nếu file đã ở thư mục hiện tại
            if os.path.abspath(root) == os.path.abspath(destination):
                continue

            # Nếu trùng tên thì tự đổi tên
            base, ext = os.path.splitext(file)
            counter = 1
            while os.path.exists(dst):
                dst = os.path.join(destination, f"{base}_{counter}{ext}")
                counter += 1

            shutil.move(src, dst)
            print(f"Moved: {src} -> {dst}")

print("Done!")
