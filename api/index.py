from flask import Flask, request, jsonify
import re
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# ================= KHỞI TẠO FIREBASE (Serverless Safe) =================
# Kiểm tra xem app đã khởi tạo chưa (tránh lỗi sập web khi Vercel khởi động lại liên tục)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        print("[+] Đã kết nối thành công với Firebase Firestore!")
    except Exception as e:
        print("[-] Lỗi kết nối Firebase:", e)

db = firestore.client()

# ================= LUẬT CHƠI =================
GAME_RULES = {
    'C':  {'digits': [2, 4, 6, 8], 'rate': 2.0},
    'L':  {'digits': [1, 3, 5, 7], 'rate': 2.0},
    'C2': {'digits': [0, 2, 4, 6, 8], 'rate': 1.5},
    'L2': {'digits': [1, 3, 5, 7, 9], 'rate': 1.5},
    'CC': {'digits': [1, 2, 3, 4, 5], 'rate': 1.5},
    'LL': {'digits': [6, 7, 8, 9, 0], 'rate': 1.5},
    'N1': {'digits': [1, 5, 7], 'rate': 3.0},
    'N2': {'digits': [2, 4, 8], 'rate': 3.0},
    'N3': {'digits': [3, 6, 9], 'rate': 3.0}
}

# ================= KIỂM TRA GAME GẤP 3 (KG3) =================
def check_kg3_result(ref_number):
    ref_str = ''.join(filter(str.isdigit, str(ref_number)))
    if not ref_str: return False, 0.0
    
    last2 = ref_str[-2:] if len(ref_str) >= 2 else ""
    last3 = ref_str[-3:] if len(ref_str) >= 3 else ""
    
    x3_list = ['02', '13', '17', '19', '21', '29', '35', '37', '47', '49', '51', '54', '57', '63', '64', '74', '83', '91', '95', '96']
    x4_list = ['66', '99']
    x5_list = ['123', '234', '456', '678', '789']
    
    if last3 in x5_list: return True, 5.0
    if last2 in x4_list: return True, 4.0
    if last2 in x3_list: return True, 3.0
        
    return False, 0.0

def get_last_digit(ref_number):
    digits = [char for char in str(ref_number) if char.isdigit()]
    return int(digits[-1]) if digits else None

def find_user_by_username(username):
    users_ref = db.collection('users')
    docs = users_ref.stream()
    for doc in docs:
        email = doc.to_dict().get('email', '')
        if email.split('@')[0].lower() == username.lower():
            return doc.reference
    return None

# ================= API WEBHOOK LẮNG NGHE SEPAY =================
# SePay sẽ gọi vào đường dẫn /api/index (Phương thức POST) mỗi khi có tiền vào
@app.route('/api/index', methods=['POST'])
def sepay_webhook():
    # Lấy dữ liệu SePay bắn sang
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    # Định dạng Webhook của SePay (Tên biến có thể là amountIn hoặc amount_in tuỳ phiên bản)
    tx_id = str(data.get("id", ""))
    amount_in = float(data.get("amountIn", data.get("amount_in", 0)))
    ref_number = data.get("referenceNumber", data.get("reference_number", ""))
    content = data.get("transactionContent", data.get("transaction_content", "")).strip()

    # Bỏ qua nếu không phải tiền vào
    if amount_in <= 0:
        return jsonify({"status": "ignored", "message": "Not an incoming transfer"}), 200

    print(f"\n[*] WEBHOOK NHẬN GD MỚI | ID: {tx_id} | Tiền: {amount_in:,.0f}đ | Mã Bank: {ref_number}")

    if amount_in < 2000:
        print("    [-] Bỏ qua: Số tiền cược dưới 2.000đ.")
        return jsonify({"status": "ignored", "message": "Amount too low"}), 200

    # Tìm cú pháp: CLVN <username> <C/L/C2/L2/CC/LL/N1/N2/N3/KG3>
    match = re.search(r'CLVN\s+(\w+)\s+(C2|L2|CC|LL|N1|N2|N3|KG3|C|L)', content, re.IGNORECASE)
    
    if match:
        username = match.group(1).lower()
        choice = match.group(2).upper()
        
        status = "lose"
        payout = 0
        rate = 0.0

        if choice == 'KG3':
            is_win, result_rate = check_kg3_result(ref_number)
            if is_win:
                rate = result_rate
                payout = amount_in * rate
                status = "win"
            else:
                rate = 3.0 # Chỉ dùng để lưu lịch sử
        else:
            last_digit = get_last_digit(ref_number)
            if last_digit is None:
                return jsonify({"status": "error", "message": "Cannot parse reference digit"}), 400

            rule = GAME_RULES.get(choice)
            if last_digit in rule['digits']:
                rate = rule['rate']
                payout = amount_in * rate
                status = "win"
            else:
                rate = rule['rate']

        print(f"    => Lệnh: {username} | Cửa: {choice} | Kết quả: {status.upper()} | Trả thưởng: {payout}")

        # TƯƠNG TÁC FIREBASE
        user_ref = find_user_by_username(username)
        if user_ref:
            try:
                @firestore.transactional
                def update_user_stats(transaction, ref):
                    snapshot = ref.get(transaction=transaction)
                    user_data = snapshot.to_dict() if snapshot.exists else {}
                    
                    current_balance = float(user_data.get('balance', 0))
                    total_deposit = float(user_data.get('totalDeposit', 0))
                    total_games = int(user_data.get('totalGames', 0))
                    
                    transaction.update(ref, {
                        'balance': current_balance + payout,
                        'totalDeposit': total_deposit + amount_in,
                        'totalGames': total_games + 1
                    })
                
                transaction = db.transaction()
                update_user_stats(transaction, user_ref)
                
                tx_data = {
                    'transId': ref_number,
                    'amount': amount_in,
                    'choice': f"{choice} (x{rate})" if choice != "KG3" or status == "win" else f"KG3 (Chờ x3-x5)",
                    'rate': rate,
                    'status': status,
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                
                user_ref.collection('transactions').document(str(tx_id)).set(tx_data)
                if ref_number:
                    db.collection('giaodich').document(str(ref_number)).set(tx_data)

                print("    [+] Đã cập nhật Firebase thành công!")
                return jsonify({"status": "success", "message": "Payout processed"})
                
            except Exception as e:
                print(f"    [-] Lỗi Firebase: {e}")
                return jsonify({"status": "error", "message": "Firebase update failed"}), 500
        else:
            print(f"    [-] Không tìm thấy user '{username}'")
            return jsonify({"status": "ignored", "message": "User not found"}), 404
    else:
        print("    [-] Sai cú pháp cược.")
        return jsonify({"status": "ignored", "message": "Invalid syntax"}), 200

# Tuỳ thuộc vào nền tảng (Vercel hỗ trợ biến app ở dạng root)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
