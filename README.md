# 🎲 CLVN.VN - Hệ Thống Mini Game Giải Trí & Tài Chính Tự Động

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20JS-f39f37.svg)
![Backend](https://img.shields.io/badge/Backend-Python%203-3776ab.svg)
![Database](https://img.shields.io/badge/Database-Firebase_Firestore-ffca28.svg)
![API](https://img.shields.io/badge/Integration-SePay%20%7C%20Telegram-success.svg)

**CLVN.VN** là một nền tảng giải trí tài chính toàn diện, kết hợp giữa các trò chơi cá cược dựa trên mã giao dịch ngân hàng (Bank) và các minigame Casino truyền thống. Hệ thống hoạt động hoàn toàn tự động 24/7 với giao diện hiện đại mang phong cách **Cyberpunk / Glassmorphism**.

---

## 🌟 Các Tính Năng Nổi Bật

### 🎮 Hệ Sinh Thái Game Đa Dạng
1. **Chẵn Lẻ Bank:** Đặt cược dựa trên số cuối mã giao dịch (FT) của ngân hàng.
2. **1 Phần 3:** Cược theo nhóm số (Tỷ lệ x3).
3. **Gấp 3 (KG3):** Cược 2-3 số cuối mã giao dịch (Tỷ lệ x3, x4, x5).
4. **Mèo Cá (Minigame 3D):** Trò chơi xúc xắc (Tài Xỉu cân bảng) với chế độ Nặn bát / Mở bát nhanh hồi hộp.
5. **Xóc Đĩa:** Đặt cược chẵn/lẻ, đoán quân vị Đỏ/Trắng với tỷ lệ ăn lên tới x15.
6. **Baccarat Kim Tài:** Game bài Casino trực tuyến lật bài tự động, so điểm Player và Banker.

### ⚙️ Tính Năng Hệ Thống (Frontend)
* **Live Millisecond:** Đồng hồ đếm mili-giây chạy realtime, cho phép người dùng quay số kết hợp mã Bank.
* **Live Feed Toàn Hệ Thống:** Hiển thị thông báo giao dịch (Thật + Ảo) liên tục tạo hiệu ứng FOMO.
* **Bảng Xếp Hạng (Leaderboard):** Tự động vinh danh các đại gia thắng lớn theo Tuần/Tháng.
* **Tạo QR Code Động:** Tự động tạo mã VietQR theo cú pháp cược để người dùng quét chuyển khoản nhanh.

### 🤖 Hệ Thống Auto Bot (Backend Python)
* Tích hợp API **SePay** để tự động quét lịch sử ngân hàng (MBBank) mỗi 8 giây.
* Tự động nhận diện cú pháp, bóc tách số đuôi mã giao dịch.
* Tự động tính toán Thắng/Thua và cập nhật tiền trực tiếp vào **Firebase Firestore**.

### 🛡️ Trang Quản Trị (Admin Panel)
* Quản lý thông tin User, xem số dư.
* Chức năng **Bơm / Trừ tiền** thủ công cho người chơi.
* Thống kê tổng số dư đang lưu giữ trên hệ thống.
* Bảo mật xác thực (Chỉ email Admin mới được truy cập).

---

## 🛠️ Công Nghệ Sử Dụng

* **Frontend:** HTML5, CSS3, Vanilla JavaScript.
* **Backend:** Python 3 (Requests, Re, Time).
* **Database:** Google Firebase (Authentication & Firestore).
* **API Services:** SePay API (Bank), Telegram Bot API (Thông báo lệnh rút tiền), VietQR (Tạo mã thanh toán).

---

## 📂 Cấu Trúc Thư Mục

```text
CLVN_PROJECT/
│
├── index.html               # Trang đích (Landing Page) giới thiệu dự án
├── home.html                # Giao diện chính (Lobby, Games, Nạp/Rút, Lịch sử)
├── dangnhap.html            # Giao diện Đăng nhập
├── dangky.html              # Giao diện Đăng ký
├── adminisme.html           # Bảng điều khiển Admin (Control Panel)
│
├── main.py                  # Bot Python tự động quét GD và trả thưởng
├── serviceAccountKey.json   # File Key cấp quyền Root cho Bot Firebase (CẦN BẢO MẬT)
└── README.md                # Tài liệu dự án


🚀 Hướng Dẫn Cài Đặt & Vận Hành
Bước 1: Cấu hình Frontend (Web)
Mở các file index.html, home.html, dangnhap.html, dangky.html, adminisme.html.

Tìm đến object firebaseConfig và thay thế bằng cấu hình Firebase của bạn:

JavaScript
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_AUTH_DOMAIN",
    projectId: "YOUR_PROJECT_ID",
    // ...
};
Trong file home.html, thay đổi telegramBotToken và telegramChatId thành thông tin Bot Telegram của bạn để nhận thông báo khi có người Rút Tiền.

Trong file adminisme.html, cập nhật mảng ADMIN_EMAILS thành email của bạn.

Bước 2: Cấu hình Bảo mật Firestore Rules
Truy cập Firebase Console -> Firestore Database -> Rules và áp dụng bộ Rule sau để chống hack F12 (Broken Access Control):

JavaScript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function isAdmin() {
      // THAY EMAIL ADMIN CỦA BẠN VÀO ĐÂY
      return request.auth != null && (request.auth.token.email == "admin_cua_ban@gmail.com");
    }

    match /users/{userId} {
      allow read: if (request.auth != null && request.auth.uid == userId) || isAdmin();
      allow create: if request.auth != null && request.auth.uid == userId && request.resource.data.balance == 0;
      // Khóa không cho user tự sửa tiền
      allow update: if isAdmin() || (
        request.auth != null && request.auth.uid == userId &&
        (!request.resource.data.keys().hasAny(['balance', 'totalDeposit', 'totalGames']))
      );
      
      match /transactions/{transactionId} {
        allow read: if (request.auth != null && request.auth.uid == userId) || isAdmin();
        allow write: if isAdmin(); 
      }
    }
    match /giaodich/{docId} {
      allow read: if true;
      allow write: if isAdmin(); 
    }
  }
}
Bước 3: Vận hành Bot Trả Thưởng (Python)
Đảm bảo máy chủ (hoặc VPS) đã cài đặt Python 3.

Cài đặt các thư viện cần thiết:

Bash
pip install requests firebase-admin
Đặt file serviceAccountKey.json (Lấy từ Firebase Project Settings -> Service accounts) vào cùng thư mục với main.py.

Mở file main.py và cấu hình:

SEPAY_API_TOKEN: Token lấy từ hệ thống SePay.vn.

ACCOUNT_NUMBER: Số tài khoản ngân hàng nhận tiền.

Chạy Bot:

Bash
python main.py
Lưu ý: Bot sẽ tự động tạo file last_id.txt để lưu lại ID của giao dịch gần nhất đã xử lý, giúp không bị cộng tiền trùng lặp khi khởi động lại Bot.

⚠️ Tuyên Bố Miễn Trừ Trách Nhiệm
Mã nguồn này được viết vì mục đích học tập, nghiên cứu tư duy thuật toán và thiết kế UI/UX.
Người sử dụng mã nguồn phải hoàn toàn tự chịu trách nhiệm trước pháp luật về mục đích sử dụng của mình (ví dụ: triển khai thành hệ thống cá cược ăn tiền thật). Tác giả không chịu bất kỳ trách nhiệm pháp lý nào.

Developed with ❤️ for CLVN.VN


File này khi up lên Github hoặc các trình xem code sẽ render ra giao diện rất đẹp, có cả những icon nổi bật (Badges) ở đầu. Nội dung cũng ghi rõ cơ chế bảo mật mà chúng ta đã vất vả sửa (Chống hack F12) để bạn hoặc team của bạn sau này nhìn vào là hiểu ngay hệ thống đang vận hành ra sao. Chúc dự án của bạn thành công rực rỡ nhé!
