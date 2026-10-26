import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class UserProfile:
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    balance_default: int = 0
    balance_candy: int = 0
    balance_key: int = 0
    ballot: int = 0
    level: int = 1
    exp: int = 0
    vip_tier: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        user = data.get("user", data)
        return cls(
            id=user.get("id", 0),
            name=user.get("name", "Unknown"),
            email=user.get("email", ""),
            phone=user.get("phone"),
            balance_default=user.get("balance_default", 0),
            balance_candy=user.get("balance_candy", 0),
            balance_key=user.get("balance_key", 0),
            ballot=user.get("ballot", 0),
            level=user.get("level", 1),
            exp=user.get("exp", 0),
            vip_tier=user.get("rank", 0)
        )

@dataclass
class Book:
    id: int
    name: str
    slug: str
    author_name: str
    status: str = "Đang ra"
    synopsis: str = ""
    view_count: int = 0
    like_count: int = 0
    vote_count: int = 0
    chap_count: int = 0
    review_score: str = "5.0"
    genres: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Book":
        author = data.get("author")
        if isinstance(author, dict):
            a_name = author.get("name") or author.get("local_name") or "Chưa rõ"
        elif isinstance(author, str) and author.strip():
            a_name = author.strip()
        else:
            a_name = data.get("author_name") or "Chưa rõ"

        raw_name = data.get("name", "Unknown")
        clean_name = re.sub(r'\s+', ' ', str(raw_name)).strip()

        genres_list = []
        if "genres" in data and isinstance(data["genres"], list):
            for g in data["genres"]:
                if isinstance(g, dict) and "name" in g:
                    genres_list.append(g["name"].strip())
                elif isinstance(g, str):
                    genres_list.append(g.strip())

        status_text = data.get("status_name") or data.get("status") or "Đang ra"

        return cls(
            id=data.get("id", 0),
            name=clean_name,
            slug=data.get("slug", ""),
            author_name=re.sub(r'\s+', ' ', a_name).strip(),
            status=str(status_text),
            synopsis=data.get("synopsis", "") or "",
            view_count=data.get("view_count", 0) or 0,
            like_count=data.get("like_count", 0) or 0,
            vote_count=data.get("vote_count", 0) or 0,
            chap_count=data.get("chapter_count") or data.get("chap_count", 0) or 0,
            review_score=str(data.get("review_score", "5.0")),
            genres=genres_list
        )

@dataclass
class Chapter:
    id: int
    name: str
    slug: str = ""
    index: int = 0
    book_id: int = 0
    lock_type: Optional[int] = None
    unlock_price: int = 0
    content: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chapter":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", f"Chương {data.get('index', '')}"),
            slug=data.get("slug", ""),
            index=data.get("index", 0),
            book_id=data.get("book_id", 0),
            lock_type=data.get("lockType"),
            unlock_price=data.get("unlockPrice", 0),
            content=data.get("content", "")
        )

@dataclass
class NovelReview:
    id: int
    user_name: str
    score: str
    content: str
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovelReview":
        u = data.get("user")
        uname = u.get("name") if isinstance(u, dict) else "Reader"
        return cls(
            id=data.get("id", 0),
            user_name=uname or "Reader",
            score=str(data.get("score") or data.get("average_score", "5.0")),
            content=data.get("content", ""),
            created_at=data.get("created_at", "")
        )
