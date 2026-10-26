# 📚 MTC NovelFever Terminal App

Ứng dụng dòng lệnh (Terminal TUI Client) cho nền tảng đọc truyện **MTC / NovelFever**. Giao diện hiện đại, trực quan, hỗ trợ duyệt danh mục, tìm kiếm, đọc truyện và tải tiểu thuyết sang tệp `.txt` tiện lợi.

---

## 🌟 Giới Thiệu

- **Giao diện TUI chuyên nghiệp:** Thiết kế dạng bảng điều khiển (Dashboard) với `rich`, chuyển màn hình tại chỗ không trôi dòng.
- **Khám phá & Đọc truyện:** Xem truyện mới cập nhật, bảng xếp hạng đọc nhiều nhất, đọc trực tiếp nội dung chương trên terminal.
- **Tải sách `.txt`:** Hỗ trợ tải trọn bộ hoặc một số chương tùy chọn với đầy đủ thông tin truyện, tác giả, thể loại và giới thiệu.
- **Hỗ trợ mọi tài khoản:** Đăng nhập bằng tài khoản cá nhân, tự động lưu phiên để sử dụng nhanh cho các lần sau mà không cần gõ lại mật khẩu.

---

## ⚙️ Cài Đặt

### Yêu Cầu Hệ Thống
- Hệ điều hành: **Windows 10 / Windows 11**
- Python: **3.8 trở lên**

### Cài Đặt Thư Viện Phụ Thuộc
Chạy lệnh sau trong terminal hoặc PowerShell:

```powershell
pip install rich curl_cffi
```

---

## 🚀 Hướng Dẫn Sử Dụng

### 1. Khởi Chạy Giao Diện Tương Tác (Khuyên Dùng)

Chạy lệnh:
```powershell
python mtc_cli.py
```

- Trong lần chạy đầu tiên, ứng dụng sẽ yêu cầu bạn nhập **Email** và **Mật khẩu** tài khoản MTC.
- Bạn có thể chọn lưu phiên (`y`) để các lần chạy sau tự động đăng nhập.

#### Các Chức Năng Chính Trong Ứng Dụng:
- `[1]` **Hồ sơ tài khoản:** Xem thông tin cá nhân, cấp độ và số dư ví (Xu, Kẹo, Khóa, Phiếu).
- `[2]` **Danh mục truyện:** Duyệt danh sách truyện mới cập nhật (`[N]` trang sau, `[P]` trang trước, gõ `[ID]` để xem chi tiết).
- `[3]` **Tìm kiếm truyện:** Tìm kiếm tác phẩm theo tên hoặc từ khóa.
- `[4]` **Bảng xếp hạng:** Xem top truyện có lượt đọc, lượt thích, bình chọn và đánh giá cao nhất.
- `[5]` **Danh sách chương:** Xem mục lục các chương của truyện theo ID.
- `[6]` **Đọc truyện:** Đọc nội dung chương trên terminal (phím `[N]` chương tiếp, `[P]` chương trước).
- `[7]` **Tải truyện về máy:** Tải truyện sang tệp `.txt` (được lưu tại thư mục `downloads/`).
- `[8]` **Đánh giá độc giả:** Đọc các bài nhận xét, đánh giá của cộng đồng.
- `[9]` **Lịch sử ví tiền:** Tra cứu biến động số dư và sao kê tài khoản.
- `[10]` **Đổi tài khoản:** Đăng xuất tài khoản hiện tại để đăng nhập tài khoản khác.
- `[0]` hoặc `[B]` **Quay lại / Thoát.**

---

### 2. Sử Dụng Nhanh Qua Tham Số Dòng Lệnh (CLI Flags)

Bạn có thể thực hiện nhanh các tác vụ mà không cần vào menu tương tác:

- **Tìm kiếm truyện:**
  ```powershell
  python mtc_cli.py -s "tiên đế"
  ```

- **Tải truyện sang file `.txt`:**
  ```powershell
  # Tải 10 chương đầu của truyện có ID 136495:
  python mtc_cli.py -d 136495 --max-chapters 10

  # Tải toàn bộ truyện:
  python mtc_cli.py -d 136495
  ```

- **Đọc nhanh một chương theo Chapter ID:**
  ```powershell
  python mtc_cli.py -r 20590915
  ```

- **Xem bảng xếp hạng:**
  ```powershell
  python mtc_cli.py --rankings
  ```

- **Đăng nhập bằng tài khoản cụ thể:**
  ```powershell
  python mtc_cli.py -e "email@example.com" -p "matkhau"
  ```

- **Đăng xuất và xóa phiên đăng nhập:**
  ```powershell
  python mtc_cli.py --logout
  ```
