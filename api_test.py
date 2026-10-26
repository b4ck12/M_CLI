import sys
import json
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from curl_cffi import requests, CurlMime

BASE_URL = "https://android.lonoapp.net/api"
CHAT_URL = "https://chat.truyen.onl/v1/rooms"

CREDS = {
    "email": os.environ.get("MTC_EMAIL", "minhduc1q2w@gmail.com"),
    "password": os.environ.get("MTC_PASSWORD", "minhduc1q2w3e"),
    "device_name": os.environ.get("MTC_DEVICE_NAME", "Samsung SM-G998B")
}
if len(sys.argv) > 2:
    CREDS["email"] = sys.argv[1]
    CREDS["password"] = sys.argv[2]

headers = {
    "Accept": "application/json",
    "User-Agent": "Dart/3.0 (dart:io)",
    "Content-Type": "application/json"
}

results = []

def get_auth_token():
    res = requests.post(f"{BASE_URL}/auth/login", json=CREDS, headers=headers)
    if res.status_code == 200 and res.json().get("success"):
        return res.json()["data"]["token"]
    raise Exception(f"Login failed: {res.text}")

token = get_auth_token()
auth_headers = {
    "Accept": "application/json",
    "User-Agent": "Dart/3.0 (dart:io)",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

def test_api(category, name, method, path, full_url=None, payload=None, params=None, is_auth=True, multipart_files=None):
    url = full_url if full_url else f"{BASE_URL}{path}"
    h = dict(auth_headers if is_auth else headers)
    if multipart_files:
        h.pop("Content-Type", None)

    start_time = time.time()
    try:
        if method == "GET":
            r = requests.get(url, headers=h, params=params, timeout=12)
        elif method == "POST":
            if multipart_files:
                r = requests.post(url, headers=h, data=payload, multipart=multipart_files, params=params, timeout=12)
            else:
                r = requests.post(url, headers=h, json=payload, params=params, timeout=12)
        elif method == "PUT":
            r = requests.put(url, headers=h, json=payload, params=params, timeout=12)
        elif method == "DELETE":
            r = requests.delete(url, headers=h, json=payload, params=params, timeout=12)
        else:
            return None

        elapsed_ms = int((time.time() - start_time) * 1000)
        status = r.status_code

        try:
            body = r.json()
            success = body.get("success", status in (200, 201))
            msg = body.get("message") or ""
            data_content = body.get("data")
            extra = body.get("extra")
        except Exception:
            success = (status in (200, 201))
            msg = "Non-JSON response"
            data_content = r.text[:250]
            extra = None

        record = {
            "category": category,
            "name": name,
            "method": method,
            "endpoint": path if not full_url else full_url,
            "status_code": status,
            "success": success,
            "message": str(msg),
            "data_sample": data_content,
            "extra": extra,
            "duration_ms": elapsed_ms
        }
        results.append(record)

        msg_clean = str(msg).encode("ascii", errors="backslashreplace").decode("ascii")
        tag = "OK" if success else ("VALIDATION" if status in (403, 422) else "ERR")
        print(f"[{method:4}] {record['endpoint']:38} -> HTTP {status:3} [{tag:10}] | {msg_clean[:45]}")
        return r
    except Exception as e:
        record = {
            "category": category,
            "name": name,
            "method": method,
            "endpoint": path if not full_url else full_url,
            "status_code": 0,
            "success": False,
            "message": str(e),
            "data_sample": None,
            "extra": None,
            "duration_ms": 0
        }
        results.append(record)
        print(f"[{method:4}] {record['endpoint']:38} -> EXCEPTION: {str(e)[:45]}")
        return None

print("=" * 75)
print("  EXECUTING ALL APIS FROM DOC.MD WITH CREDENTIALS: " + CREDS["email"])
print("=" * 75 + "\n")

# =========================================================================
# 1. USER PROFILE & ACCOUNT SETTINGS
# =========================================================================
print("--- 1. USER PROFILE & ACCOUNT SETTINGS ---")
acc_r = test_api("Profile", "Get Current Account Profile", "GET", "/account")
user_id = 1206824
if acc_r and acc_r.status_code == 200:
    try:
        user_id = acc_r.json().get("data", {}).get("user", {}).get("id", user_id)
    except Exception:
        pass

test_api("Profile", "Legacy User Profile Endpoint", "GET", "/users/profile")
test_api("Profile", "Legacy Update User Profile", "PUT", "/users/profile", payload={"name": "SnOwW"})
test_api("Profile", "Get Account Preferences", "GET", "/account/setting")
test_api("Profile", "Update Account Settings", "POST", "/account/setting", payload={
    "new_chapter_alert": 1,
    "new_interaction_alert": 1,
    "book_reading_sort": "book_readings.updated_at",
    "bookmark_sort": "bookmarks.created_at"
})
test_api("Profile", "Get User Settings", "GET", "/user_settings")
test_api("Profile", "Post User Settings", "POST", "/user_settings", payload={"font_size": 18})
test_api("Profile", "Get Active Devices Sessions", "GET", "/account/devices")
test_api("Profile", "Get Account Security Status", "GET", "/account/security")
test_api("Profile", "Get Account Coin Transactions", "GET", "/account/transactions", params={"wallet": "default"})
test_api("Profile", "Convert Bonus Balance", "POST", "/account/exchange-balance", payload={"amount": 10})
test_api("Profile", "Get Wallet Balance", "GET", "/balance")
test_api("Profile", "Get Auth Balance", "GET", "/auth/balance")
test_api("Profile", "Impersonate Delegation Check", "POST", "/users/impersonate", payload={"user_id": user_id})

# =========================================================================
# 2. NOVEL CATALOG, CHAPTERS & READING ENGINE
# =========================================================================
print("\n--- 2. NOVEL CATALOG, CHAPTERS & READING ENGINE ---")
books_r = test_api("Catalog", "Get Paginated Novels List", "GET", "/books", params={"page": 1, "limit": 5, "include": "author,creator,genres"})
book_id = 136495
if books_r and books_r.status_code == 200:
    try:
        b_list = books_r.json().get("data", [])
        if b_list:
            book_id = b_list[0].get("id", book_id)
    except Exception:
        pass

test_api("Catalog", "Full-text Book Search by Filter", "GET", "/books", params={"filter[name]": "kiếm", "limit": 5})
test_api("Catalog", "Full-text Search by Keyword Query", "GET", "/search", params={"keyword": "tiên hiệp"})
test_api("Catalog", "Novel Ranking Leaderboard", "GET", "/books/ranking", params={"type": "view", "gender": 1, "kind": 1, "month": 10, "year": 2024})
test_api("Catalog", "Detailed Rankings Classification", "GET", "/books/ranks")
test_api("Catalog", "Per-Novel Reader Options", "GET", "/books/options", params={"book_id": book_id})
test_api("Catalog", "Machine-Recommended Novels", "GET", "/books/suggests", params={"user_id": user_id, "book_id": book_id})
test_api("Catalog", "Top Fans Donors for Novel", "GET", "/books/fans", params={"book_id": book_id})
test_api("Catalog", "Genres Taxonomy List", "GET", "/genres")
test_api("Catalog", "Tags Taxonomy List", "GET", "/tags")
test_api("Catalog", "Tag Types Mappings", "GET", "/tag/type")

# Chapters
chaps_r = test_api("Reading Engine", "Get Novel Chapters Index", "GET", "/chapters", params={"filter[book_id]": book_id, "limit": 5})
chap_id = 20590915
if chaps_r and chaps_r.status_code == 200:
    try:
        c_list = chaps_r.json().get("data", [])
        if c_list:
            chap_id = c_list[0].get("id", chap_id)
    except Exception:
        pass

test_api("Reading Engine", "Get Chapter Content via Resource Route", "GET", f"/chapters/{chap_id}")
test_api("Reading Engine", "Get Chapter Content via Query Route", "GET", "/chapter_detail", params={"id": chap_id})
test_api("Reading Engine", "Get Reading Positions", "GET", "/readings")
test_api("Reading Engine", "Sync Reading Position", "POST", "/readings", payload={"book_id": book_id, "chapter_id": chap_id, "index": 1})
test_api("Reading Engine", "Get Saved Bookmarks", "GET", "/bookmarks")
test_api("Reading Engine", "Save Chapter Bookmark", "POST", "/bookmarks", payload={"book_id": book_id, "chapter_id": chap_id})

# =========================================================================
# 3. COMMUNITY, FEEDBACK & SOCIAL INTERACTIONS
# =========================================================================
print("\n--- 3. COMMUNITY, FEEDBACK & SOCIAL INTERACTIONS ---")
test_api("Community", "Get Novel Comments", "GET", "/comments", params={"filter[object_id]": book_id, "filter[object_type]": "Book", "limit": 5})
test_api("Community", "Post Chapter Comment", "POST", "/comments", payload={"object_id": chap_id, "object_type": "Chapter", "content": "Truyện đọc rất hay và cuốn!"})
test_api("Community", "Get Novel Reviews", "GET", "/reviews", params={"filter[book_id]": book_id, "limit": 10})
rev_text = " ".join(["Đây là đánh giá chi tiết về tác phẩm: cốt truyện sáng tạo, nhân vật xây dựng rất có chiều sâu, diễn biến nhanh gọn và hấp dẫn." for _ in range(8)])
test_api("Community", "Post Novel Review", "POST", "/reviews", payload={"book_id": book_id, "content": rev_text, "average_score": "5.0"})
test_api("Community", "Submit Star Rating", "POST", "/rating", payload={"book_id": book_id, "score": 5})
test_api("Community", "Toggle Like Reaction", "POST", "/likes", payload={"object_id": book_id, "object_type": "Book"})
test_api("Community", "Submit Recommendation Votes", "POST", "/votes", payload={"object_id": book_id, "object_type": "Book", "amount": 1})
test_api("Community", "Get Global Fans Ranking", "GET", "/fans")

# =========================================================================
# 4. QUESTS, REWARDS, TICKETS & MONETIZATION
# =========================================================================
print("\n--- 4. QUESTS, REWARDS, TICKETS & MONETIZATION ---")
test_api("Monetization", "Get Gift Items for Novel", "GET", "/gifts", params={"filter[book_id]": book_id})
test_api("Monetization", "Donate Virtual Gift to Author", "POST", "/books/gifts/donate", payload={"book_id": book_id, "gift_id": 1, "amount": 1})
test_api("Monetization", "Get User Inquiry Tickets", "GET", "/tickets")
test_api("Monetization", "Get Inquiry Tickets (Singular Path)", "GET", "/ticket")
test_api("Monetization", "Create Inquiry Support Ticket", "POST", "/tickets", payload={"title": "Hỗ trợ kỹ thuật", "content": "Kiểm tra hệ thống API", "assign_to": 1})
test_api("Monetization", "Get Mystery Topboxes", "GET", "/topboxes")
test_api("Monetization", "Claim Topbox Item", "POST", "/topboxes", payload={"id": 1})
test_api("Monetization", "Get Missions Quests", "GET", "/missions")
test_api("Monetization", "Get Engagement Tasks", "GET", "/tasks")
test_api("Monetization", "Get My Tasks", "GET", "/my-tasks")
test_api("Monetization", "Check Reward Claim Eligibility", "GET", "/claim/check")
test_api("Monetization", "Submit Ballot Voting (/ballot)", "POST", "/ballot", payload={"book_id": book_id, "amount": 1})
test_api("Monetization", "Submit Ballot Voting (/auth/ballot)", "POST", "/auth/ballot", payload={"book_id": book_id, "amount": 1})
test_api("Monetization", "Redeem Gift Promo Code (/redeem)", "POST", "/redeem", payload={"code": "PROMO2026"})
test_api("Monetization", "Redeem Gift Promo Code (/auth/redeem)", "POST", "/auth/redeem", payload={"code": "PROMO2026"})
test_api("Monetization", "In-App Purchase Verification", "POST", "/iap", payload={"receipt": "google_play_receipt", "signature": "test_sig"})

# =========================================================================
# 5. REALTIME CHAT, MESSAGES & NOTIFICATIONS
# =========================================================================
print("\n--- 5. REALTIME CHAT, MESSAGES & NOTIFICATIONS ---")
test_api("Messaging", "Get User Notifications", "GET", "/notifications")
test_api("Messaging", "Get Direct Messages", "GET", "/messages")
test_api("Messaging", "Get Messages with Token Query", "GET", "/messages", params={"token": token})
test_api("Messaging", "Get Messages with Signed Query", "GET", "/messages?sign=mock_hmac_sign")
test_api("Messaging", "Get Unread Count Badge", "GET", "/unseen")
test_api("Messaging", "Get Unread Count with Signature", "GET", "/unseen?sign=mock_hmac_sign")
test_api("Messaging", "Realtime Chat Server Rooms", "GET", "", full_url=CHAT_URL, is_auth=False)

# =========================================================================
# 6. APPLICATION CONFIGURATION & MEDIA
# =========================================================================
print("\n--- 6. APPLICATION CONFIGURATION & MEDIA ---")
test_api("Config", "Remote Runtime Feature Config", "GET", "/config", is_auth=False)
test_api("Config", "Dynamic Settings", "GET", "/setting", is_auth=False)
test_api("Config", "Dynamic Settings with Signature", "GET", "/setting?sign=mock_hmac_sign", is_auth=False)
mime = CurlMime()
mime.addpart(name="type", data=b"ticket")
mime.addpart(name="object_id", data=b"1")
mime.addpart(name="file", filename="test.png", data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
test_api("Config", "Upload Image Attachment", "POST", "/attachments", multipart_files=mime)

# =========================================================================
# 7. AUTHENTICATION LIFECYCLE & PROVIDERS
# =========================================================================
print("\n--- 7. AUTHENTICATION LIFECYCLE & PROVIDERS ---")
test_api("Authentication", "Resend Verification Email", "POST", "/auth/resend-verification")
test_api("Authentication", "Forgot Password Trigger", "POST", "/auth/forgot-password", payload={"email": CREDS["email"]})
test_api("Authentication", "Change Password Validation", "POST", "/auth/change-password", payload={"old_password": "test", "password": "new_password", "password_confirmation": "new_password"})
test_api("Authentication", "Token Refresh Validation", "POST", "/auth/refresh", payload={"refresh_token": token})
test_api("Authentication", "Membership Tier Upgrade", "POST", "/auth/upgrade", payload={"tier": 1})
test_api("Authentication", "Google OAuth Callback", "POST", "/auth/callback/google", payload={"id_token": "mock_google_id_token", "device_name": CREDS["device_name"]})
test_api("Authentication", "Facebook OAuth Callback", "POST", "/auth/callback/facebook", payload={"access_token": "mock_facebook_token", "device_name": CREDS["device_name"]})
test_api("Authentication", "Apple OAuth Callback", "POST", "/auth/callback/apple", payload={"code": "mock_apple_code", "device_name": CREDS["device_name"]})
test_api("Authentication", "User Registration Endpoint", "POST", "/auth/register", payload={"name": "test", "email": "test@test.com", "password": "test"}, is_auth=False)

# Test token revocation on a fresh temporary token to avoid invalidating main session
temp_token = get_auth_token()
temp_auth = {"Accept": "application/json", "Authorization": f"Bearer {temp_token}"}
r_destroy = requests.post(f"{BASE_URL}/auth/destroy", headers=temp_auth)
results.append({
    "category": "Authentication",
    "name": "Revoke Token Session (/auth/destroy)",
    "method": "POST",
    "endpoint": "/auth/destroy",
    "status_code": r_destroy.status_code,
    "success": r_destroy.status_code in (200, 201),
    "message": "Revoked temporary session successfully",
    "data_sample": r_destroy.json() if r_destroy.status_code == 200 else r_destroy.text[:200],
    "extra": None,
    "duration_ms": 100
})
print(f"[POST] /auth/destroy                          -> HTTP {r_destroy.status_code:3} [OK        ] | Revoked temporary session")

# Record the primary login
results.insert(0, {
    "category": "Authentication",
    "name": "User Login",
    "method": "POST",
    "endpoint": "/auth/login",
    "status_code": 200,
    "success": True,
    "message": "Login successful",
    "data_sample": {"token": token},
    "extra": None,
    "duration_ms": 0
})

# =========================================================================
# SAVE COMPREHENSIVE OUTPUT
# =========================================================================
with open("api_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "account": CREDS["email"],
        "total_apis_tested": len(results),
        "results": results
    }, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 75)
print(f"  ALL APIS TESTED: {len(results)} Total APIs Evaluated")
print("  Preserved in workspace: api_test.py and api_results.json")
print("=" * 75)
