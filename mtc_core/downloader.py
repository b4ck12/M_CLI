"""
MTC Novel Downloader Engine
Downloads chapters in concurrent batches, decrypts AES ciphertext,
and compiles clean .txt files with comprehensive metadata, table of contents, and chapters.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, List
from .client import MTCClient
from .models import Book, Chapter

def sanitize_filename(name: str) -> str:
    """
    Removes invalid filesystem characters, normalizes multiple spaces,
    and formats colons cleanly as ' - '.
    """
    s = name.replace(":", " - ")
    s = re.sub(r'[\\/*?:"<>|]', "", s)
    s = re.sub(r'\s+', ' ', s).strip(" .-_")
    return s if s else "novel"

class BookDownloader:
    def __init__(self, client: MTCClient, output_dir: str = "downloads"):
        self.client = client
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def download_book_as_txt(
        self,
        book_id: int,
        start_chapter: int = 1,
        max_chapters: Optional[int] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        """
        Downloads novel chapters, decrypts them to plaintext, and writes a single .txt book file.
        Returns the absolute path of the generated .txt file.
        """
        # 1. Fetch all chapters
        all_chaps = self.client.get_chapters(book_id=book_id, limit=50000)
        if not all_chaps:
            raise ValueError(f"No chapters found for Book ID {book_id}")

        # 2. Filter chapter range
        selected_chaps = [c for c in all_chaps if c.index >= start_chapter]
        if max_chapters is not None:
            selected_chaps = selected_chaps[:max_chapters]

        total_to_download = len(selected_chaps)
        if total_to_download == 0:
            raise ValueError("No chapters matched the requested range")

        start_idx = selected_chaps[0].index
        end_idx = selected_chaps[-1].index

        # 3. Fetch Book info for title and metadata
        book, _ = self.client.get_book_details(book_id)
        raw_title = book.name if book else f"Book_{book_id}"
        book_title = re.sub(r'\s+', ' ', raw_title).strip()

        raw_author = book.author_name if book and book.author_name else "Chưa rõ tác giả"
        author_name = re.sub(r'\s+', ' ', raw_author).strip()

        genres_str = ", ".join(book.genres) if book and book.genres else "Chưa phân loại"
        status_str = getattr(book, "status", "Đang ra")
        synopsis = book.synopsis.strip() if book and book.synopsis else "Không có giới thiệu."

        safe_title = sanitize_filename(book_title)
        out_filepath = os.path.join(self.output_dir, f"{safe_title}.txt")

        # Download chapters concurrently with retry support
        downloaded_contents = {}

        def _fetch_one(chap: Chapter):
            clean_chap_name = re.sub(r'\s+', ' ', chap.name).strip()
            for attempt in range(3):
                try:
                    time.sleep(0.06)
                    full_chap = self.client.get_chapter_content(chap.id, decrypt=True)
                    return chap.index, clean_chap_name, full_chap.content
                except Exception as e:
                    if attempt == 2:
                        return chap.index, clean_chap_name, f"[Lỗi tải chương {chap.index}: {str(e)}]"
                    time.sleep(0.4 * (attempt + 1))

        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_fetch_one, c): c for c in selected_chaps}
            for future in as_completed(future_map):
                idx, name, text = future.result()
                downloaded_contents[idx] = (name, text)
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, total_to_download, name)

        # Write clean combined TXT file with rich metadata
        with open(out_filepath, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"TÊN TRUYỆN:  {book_title}\n")
            f.write(f"TÁC GIẢ:     {author_name}\n")
            f.write(f"THỂ LOẠI:    {genres_str}\n")
            f.write(f"TÌNH TRẠNG:  {status_str}\n")
            f.write(f"NGUỒN:       MTC / NovelFever (android.lonoapp.net)\n")
            f.write(f"SỐ CHƯƠNG:   {total_to_download} chương (Chương {start_idx} -> Chương {end_idx})\n")
            f.write(f"NGÀY TẢI:    {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            # Book Synopsis
            f.write("GIỚI THIỆU TÁC PHẨM:\n")
            f.write("-" * 50 + "\n")
            for s_line in synopsis.split("\n"):
                clean_s = re.sub(r'[ \t]+', ' ', s_line).strip()
                if clean_s:
                    f.write(clean_s + "\n")
            f.write("-" * 50 + "\n")

            # Chapters content
            for idx in sorted(downloaded_contents.keys()):
                name, text = downloaded_contents[idx]
                f.write("\n\n" + "-" * 50 + "\n")
                f.write(f"{name.upper()}\n")
                f.write("-" * 50 + "\n\n")
                f.write(text.strip() + "\n")

        return out_filepath
