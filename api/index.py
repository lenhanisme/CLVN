import os
from flask import Flask, request, jsonify
import re
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# ================= KHỞI TẠO FIREBASE (VERCEL SAFE) =================
db = None
try:
    if not firebase_admin._apps:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(current_dir, "serviceAccountKey.json")
        
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("[+] Firebase kết nối thành công!")
        else:
            print(f"[-] LỖI CHÍNH MẠNG: Không tìm thấy file {key_path}")
    else:
        db = firestore.client()
except Exception as e:
    print("[-] Lỗi khởi tạo Firebase:", e)

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

def check_kg3_result(ref_number):
    ref_str = ''.join(filter(str.isdigit, str(ref_number)))
    if not ref_str: return False, 0.0
    last2 = ref_str[-2:] if len(ref_str) >= 2 else ""
    last3 = ref_str[-3:] if len(ref_str) >= 3 else ""
    
    if last3 in ['123', '234', '456', '678', '789']: return True, 5.0
    if last2 in ['66', '99']: return True, 4.0
    if last2 in ['02', '13', '17', '19', '21', '29', '35', '37', '47', '49', '51', '54', '57', '63', '64', '74', '83', '91', '95', '96']: return True, 3.0
    return False, 0.0

def get_last_digit(ref_number):
    digits = [char for char in str(ref_number) if char.isdigit()]
    return int(digits[-1]) if digits else None

def find_user_by_username(username):
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        for doc in docs:
            email = doc.to_dict().get('email', '')
            if email.split('@')[0].lower() == username.lower():
                return doc.reference
    except Exception as e:
        print("[-] Lỗi khi quét tìm User:", e)
    return None

# ================= API WEBHOOK =================
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def sepay_webhook(path):
    if request.method == 'GET':
        return jsonify({"status": "ok", "message": "API Webhook is fully operational!"}), 200

    if db is None:
        return jsonify({"status": "error", "message": "Firebase not initialized"}), 500

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    tx_id = str(data.get("id", ""))
    amount_in = float(data.get("transferAmount", data.get("amountIn", data.get("amount_in", 0))))
    ref_number = data.get("referenceCode", data.get("referenceNumber", data.get("reference_number", "")))
    content = data.get("content", data.get("transactionContent", data.get("transaction_content", ""))).strip()

    if amount_in <= 0:
        return jsonify({"status": "ignored", "message": "Not an incoming transfer"}), 200

    print(f"\n[*] WEBHOOK NHẬN GD MỚI | ID: {tx_id} | Tiền: {amount_in:,.0f}đ | Mã Bank: {ref_number} | ND: {content}")

    if amount_in < 2000:
        return jsonify({"status": "ignored", "message": "Amount too low"}), 200

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
                rate = 3.0
        else:
            last_digit = get_last_digit(ref_number)
            if last_digit is None:
                return jsonify({"status": "error", "message": "Parse ref digit failed"}), 400
            
            rule = GAME_RULES.get(choice)
            if last_digit in rule['digits']:
                rate = rule['rate']
                payout = amount_in * rate
                status = "win"
            else:
                rate = rule['rate']

        print(f"    => Xử lý: User [{username}] - Cửa [{choice}] - Kết quả [{status.upper()}] - Thưởng: {payout}")

        user_ref = find_user_by_username(username)
        if user_ref:
            try:
                # FIX BẤT TỬ: Dùng firestore.Increment() chống sập Serverless
                user_ref.set({
                    'balance': firestore.Increment(payout),
                    'totalDeposit': firestore.Increment(amount_in),
                    'totalGames': firestore.Increment(1)
                }, merge=True)
                
                tx_data = {
                    'transId': ref_number,
                    'amount': amount_in,
                    'choice': f"{choice} (x{rate})" if choice != "KG3" or status == "win" else "KG3",
                    'rate': rate,
                    'status': status,
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                
                user_ref.collection('transactions').document(str(tx_id)).set(tx_data)
                if ref_number:
                    db.collection('giaodich').document(str(ref_number)).set(tx_data)

                print("    [+] ĐÃ LƯU KẾT QUẢ FIREBASE THÀNH CÔNG!")
                return jsonify({"status": "success", "message": "Payout processed"}), 200
            
            except Exception as e:
                print(f"    [-] Lỗi Firebase Write: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            print(f"    [-] Không tìm thấy user '{username}'")
            return jsonify({"status": "ignored", "message": "User not found"}), 200
    else:
        print("    [-] Sai cú pháp cược.")
        return jsonify({"status": "ignored", "message": "Invalid syntax"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
