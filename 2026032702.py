import time
from pathlib import Path
from urllib.parse import urljoin, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======== Config ========

BASE_URLS = [
    "http://twins.ee.nctu.edu.tw/courses/embedlab_09/http://twins.ee.nctu.edu.tw/courses/embedlab_09/Labs/AndeShape%20Labs_AG101/Lab10-MP3/",
    # "http://twins.ee.nctu.edu.tw/courses/Comm06_I/",
    # "https://nthuee.org/archive/",
]

SAVE_DIR = Path(r"C:\Users\linga\Downloads\nctu")

ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls",
                ".xlsx", ".txt", ".v", ".png", ".jpg", ".jpeg",
                ".htm", ".html", ".rar", ".zip", ".exe", ".xml",
                ".thmx", ".cnf", ".btr", ".lck", ".ico", ".ini",
                ".m", ".gif", ".bmp", ".wmf", ".sh", ".tgz", ".gz",
                ".tar"}

SKIP_DIR_KEYWORDS = {
    "/_vti_cnf/",
    "/_vti_pvt/",
    "/_private/",
}

MAX_DOWNLOAD_ATTEMPTS = 5
CHUNK_SIZE = 1024 * 1024  # 1 MB

# ======== Runtime State ========

visited_pages = set()
processed_file_urls = set()

stats = {
    "download_success": 0,
    "skip_existing": 0,
    "restart_after_416_success": 0,
    "skip_query_page": 0,
    "skip_non_target": 0,
    "skip_outside_root": 0,
    "skip_duplicate_file_url": 0,
    "page_success": 0,
    "page_failed": 0,
}

failure_stats = {
    "local_path_is_directory": [],
    "parent_path_conflict": [],
    "resume_416_restart_failed": [],
    "request_failed": [],
    "page_failed": [],
}

failure_labels = {
    "local_path_is_directory": "本地目標路徑其實是資料夾",
    "parent_path_conflict": "父層路徑被同名檔案卡住",
    "resume_416_restart_failed": "續傳 416 後重抓仍失敗",
    "request_failed": "一般下載重試後仍失敗",
    "page_failed": "頁面抓取失敗",
}

# ======== Session ========

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

retry_strategy = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ======== Helpers ========

def record_failure(category: str, url: str, detail: str = ""):
    failure_stats.setdefault(category, []).append({
        "url": url,
        "detail": detail,
    })


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    return f"{scheme}://{parsed.netloc}{parsed.path}" + (f"?{parsed.query}" if parsed.query else "")


def page_key_from_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    return f"{scheme}://{parsed.netloc}{parsed.path}"


def should_skip_href(href: str) -> bool:
    if not href:
        return True
    if href in ("../", "/"):
        return True
    if href.startswith("#"):
        return True
    return False


def should_skip_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.query in {
        "C=N;O=D", "C=M;O=A", "C=S;O=A", "C=D;O=A",
        "C=N;O=A", "C=M;O=D", "C=S;O=D", "C=D;O=D",
    }:
        return True

    path = parsed.path.lower()
    if any(keyword in path for keyword in SKIP_DIR_KEYWORDS):
        return True

    return False


def is_directory_link(href: str) -> bool:
    return href.endswith("/") and href not in ("../", "/")


def has_allowed_extension(url: str) -> bool:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    suffix = Path(path).suffix.lower()
    return suffix in ALLOWED_EXTS


def local_path_from_url(url: str) -> Path:
    parsed = urlparse(url)
    rel_path = unquote(parsed.path.lstrip("/"))

    if rel_path.startswith("archive/"):
        rel_path = rel_path[len("archive/"):]

    return SAVE_DIR / rel_path


def ensure_parent_dir(local_path: Path) -> bool:
    parent = local_path.parent

    if parent.exists() and not parent.is_dir():
        print(f"[Skip] Parent exists as file, not directory: {parent}")
        return False

    parent.mkdir(parents=True, exist_ok=True)
    return True


def remote_size(url: str):
    try:
        r = session.head(url, allow_redirects=True, timeout=(15, 30))
        r.raise_for_status()
        content_length = r.headers.get("Content-Length")
        if content_length and content_length.isdigit():
            return int(content_length)
        return None
    except requests.RequestException:
        return None


# ======== Download ========

def download_file(file_url: str, max_attempts: int = MAX_DOWNLOAD_ATTEMPTS):
    file_url = normalize_url(file_url)

    if file_url in processed_file_urls:
        stats["skip_duplicate_file_url"] += 1
        return
    processed_file_urls.add(file_url)

    if should_skip_url(file_url):
        print(f"[Skip query page] {file_url}")
        stats["skip_query_page"] += 1
        return

    if not has_allowed_extension(file_url):
        print(f"[Skip non-target] {file_url}")
        stats["skip_non_target"] += 1
        return

    local_path = local_path_from_url(file_url)

    if local_path.exists() and local_path.is_dir():
        print(f"[Skip] Local path is a directory, cannot write file: {local_path}")
        record_failure("local_path_is_directory", file_url, str(local_path))
        return

    if not ensure_parent_dir(local_path):
        record_failure("parent_path_conflict", file_url, str(local_path.parent))
        return

    remote = remote_size(file_url)
    existing_size = local_path.stat().st_size if local_path.exists() else 0

    if remote is not None and existing_size > 0 and existing_size == remote:
        print(f"[Skip existing] {file_url}")
        stats["skip_existing"] += 1
        return

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            existing_size = local_path.stat().st_size if local_path.exists() else 0
            headers = {}

            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                print(f"[Resume] {file_url} from {existing_size} bytes")
            else:
                print(f"[Download] {file_url}")

            with session.get(file_url, stream=True, timeout=(15, 60), headers=headers) as r:
                if r.status_code == 416:
                    print(f"[416] Range invalid, restarting: {file_url}")
                    try:
                        if local_path.exists():
                            local_path.unlink()

                        with session.get(file_url, stream=True, timeout=(15, 60)) as r2:
                            r2.raise_for_status()
                            with open(local_path, "wb") as f:
                                for chunk in r2.iter_content(chunk_size=CHUNK_SIZE):
                                    if chunk:
                                        f.write(chunk)

                        stats["restart_after_416_success"] += 1
                        return

                    except requests.exceptions.RequestException as e2:
                        print(f"[416 Restart Failed] {file_url}")
                        print(f"  Error: {e2}")
                        record_failure("resume_416_restart_failed", file_url, repr(e2))
                        return

                if r.status_code not in (200, 206):
                    r.raise_for_status()

                mode = "ab" if (existing_size > 0 and r.status_code == 206) else "wb"

                if mode == "wb" and existing_size > 0:
                    print(f"[Restart] Server does not support resume, restarting: {file_url}")

                with open(local_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)

            stats["download_success"] += 1
            return

        except requests.exceptions.RequestException as e:
            print(f"[Retry {attempt}/{max_attempts}] {file_url}")
            print(f"  Error: {e}")
            time.sleep(2 * attempt)

    print(f"[Failed] {file_url}")
    record_failure("request_failed", file_url, f"failed after {max_attempts} attempts")


# ======== Crawl ========

def crawl(url: str, root_url: str):
    url = normalize_url(url)
    root_url = normalize_url(root_url)

    if should_skip_url(url):
        print(f"[Skip query page] {url}")
        stats["skip_query_page"] += 1
        return

    key = page_key_from_url(url)

    if key in visited_pages:
        return
    visited_pages.add(key)

    print(f"[Crawl] {key}")
    try:
        r = session.get(key, timeout=(15, 60))
        r.raise_for_status()
        r.encoding = "utf-8"
        stats["page_success"] += 1
    except requests.exceptions.RequestException as e:
        print(f"[Page Failed] {key}")
        print(f"  Error: {e}")
        stats["page_failed"] += 1
        record_failure("page_failed", key, repr(e))
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if should_skip_href(href):
            continue

        full_url = normalize_url(urljoin(key, href))

        if not full_url.startswith(root_url):
            stats["skip_outside_root"] += 1
            continue

        if should_skip_url(full_url):
            print(f"[Skip query page] {full_url}")
            stats["skip_query_page"] += 1
            continue

        if is_directory_link(href):
            crawl(full_url, root_url)
        elif has_allowed_extension(full_url):
            download_file(full_url)
        else:
            print(f"[Skip non-target] {full_url}")
            stats["skip_non_target"] += 1


# ======== Report ========

def write_failure_report():
    failure_log = SAVE_DIR / "failure_report.txt"
    total_failures = sum(len(v) for v in failure_stats.values())

    with open(failure_log, "w", encoding="utf-8") as f:
        f.write("Download Failure Report\n")
        f.write("=" * 70 + "\n\n")

        f.write("Summary\n")
        f.write("-" * 70 + "\n")
        f.write(f"下載成功: {stats['download_success']}\n")
        f.write(f"已存在略過: {stats['skip_existing']}\n")
        f.write(f"416 後重抓成功: {stats['restart_after_416_success']}\n")
        f.write(f"跳過 query page: {stats['skip_query_page']}\n")
        f.write(f"跳過非目標檔案: {stats['skip_non_target']}\n")
        f.write(f"跳過 root 外連結: {stats['skip_outside_root']}\n")
        f.write(f"跳過重複檔案 URL: {stats['skip_duplicate_file_url']}\n")
        f.write(f"成功頁面數: {stats['page_success']}\n")
        f.write(f"失敗頁面數: {stats['page_failed']}\n")
        f.write(f"總失敗項目: {total_failures}\n\n")

        f.write("Failure Categories\n")
        f.write("-" * 70 + "\n\n")

        for category, items in failure_stats.items():
            label = failure_labels.get(category, category)
            f.write(f"[{label}] count = {len(items)}\n")
            for item in items:
                f.write(f"  URL: {item['url']}\n")
                if item["detail"]:
                    f.write(f"  Detail: {item['detail']}\n")
                f.write("\n")
            f.write("-" * 70 + "\n")

    return failure_log, total_failures


def print_summary(failure_log: Path, total_failures: int):
    print("\nDone.")
    print("=" * 50)
    print(f"下載成功: {stats['download_success']}")
    print(f"已存在略過: {stats['skip_existing']}")
    print(f"416 後重抓成功: {stats['restart_after_416_success']}")
    print(f"跳過 query page: {stats['skip_query_page']}")
    print(f"跳過非目標檔案: {stats['skip_non_target']}")
    print(f"跳過 root 外連結: {stats['skip_outside_root']}")
    print(f"跳過重複檔案 URL: {stats['skip_duplicate_file_url']}")
    print(f"成功頁面數: {stats['page_success']}")
    print(f"失敗頁面數: {stats['page_failed']}")
    print(f"總失敗項目: {total_failures}")
    print("-" * 50)
    for category, items in failure_stats.items():
        label = failure_labels.get(category, category)
        print(f"{label}: {len(items)}")
    print("-" * 50)
    print(f"Failure report: {failure_log}")


# ======== Main ========

if __name__ == "__main__":
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    for base_url in BASE_URLS:
        crawl(base_url, base_url)

    failure_log, total_failures = write_failure_report()
    print_summary(failure_log, total_failures)
