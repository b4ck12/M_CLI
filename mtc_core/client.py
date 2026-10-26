"""
MTC API Client
Handles REST communication with https://android.lonoapp.net/api,
token management, request headers, error handling, and chapter decryption.
"""

import time
from typing import Optional, List, Dict, Any, Tuple
from curl_cffi import requests
from .models import Book, Chapter, UserProfile, NovelReview
from .crypto import decrypt_chapter_content

DEFAULT_BASE_URL = "https://android.lonoapp.net/api"

class MTCClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, device_name: str = "Samsung SM-G998B"):
        self.base_url = base_url.rstrip("/")
        self.device_name = device_name
        self.token: Optional[str] = None
        self.user_profile: Optional[UserProfile] = None
        self._session = requests.Session()

    def _get_headers(self, authenticated: bool = True) -> Dict[str, str]:
        h = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Dart/3.0 (dart:io)",
            "x-app": "app.android"
        }
        if authenticated and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def login(self, email: str, password: str) -> UserProfile:
        """Authenticates with user credentials and initializes user session."""
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": email,
            "password": password,
            "device_name": self.device_name
        }
        resp = self._session.post(url, json=payload, headers=self._get_headers(authenticated=False), timeout=15)
        data = resp.json()

        if resp.status_code != 200 or not data.get("success"):
            err_msg = data.get("message", "Login failed")
            raise ConnectionError(f"Authentication failed: {err_msg}")

        self.token = data["data"]["token"]
        return self.get_profile()

    def login_with_token(self, token: str) -> UserProfile:
        """Restores an authenticated user session using an existing Sanctum token."""
        self.token = token
        return self.get_profile()

    def logout(self) -> bool:
        """Revokes the current session token."""
        url = f"{self.base_url}/auth/logout"
        try:
            resp = self._session.post(url, headers=self._get_headers(), timeout=10)
            success = resp.status_code == 200
        except Exception:
            success = False
        self.token = None
        self.user_profile = None
        return success

    def get_profile(self) -> UserProfile:
        """Fetches the current user profile, currency balances, and VIP status."""
        url = f"{self.base_url}/account"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        data = resp.json()
        if resp.status_code != 200 or not data.get("success"):
            raise ConnectionError(f"Failed to fetch profile: {data.get('message')}")
        
        self.user_profile = UserProfile.from_dict(data["data"])
        return self.user_profile

    def get_settings(self) -> Dict[str, Any]:
        """Retrieves user application and reading preferences."""
        url = f"{self.base_url}/account/setting"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get("data", {})

    def update_settings(self, new_chapter_alert: int = 1, new_interaction_alert: int = 1,
                        reading_sort: str = "book_readings.updated_at",
                        bookmark_sort: str = "bookmarks.created_at") -> bool:
        """Updates user account settings."""
        url = f"{self.base_url}/account/setting"
        payload = {
            "new_chapter_alert": new_chapter_alert,
            "new_interaction_alert": new_interaction_alert,
            "book_reading_sort": reading_sort,
            "bookmark_sort": bookmark_sort
        }
        resp = self._session.post(url, json=payload, headers=self._get_headers(), timeout=15)
        return resp.status_code == 200

    def get_transactions(self, wallet: str = "default", page: int = 1) -> List[Dict[str, Any]]:
        """Retrieves financial transactions history."""
        url = f"{self.base_url}/account/transactions"
        params = {"wallet": wallet, "page": page}
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("data", [])
        return []

    def get_catalog(self, page: int = 1, limit: int = 15, sort: str = "-new_chap_at") -> List[Book]:
        """Fetches latest novels from the catalog."""
        url = f"{self.base_url}/books"
        params = {
            "page": page,
            "limit": limit,
            "include": "author,creator,genres",
            "sort": sort,
            "filter[state]": "published"
        }
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=15)
        data = resp.json().get("data", [])
        return [Book.from_dict(b) for b in data]

    def search_books(self, keyword: str, limit: int = 15) -> List[Book]:
        """Performs full-text title and keyword search across novels."""
        url = f"{self.base_url}/books"
        # Server requires limit >= 5
        limit = max(5, limit)
        params = {
            "filter[name]": keyword,
            "limit": limit,
            "include": "author,creator,genres"
        }
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", []) or []
        return [Book.from_dict(b) for b in data]

    def get_rankings(self, ranking_type: str = "views", limit: int = 15) -> List[Book]:
        """Fetches top novels sorted by popularity / views / votes."""
        sort_map = {
            "views": "-view_count",
            "likes": "-like_count",
            "votes": "-vote_count",
            "rating": "-review_score"
        }
        sort_key = sort_map.get(ranking_type, "-view_count")
        return self.get_catalog(page=1, limit=limit, sort=sort_key)

    def get_book_details(self, book_id: int) -> Tuple[Optional[Book], Dict[str, Any]]:
        """Retrieves detailed options and properties for a novel."""
        url = f"{self.base_url}/books/{book_id}"
        params = {"include": "author,creator,genres"}
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=15)
        book = None
        if resp.status_code == 200:
            b_data = resp.json().get("data", {})
            if b_data:
                book = Book.from_dict(b_data)

        # Options
        opt_url = f"{self.base_url}/books/options"
        opt_resp = self._session.get(opt_url, headers=self._get_headers(), params={"book_id": book_id}, timeout=15)
        options = opt_resp.json().get("data", {}) if opt_resp.status_code == 200 else {}
        return book, options

    def get_chapters(self, book_id: int, limit: int = 5000, page: int = 1) -> List[Chapter]:
        """Fetches chapter index list for a novel."""
        url = f"{self.base_url}/chapters"
        params = {
            "filter[book_id]": book_id,
            "limit": limit,
            "page": page
        }
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=20)
        data = resp.json().get("data", [])
        return [Chapter.from_dict(c) for c in data]

    def get_chapter_content(self, chapter_id: int, decrypt: bool = True) -> Chapter:
        """
        Fetches full chapter content. If encrypted, decrypts ciphertext using
        native AES-CBC decryption engine.
        """
        url = f"{self.base_url}/chapters/{chapter_id}"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        data = resp.json()
        if resp.status_code != 200 or not data.get("success"):
            raise ValueError(f"Failed to fetch chapter {chapter_id}: {data.get('message')}")

        chapter = Chapter.from_dict(data["data"])
        if decrypt and chapter.content:
            chapter.content = decrypt_chapter_content(chapter.content)
        return chapter

    def get_reviews(self, book_id: Optional[int] = None, limit: int = 10) -> List[NovelReview]:
        """Fetches reviews for a novel or globally."""
        url = f"{self.base_url}/reviews"
        limit = max(6, limit)
        params: Dict[str, Any] = {"limit": limit}
        if book_id:
            params["filter[book_id]"] = book_id
        resp = self._session.get(url, headers=self._get_headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", []) or []
        return [NovelReview.from_dict(r) for r in data]

    def post_review(self, book_id: int, content: str, score: str = "5.0") -> Tuple[bool, str]:
        """Submits a book review (requires content > 100 words and 1-decimal score)."""
        url = f"{self.base_url}/reviews"
        payload = {
            "book_id": book_id,
            "content": content,
            "average_score": score
        }
        resp = self._session.post(url, json=payload, headers=self._get_headers(), timeout=15)
        data = resp.json()
        return resp.status_code == 200, data.get("message", "")

    def post_comment(self, chapter_id: int, content: str) -> Tuple[bool, str]:
        """Posts a comment on a chapter."""
        url = f"{self.base_url}/comments"
        payload = {
            "object_id": chapter_id,
            "object_type": "Chapter",
            "content": content
        }
        resp = self._session.post(url, json=payload, headers=self._get_headers(), timeout=15)
        data = resp.json()
        return resp.status_code == 200, data.get("message", "")

    def sync_reading(self, book_id: int, chapter_id: int, index: int = 1) -> bool:
        """Synchronizes cloud reading position."""
        url = f"{self.base_url}/readings"
        payload = {"book_id": book_id, "chapter_id": chapter_id, "index": index}
        resp = self._session.post(url, json=payload, headers=self._get_headers(), timeout=15)
        return resp.status_code == 200

    def bookmark_chapter(self, book_id: int, chapter_id: int) -> bool:
        """Saves a chapter bookmark."""
        url = f"{self.base_url}/bookmarks"
        payload = {"book_id": book_id, "chapter_id": chapter_id}
        resp = self._session.post(url, json=payload, headers=self._get_headers(), timeout=15)
        return resp.status_code == 200

    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """Retrieves user's bookmarks list."""
        url = f"{self.base_url}/bookmarks"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get("data", [])

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Retrieves system and novel update notifications."""
        url = f"{self.base_url}/notifications"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get("data", [])

    def get_topboxes(self) -> List[Dict[str, Any]]:
        """Retrieves available reward topboxes."""
        url = f"{self.base_url}/topboxes"
        resp = self._session.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get("data", [])
