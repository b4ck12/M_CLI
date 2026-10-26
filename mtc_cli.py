"""
MTC CLI Application - Real Terminal TUI App
A sleek, full-screen terminal experience for MTC / NovelFever.
Supports search, catalog, rankings, chapter reading with AES decryption,
cloud sync, reviews, transactions, and .TXT book downloading.
Screen states transition cleanly without scrolling duplicate lines.
"""

import os
import sys
import json
import time
import argparse
from typing import Optional, Dict, Any, List

# UTF-8 encoding support on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.columns import Columns
from rich import box

from mtc_core.client import MTCClient
from mtc_core.downloader import BookDownloader
from mtc_core.models import Book, Chapter

console = Console()
SESSION_FILE = os.path.expanduser("~/.mtc_session.json")

def clear_screen():
    """Clears the console screen completely for in-place TUI state transitions."""
    console.clear()

def load_saved_session() -> Optional[Dict[str, Any]]:
    """Loads saved login session from disk if available."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_session(token: str, email: str, profile_name: str, user_id: int):
    """Persists session token to allow instant login without re-typing credentials."""
    try:
        data = {
            "token": token,
            "email": email,
            "name": profile_name,
            "user_id": user_id,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clear_session():
    """Removes saved session from disk."""
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

def render_header(client: MTCClient, screen_title: str = "BẢNG ĐIỀU KHIỂN"):
    """Renders a sleek persistent status & navigation header at the top of every screen."""
    p = client.user_profile
    if p:
        user_info = (
            f"[bold green]👤 {p.name}[/bold green] (ID: [cyan]{p.id}[/cyan])  |  "
            f"[yellow]🪙 Xu: {p.balance_default:,}[/yellow]  "
            f"[magenta]🍬 Kẹo: {p.balance_candy}[/magenta]  "
            f"[cyan]🔑 Khóa: {p.balance_key}[/cyan]  "
            f"[red]🗳️ Phiếu: {p.ballot}[/red]  "
            f"[bold yellow]⭐ Cấp {p.level}[/bold yellow]"
        )
    else:
        user_info = "[dim]👤 Chưa đăng nhập / Khách[/dim]"

    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right", ratio=1)
    grid.add_row(
        "[bold cyan]📚 MTC NOVELFEVER TERMINAL APP[/bold cyan] [dim]v2.0[/dim]",
        f"[bold bright_white]{screen_title}[/bold bright_white]"
    )
    grid.add_row(user_info, "[dim][0] hoặc [B] Quay lại menu[/dim]")

    panel = Panel(grid, box=box.ROUNDED, border_style="cyan", padding=(0, 1))
    console.print(panel)
    console.print()

def display_books_table(books: List[Book], title: str = "Danh Sách Truyện") -> Table:
    """Formats a responsive, clean table of novels."""
    table = Table(title=f"[bold yellow]{title}[/bold yellow]", box=box.ROUNDED, expand=True)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Tên Truyện", style="bold white", ratio=3)
    table.add_column("Tác Giả", style="magenta", ratio=2)
    table.add_column("Số Chương", style="green", justify="right", width=12)
    table.add_column("Lượt Xem", style="yellow", justify="right", width=12)
    table.add_column("Đánh Giá", style="bold red", justify="center", width=10)

    for idx, b in enumerate(books, 1):
        table.add_row(
            str(idx),
            str(b.id),
            b.name,
            b.author_name,
            f"{b.chap_count:,}",
            f"{b.view_count:,}",
            f"★ {b.review_score}"
        )
    return table

# ─────────────────────────────────────────────────────────────────────────────
# VIEW CONTROLLERS (Single-Screen TUI)
# ─────────────────────────────────────────────────────────────────────────────

def view_profile(client: MTCClient):
    """View 1: User Account Profile & Balances."""
    clear_screen()
    render_header(client, "HỒ SƠ TÀI KHOẢN & VÍ TIỀN")

    with console.status("[bold green]Đang làm mới thông tin tài khoản...[/bold green]"):
        try:
            p = client.get_profile()
        except Exception as e:
            console.print(f"[bold red]Lỗi khi tải hồ sơ: {e}[/bold red]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("Thông Tin Tài Khoản", style="bold cyan", width=25)
    table.add_column("Chi Tiết", style="bold bright_white")

    table.add_row("User ID", str(p.id))
    table.add_row("Tên Hiển Thị", p.name)
    table.add_row("Email", p.email)
    table.add_row("Số Điện Thoại", str(p.phone or "Chưa liên kết"))
    table.add_row("Cấp Độ (Level)", f"Cấp {p.level} (EXP: {p.exp:,})")
    table.add_row("Hạng VIP", f"VIP {p.vip_tier}")
    table.add_row("Số Dư Xu (balance_default)", f"[bold yellow]{p.balance_default:,} Xu[/bold yellow]")
    table.add_row("Số Dư Kẹo (balance_candy)", f"[magenta]{p.balance_candy:,} Kẹo[/magenta]")
    table.add_row("Chìa Khóa Vàng (balance_key)", f"[cyan]{p.balance_key} Khóa[/cyan]")
    table.add_row("Phiếu Đề Cử (ballot)", f"[red]{p.ballot} Phiếu[/red]")

    console.print(table)
    console.print()
    Prompt.ask("[dim]Nhấn [bold white]Enter[/bold white] để quay lại menu chính...[/dim]")

def view_catalog(client: MTCClient):
    """View 2: Latest Novels Catalog with interactive selection."""
    page = 1
    while True:
        clear_screen()
        render_header(client, f"DANH MỤC TRUYỆN MỚI CẬP NHẬT (Trang {page})")

        with console.status(f"[bold green]Đang tải danh mục trang {page}...[/bold green]"):
            try:
                books = client.get_catalog(page=page, limit=12)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi tải danh mục: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                return

        if not books:
            console.print("[yellow]Không có dữ liệu ở trang này.[/yellow]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

        console.print(display_books_table(books, title=f"Truyện Mới Cập Nhật - Trang {page}"))
        console.print()
        console.print("[cyan][ID][/cyan] Nhập ID truyện để xem chi tiết / đọc / tải  |  [cyan][N][/cyan] Trang sau  |  [cyan][P][/cyan] Trang trước  |  [cyan][0/B][/cyan] Quay lại")

        choice = Prompt.ask("[bold green]Thao tác[/bold green]", default="b").strip().lower()
        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "n":
            page += 1
        elif choice == "p":
            page = max(1, page - 1)
        elif choice.isdigit():
            view_book_detail(client, int(choice))

def view_search(client: MTCClient, keyword: Optional[str] = None):
    """View 3: Full-text Search novels."""
    while True:
        if not keyword:
            clear_screen()
            render_header(client, "TÌM KIẾM TRUYỆN")
            keyword = Prompt.ask("[bold cyan]Nhập tên truyện hoặc từ khóa tìm kiếm (hoặc [0] để quay lại)[/bold cyan]").strip()
            if keyword in ["0", "b", "q", ""]:
                break

        clear_screen()
        render_header(client, f"KẾT QUẢ TÌM KIẾM: '{keyword}'")

        with console.status(f"[bold green]Đang tìm kiếm '{keyword}'...[/bold green]"):
            try:
                books = client.search_books(keyword=keyword, limit=20)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi tìm kiếm: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                keyword = None
                continue

        if not books:
            console.print(f"[yellow]Không tìm thấy truyện nào khớp với từ khóa '{keyword}'.[/yellow]")
        else:
            console.print(display_books_table(books, title=f"Tìm Thấy {len(books)} Kết Quả Cho '{keyword}'"))

        console.print()
        console.print("[cyan][ID][/cyan] Nhập ID truyện để xem  |  [cyan][S][/cyan] Tìm từ khóa khác  |  [cyan][0/B][/cyan] Quay lại")
        choice = Prompt.ask("[bold green]Thao tác[/bold green]", default="b").strip().lower()

        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "s":
            keyword = None
        elif choice.isdigit():
            view_book_detail(client, int(choice))

def view_rankings(client: MTCClient):
    """View 4: Popularity Leaderboard with tabs."""
    ranking_type = "views"
    type_names = {
        "views": "Lượt Đọc (Views)",
        "likes": "Lượt Thích (Likes)",
        "votes": "Bình Chọn (Votes)",
        "rating": "Điểm Đánh Giá (Rating)"
    }

    while True:
        clear_screen()
        render_header(client, f"BẢNG XẾP HẠNG: {type_names.get(ranking_type, 'Top')}")

        with console.status("[bold green]Đang tải bảng xếp hạng...[/bold green]"):
            try:
                books = client.get_rankings(ranking_type=ranking_type, limit=15)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi tải bảng xếp hạng: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                return

        console.print(display_books_table(books, title=f"Bảng Xếp Hạng - {type_names.get(ranking_type)}"))
        console.print()
        console.print("[cyan][1][/cyan] Top Lượt Đọc  |  [cyan][2][/cyan] Top Yêu Thích  |  [cyan][3][/cyan] Top Bình Chọn  |  [cyan][4][/cyan] Top Đánh Giá")
        console.print("[cyan][ID][/cyan] Nhập ID truyện để xem chi tiết  |  [cyan][0/B][/cyan] Quay lại menu")

        choice = Prompt.ask("[bold green]Thao tác[/bold green]", default="b").strip().lower()
        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "1":
            ranking_type = "views"
        elif choice == "2":
            ranking_type = "likes"
        elif choice == "3":
            ranking_type = "votes"
        elif choice == "4":
            ranking_type = "rating"
        elif choice.isdigit():
            view_book_detail(client, int(choice))

def view_book_detail(client: MTCClient, book_id: int):
    """Displays rich overview of a single book with direct action options."""
    while True:
        clear_screen()
        render_header(client, f"CHI TIẾT TRUYỆN [ID: {book_id}]")

        with console.status(f"[bold green]Đang tải thông tin truyện {book_id}...[/bold green]"):
            try:
                book, options = client.get_book_details(book_id)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi tải truyện: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                return

        if not book:
            console.print(f"[bold red]Không tìm thấy truyện với ID {book_id}.[/bold red]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

        genres_str = ", ".join(book.genres) if book.genres else "Chưa phân loại"
        
        info_table = Table.grid(expand=True, padding=(0, 2))
        info_table.add_column(style="bold cyan", width=15)
        info_table.add_column(style="white")
        info_table.add_column(style="bold cyan", width=15)
        info_table.add_column(style="white")

        info_table.add_row("Tên Truyện:", f"[bold yellow]{book.name}[/bold yellow]", "Tác Giả:", f"[magenta]{book.author_name}[/magenta]")
        info_table.add_row("Thể Loại:", genres_str, "Tình Trạng:", book.status)
        info_table.add_row("Số Chương:", f"{book.chap_count:,} chương", "Lượt Xem:", f"{book.view_count:,}")
        info_table.add_row("Đánh Giá:", f"★ {book.review_score} ({book.vote_count:,} bình chọn)", "Lượt Thích:", f"{book.like_count:,}")

        console.print(Panel(info_table, title="[bold green]Thông Tin Tác Phẩm[/bold green]", box=box.ROUNDED))
        console.print()

        synopsis_clean = book.synopsis.strip() if book.synopsis else "Chưa có giới thiệu."
        console.print(Panel(synopsis_clean, title="[bold yellow]Giới Thiệu Nội Dung[/bold yellow]", box=box.ROUNDED, max_height=12))
        console.print()

        console.print("[bold yellow]THAO TÁC KHẢ DỤNG:[/bold yellow]")
        console.print("  [bold cyan]1[/bold cyan]. 📑 Xem danh sách chương")
        console.print("  [bold cyan]2[/bold cyan]. 📖 Đọc truyện (chọn chương)")
        console.print("  [bold cyan]3[/bold cyan]. 💾 Tải toàn bộ / một phần ra tệp .TXT")
        console.print("  [bold cyan]4[/bold cyan]. ⭐ Xem đánh giá độc giả")
        console.print("  [bold cyan]0 / B[/bold cyan]. 🔙 Quay lại")
        console.print()

        choice = Prompt.ask("[bold green]Lựa chọn[/bold green]", default="b").strip().lower()
        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "1":
            view_chapters(client, book_id=book.id)
        elif choice == "2":
            view_reader(client, book_id=book.id)
        elif choice == "3":
            view_download(client, book_id=book.id)
        elif choice == "4":
            view_reviews(client, book_id=book.id)

def view_chapters(client: MTCClient, book_id: Optional[int] = None):
    """View 5: Chapter Index Listing with pagination."""
    if not book_id:
        clear_screen()
        render_header(client, "DANH SÁCH CHƯƠNG")
        book_id_input = Prompt.ask("[bold cyan]Nhập ID truyện (hoặc [0] để quay lại)[/bold cyan]").strip()
        if book_id_input in ["0", "b", "q", ""]:
            return
        if not book_id_input.isdigit():
            return
        book_id = int(book_id_input)

    page = 1
    limit = 20
    while True:
        clear_screen()
        render_header(client, f"DANH SÁCH CHƯƠNG [Book ID: {book_id}] - Trang {page}")

        with console.status(f"[bold green]Đang tải danh sách chương trang {page}...[/bold green]"):
            try:
                chaps = client.get_chapters(book_id, limit=limit, page=page)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi tải chương: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                return

        if not chaps and page > 1:
            page -= 1
            continue

        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("STT", style="dim", width=6, justify="right")
        table.add_column("Chương #", style="cyan", width=12)
        table.add_column("Chapter ID", style="dim", width=14)
        table.add_column("Tên Chương", style="bold bright_white")

        for idx, c in enumerate(chaps, 1 + (page - 1) * limit):
            table.add_row(str(idx), f"Chương {c.index}", str(c.id), c.name)

        console.print(table)
        console.print()
        console.print("[cyan][ID][/cyan] Nhập Chapter ID để đọc  |  [cyan][N][/cyan] Trang sau  |  [cyan][P][/cyan] Trang trước  |  [cyan][0/B][/cyan] Quay lại")

        choice = Prompt.ask("[bold green]Thao tác[/bold green]", default="b").strip().lower()
        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "n":
            page += 1
        elif choice == "p":
            page = max(1, page - 1)
        elif choice.isdigit():
            view_reader(client, chapter_id=int(choice))

def view_reader(client: MTCClient, book_id: Optional[int] = None, chapter_id: Optional[int] = None):
    """View 6: Decrypted AES Reading Pane with Next/Prev navigation."""
    if not chapter_id:
        if book_id:
            chaps = client.get_chapters(book_id, limit=1)
            if chaps:
                chapter_id = chaps[0].id
        if not chapter_id:
            clear_screen()
            render_header(client, "ĐỌC TRUYỆN")
            c_input = Prompt.ask("[bold cyan]Nhập Chapter ID cần đọc (hoặc [0] để quay lại)[/bold cyan]").strip()
            if c_input in ["0", "b", "q", ""]:
                return
            if not c_input.isdigit():
                return
            chapter_id = int(c_input)

    current_id = chapter_id
    while True:
        clear_screen()
        render_header(client, f"ĐỌC TRUYỆN [Chapter ID: {current_id}]")

        with console.status(f"[bold green]Đang tải & giải mã AES chương {current_id}...[/bold green]"):
            try:
                chap = client.get_chapter_content(current_id, decrypt=True)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi đọc chương: {e}[/bold red]")
                Prompt.ask("\nNhấn [Enter] để quay lại...")
                return

        # Cloud sync reading position
        try:
            client.sync_reading(chap.book_id, chap.id, chap.index)
        except Exception:
            pass

        # Text reader container
        title_bar = f"[bold green]{chap.name}[/bold green]"
        footer_bar = f"[dim]Chương {chap.index} | Độ dài: {len(chap.content):,} ký tự | ID: {chap.id}[/dim]"
        
        # Display content in clean bounded panel
        console.print(Panel(
            chap.content,
            title=title_bar,
            subtitle=footer_bar,
            box=box.ROUNDED,
            padding=(1, 2)
        ))
        console.print()
        console.print("[cyan][N][/cyan] Chương kế tiếp  |  [cyan][P][/cyan] Chương trước  |  [cyan][0/B][/cyan] Quay lại")

        choice = Prompt.ask("[bold green]Thao tác[/bold green]", default="b").strip().lower()
        if choice in ["0", "b", "q", ""]:
            break
        elif choice == "n":
            # Fetch next chapter
            try:
                all_c = client.get_chapters(chap.book_id, limit=50)
                next_ones = [c for c in all_c if c.index > chap.index]
                if next_ones:
                    current_id = next_ones[0].id
                else:
                    console.print("[yellow]Đã đến chương mới nhất![/yellow]")
                    time.sleep(1)
            except Exception:
                pass
        elif choice == "p":
            try:
                all_c = client.get_chapters(chap.book_id, limit=50)
                prev_ones = [c for c in all_c if c.index < chap.index]
                if prev_ones:
                    current_id = prev_ones[-1].id
                else:
                    console.print("[yellow]Đây là chương đầu tiên![/yellow]")
                    time.sleep(1)
            except Exception:
                pass

def view_download(client: MTCClient, book_id: Optional[int] = None):
    """View 7: Bulk Novel TXT Downloader."""
    clear_screen()
    render_header(client, "TẢI TRUYỆN XUỐNG .TXT")

    if not book_id:
        bid_str = Prompt.ask("[bold cyan]Nhập ID truyện cần tải xuống (hoặc [0] để quay lại)[/bold cyan]").strip()
        if bid_str in ["0", "b", "q", ""]:
            return
        if not bid_str.isdigit():
            return
        book_id = int(bid_str)

    # Fetch book info
    with console.status(f"[bold green]Đang kiểm tra thông tin truyện {book_id}...[/bold green]"):
        try:
            book, _ = client.get_book_details(book_id)
            chaps = client.get_chapters(book_id, limit=5)
        except Exception as e:
            console.print(f"[bold red]Lỗi khi truy vấn truyện: {e}[/bold red]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

    b_title = book.name if book else f"Book_{book_id}"
    console.print(f"[bold yellow]Truyện:[/bold yellow] [bold bright_white]{b_title}[/bold bright_white]")
    if book:
        console.print(f"[bold yellow]Tổng số chương:[/bold yellow] [cyan]{book.chap_count:,} chương[/cyan]")
    console.print()

    start_c_str = Prompt.ask("[cyan]Chương bắt đầu[/cyan]", default="1").strip()
    start_c = int(start_c_str) if start_c_str.isdigit() else 1

    count_str = Prompt.ask("[cyan]Số chương muốn tải (Nhập số lượng, hoặc 'all')[/cyan]", default="5").strip()
    max_c = None if count_str.lower() == "all" else (int(count_str) if count_str.isdigit() else 5)

    downloader = BookDownloader(client=client, output_dir="downloads")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Đang tải và giải mã các chương...", total=100)

        def update_progress(done, total, chap_name):
            progress.update(task, completed=done, total=total, description=f"[cyan]{chap_name[:35]}[/cyan]")

        try:
            filepath = downloader.download_book_as_txt(
                book_id=book_id,
                start_chapter=start_c,
                max_chapters=max_c,
                max_workers=5,
                progress_callback=update_progress
            )
            console.print()
            console.print(Panel(
                f"[bold green]✓ TẢI XUỐNG HOÀN TẤT THÀNH CÔNG![/bold green]\n\n"
                f"📁 Đường dẫn tệp: [bold yellow]{filepath}[/bold yellow]\n"
                f"📦 Dung lượng:   [cyan]{os.path.getsize(filepath):,} bytes[/cyan]\n"
                f"📝 Định dạng:    [white]UTF-8 Plain Text (Sạch không mục lục, đủ thông tin)[/white]",
                box=box.ROUNDED,
                title="[bold green]Kết Quả Tải Về[/bold green]"
            ))
        except Exception as e:
            console.print(f"\n[bold red]Lỗi trong quá trình tải truyện: {e}[/bold red]")

    console.print()
    Prompt.ask("[dim]Nhấn [bold white]Enter[/bold white] để quay lại menu chính...[/dim]")

def view_reviews(client: MTCClient, book_id: Optional[int] = None):
    """View 8: Reader Reviews Listing."""
    clear_screen()
    title = f"ĐÁNH GIÁ ĐỘC GIẢ [Book ID: {book_id}]" if book_id else "ĐÁNH GIÁ ĐỘC GIẢ TOÀN HỆ THỐNG"
    render_header(client, title)

    with console.status("[bold green]Đang tải đánh giá độc giả...[/bold green]"):
        try:
            reviews = client.get_reviews(book_id=book_id, limit=10)
        except Exception as e:
            console.print(f"[bold red]Lỗi khi tải đánh giá: {e}[/bold red]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

    if not reviews:
        console.print("[yellow]Chưa có bài nhận xét hoặc đánh giá nào.[/yellow]")
    else:
        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Độc Giả", style="bold cyan", width=18)
        table.add_column("Điểm", style="bold yellow", width=8, justify="center")
        table.add_column("Nội Dung Nhận Xét", style="white")

        for rv in reviews:
            table.add_row(
                rv.user_name,
                f"★ {rv.score}",
                rv.content[:160] + ("..." if len(rv.content) > 160 else "")
            )
        console.print(table)

    console.print()
    Prompt.ask("[dim]Nhấn [bold white]Enter[/bold white] để quay lại...[/dim]")

def view_transactions(client: MTCClient):
    """View 9: Wallet Transactions History."""
    clear_screen()
    render_header(client, "LỊCH SỬ GIAO DỊCH VÍ TIỀN")

    with console.status("[bold green]Đang tải sao kê giao dịch...[/bold green]"):
        try:
            txs = client.get_transactions()
        except Exception as e:
            console.print(f"[bold red]Lỗi khi tải giao dịch: {e}[/bold red]")
            Prompt.ask("\nNhấn [Enter] để quay lại...")
            return

    if not txs:
        console.print("[yellow]Không có bản ghi giao dịch nào.[/yellow]")
    else:
        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Mã GD", style="dim", width=10)
        table.add_column("Loại Ví", style="bold cyan", width=15)
        table.add_column("Biến Động", style="bold green", width=15, justify="right")
        table.add_column("Thời Gian", style="dim", width=20)
        table.add_column("Mô Tả Giao Dịch", style="white")

        for t in txs[:15]:
            amt = str(t.get("amount", "0"))
            amt_str = f"+{amt}" if not amt.startswith("-") else amt
            table.add_row(
                str(t.get("id")),
                str(t.get("wallet", "Xu")),
                amt_str,
                str(t.get("created_at", "")),
                str(t.get("description", ""))
            )
        console.print(table)

    console.print()
    Prompt.ask("[dim]Nhấn [bold white]Enter[/bold white] để quay lại menu chính...[/dim]")

def view_switch_account(client: MTCClient):
    """View 10: Switch Account or Log Out."""
    clear_screen()
    render_header(client, "ĐĂNG XUẤT / ĐỔI TÀI KHOẢN")

    confirm = Prompt.ask("[bold yellow]Bạn có chắc chắn muốn đăng xuất tài khoản hiện tại? (y/n)[/bold yellow]", default="n")
    if confirm.lower() != "y":
        return

    try:
        client.logout()
    except Exception:
        pass
    clear_session()
    console.print("[bold green]✓ Đã đăng xuất và xóa phiên lưu trữ thành công.[/bold green]\n")

    # Prompt new login
    new_profile = authenticate_user(client, allow_saved=False)
    if new_profile:
        console.print(f"[bold green]✓ Đăng nhập tài khoản mới thành công:[/bold green] [bold cyan]{new_profile.name}[/bold cyan] (ID: {new_profile.id})")
        time.sleep(1.2)

# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def authenticate_user(
    client: MTCClient,
    email: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
    allow_saved: bool = True
) -> Optional[Any]:
    """Authenticates any MTC account using CLI flags, env vars, saved session, or interactive prompt."""
    # 1. Direct Token
    if token:
        try:
            with console.status("[bold green]Đang xác thực bằng Token...[/bold green]"):
                profile = client.login_with_token(token)
                save_session(token, profile.email, profile.name, profile.id)
                return profile
        except Exception as e:
            console.print(f"[bold red]Token không hợp lệ hoặc đã hết hạn: {e}[/bold red]")

    # 2. Direct Email & Password passed via args
    if email and password:
        try:
            with console.status(f"[bold green]Đang kết nối & đăng nhập ({email})...[/bold green]"):
                profile = client.login(email, password)
                save_session(client.token, email, profile.name, profile.id)
                return profile
        except Exception as e:
            console.print(f"[bold red]Đăng nhập thất bại: {e}[/bold red]")
            return None

    # 3. Environment Variables
    env_token = os.environ.get("MTC_TOKEN")
    if env_token:
        try:
            profile = client.login_with_token(env_token)
            return profile
        except Exception:
            pass

    env_email = os.environ.get("MTC_EMAIL")
    env_pass = os.environ.get("MTC_PASSWORD")
    if env_email and env_pass:
        try:
            with console.status(f"[bold green]Đang đăng nhập bằng biến môi trường ({env_email})...[/bold green]"):
                profile = client.login(env_email, env_pass)
                save_session(client.token, env_email, profile.name, profile.id)
                return profile
        except Exception:
            pass

    # 4. Saved Session File
    if allow_saved:
        saved = load_saved_session()
        if saved and saved.get("token"):
            try:
                with console.status(f"[bold green]Đang khôi phục phiên của '{saved.get('name', 'User')}'...[/bold green]"):
                    profile = client.login_with_token(saved["token"])
                    return profile
            except Exception:
                clear_session()
                console.print("[yellow]Phiên đăng nhập đã lưu bị hết hạn. Vui lòng đăng nhập lại.[/yellow]")

    # 5. Interactive Prompt
    clear_screen()
    console.print("\n[bold cyan]╔═══════════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]      [bold bright_white]MTC NOVELFEVER TERMINAL APP - ĐĂNG NHẬP HỆ THỐNG[/bold bright_white]         [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]╚═══════════════════════════════════════════════════════════════╝[/bold cyan]\n")

    while True:
        inp_email = Prompt.ask("[bold cyan]Email tài khoản[/bold cyan]").strip()
        if not inp_email:
            console.print("[red]Email không được để trống.[/red]")
            continue
        inp_pass = Prompt.ask("[bold cyan]Mật khẩu[/bold cyan]", password=True).strip()
        if not inp_pass:
            console.print("[red]Mật khẩu không được để trống.[/red]")
            continue

        try:
            with console.status(f"[bold green]Đang kết nối & xác thực ({inp_email})...[/bold green]"):
                profile = client.login(inp_email, inp_pass)

            save_ans = Prompt.ask("Bạn có muốn lưu phiên đăng nhập cho lần sau?", choices=["y", "n"], default="y")
            if save_ans.lower() == "y":
                save_session(client.token, inp_email, profile.name, profile.id)
            return profile
        except Exception as e:
            console.print(f"[bold red]Đăng nhập thất bại: {e}[/bold red]")
            retry = Prompt.ask("Thử lại?", choices=["y", "n"], default="y")
            if retry.lower() != "y":
                return None

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TUI LOOP
# ─────────────────────────────────────────────────────────────────────────────

def render_main_dashboard(client: MTCClient):
    """Draws the clean dashboard menu without scrolling duplicate lines."""
    clear_screen()
    render_header(client, "BẢNG ĐIỀU KHIỂN CHÍNH")

    # Column 1: Reading & Discovery
    col1_content = (
        "[bold cyan][1][/bold cyan]  👤 [bold white]Hồ sơ tài khoản & Số dư ví[/bold white]\n"
        "[bold cyan][2][/bold cyan]  📚 [bold white]Danh mục truyện mới nhất[/bold white]\n"
        "[bold cyan][3][/bold cyan]  🔍 [bold white]Tìm kiếm truyện theo từ khóa[/bold white]\n"
        "[bold cyan][4][/bold cyan]  🏆 [bold white]Bảng xếp hạng lượt đọc[/bold white]\n"
        "[bold cyan][5][/bold cyan]  📑 [bold white]Xem danh sách chương truyện[/bold white]"
    )
    panel1 = Panel(col1_content, title="[bold yellow]📖 Khám Phá & Đọc Truyện[/bold yellow]", box=box.ROUNDED, expand=True)

    # Column 2: Tools & Management
    col2_content = (
        "[bold cyan][6][/bold cyan]  📖 [bold white]Đọc nội dung chương (giải mã)[/bold white]\n"
        "[bold cyan][7][/bold cyan]  💾 [bold white]Tải trọn bộ / số chương (.TXT)[/bold white]\n"
        "[bold cyan][8][/bold cyan]  ⭐ [bold white]Xem nhận xét & đánh giá[/bold white]\n"
        "[bold cyan][9][/bold cyan]  💳 [bold white]Lịch sử biến động ví tiền[/bold white]\n"
        "[bold cyan][10][/bold cyan] 🔄 [bold white]Đổi tài khoản / Đăng xuất[/bold white]"
    )
    panel2 = Panel(col2_content, title="[bold green]⚙️ Tiện Ích & Quản Lý[/bold green]", box=box.ROUNDED, expand=True)

    columns = Columns([panel1, panel2], expand=True)
    console.print(columns)
    console.print()
    console.print(Panel("[bold red][0] Thoát ứng dụng[/bold red]", box=box.ROUNDED, style="dim"))

def main():
    parser = argparse.ArgumentParser(description="MTC NovelFever Terminal Client - Read & Download Novels")
    parser.add_argument("--email", "-e", help="User login email (accepts any MTC account)")
    parser.add_argument("--password", "-p", help="User login password")
    parser.add_argument("--token", "-t", help="Direct Laravel Sanctum bearer token")
    parser.add_argument("--logout", action="store_true", help="Log out and clear saved login session")
    parser.add_argument("--search", "-s", help="Quick search query")
    parser.add_argument("--download", "-d", type=int, help="Download book by ID")
    parser.add_argument("--max-chapters", type=int, default=None, help="Max chapters to download")
    parser.add_argument("--read", "-r", type=int, help="Read chapter content by ID")
    parser.add_argument("--rankings", action="store_true", help="View leaderboard rankings")
    args = parser.parse_args()

    if args.logout:
        clear_session()
        console.print("[bold green]✓ Đã đăng xuất và xóa phiên lưu trữ thành công.[/bold green]")
        return

    client = MTCClient()

    # Authenticate (CLI flags > Env vars > Saved session > Interactive prompt)
    profile = authenticate_user(
        client=client,
        email=args.email,
        password=args.password,
        token=args.token
    )

    if not profile:
        console.print("[bold red]Không thể xác thực tài khoản. Thoát ứng dụng.[/bold red]")
        sys.exit(1)

    # CLI Direct Flags Mode (Non-interactive execution for scripts/tests)
    if args.search:
        books = client.search_books(keyword=args.search, limit=20)
        console.print(display_books_table(books, title=f"Kết Quả Tìm Kiếm: '{args.search}'"))
        return
    if args.read:
        chap = client.get_chapter_content(args.read, decrypt=True)
        console.print(Panel(chap.content[:3000], title=f"[bold green]{chap.name}[/bold green]", box=box.ROUNDED))
        return
    if args.download:
        downloader = BookDownloader(client=client, output_dir="downloads")
        filepath = downloader.download_book_as_txt(book_id=args.download, max_chapters=args.max_chapters)
        console.print(f"[bold green]✓ Tải thành công:[/bold green] {filepath}")
        return
    if args.rankings:
        rankings = client.get_rankings(ranking_type="views", limit=15)
        console.print(display_books_table(rankings, title="Bảng Xếp Hạng Lượt Đọc"))
        return

    # Interactive TUI Loop (Clean single-screen in-place transitions)
    while True:
        render_main_dashboard(client)
        choice = Prompt.ask(
            "[bold green]Lựa chọn [0-10][/bold green]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            default="2"
        ).strip()

        if choice == "0":
            clear_screen()
            console.print("[bold cyan]Cảm ơn bạn đã sử dụng MTC NovelFever Terminal App. Tạm biệt![/bold cyan]")
            break
        elif choice == "1":
            view_profile(client)
        elif choice == "2":
            view_catalog(client)
        elif choice == "3":
            view_search(client)
        elif choice == "4":
            view_rankings(client)
        elif choice == "5":
            view_chapters(client)
        elif choice == "6":
            view_reader(client)
        elif choice == "7":
            view_download(client)
        elif choice == "8":
            view_reviews(client)
        elif choice == "9":
            view_transactions(client)
        elif choice == "10":
            view_switch_account(client)

if __name__ == "__main__":
    main()
