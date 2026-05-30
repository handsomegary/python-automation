import time
from pathlib import Path
from urllib.parse import urljoin, unquote, urlparse
from posixpath import basename

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://twins.ee.nctu.edu.tw/courses/co_13/"
SAVE_DIR = Path(r"C:\Users\linga\Downloads\nctu")

# 只下載這些副檔名
ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls",
                ".xlsx", ".txt", ".v", ".png", ".jpg", ".jpeg",
                ".htm", ".html", ".rar", ".zip", ".exe", ".xml",
                ".thmx", ".cnf", ".btr", ".lck", ".ico", ".ini",
                ".m", ".gif", ".bmp", ".wmf"}

visited_pages = set()
downloaded_files = set()
failed_files = []

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


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    # 對頁面去掉 fragment，保留 query 給判斷是否 skip
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{parsed.query}" if parsed.query else "")


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

    # Apache directory listing 的排序 query，直接跳過
    if parsed.query in {
        "C=N;O=D", "C=M;O=A", "C=S;O=A", "C=D;O=A",
        "C=N;O=A", "C=M;O=D", "C=S;O=D", "C=D;O=D",
    }:
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

    # 只去掉最前面的 archive/
    if rel_path.startswith("archive/"):
        rel_path = rel_path[len("archive/"):]

    local_path = SAVE_DIR / rel_path

    return local_path


def ensure_parent_dir(local_path: Path) -> bool:
    parent = local_path.parent

    if parent.exists() and not parent.is_dir():
        print(f"[Skip] Parent exists as file, not directory: {parent}")
        return False

    parent.mkdir(parents=True, exist_ok=True)
    return True


def download_file(file_url: str, max_attempts: int = 5):
    file_url = normalize_url(file_url)

    if file_url in downloaded_files:
        return
    downloaded_files.add(file_url)

    if should_skip_url(file_url):
        print(f"[Skip query page] {file_url}")
        return

    if not has_allowed_extension(file_url):
        print(f"[Skip non-target] {file_url}")
        return

    local_path = local_path_from_url(file_url)

    if local_path.exists() and local_path.is_dir():
        print(f"[Skip] Local path is a directory, cannot write file: {local_path}")
        failed_files.append(file_url)
        return

    if not ensure_parent_dir(local_path):
        failed_files.append(file_url)
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
                # 416: Range 不合法，通常代表續傳點錯了，改成重抓
                if r.status_code == 416:
                    print(f"[416] Range invalid, restarting: {file_url}")
                    if local_path.exists():
                        local_path.unlink()
                    headers.pop("Range", None)

                    with session.get(file_url, stream=True, timeout=(15, 60)) as r2:
                        r2.raise_for_status()
                        with open(local_path, "wb") as f:
                            for chunk in r2.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                    return

                if r.status_code not in (200, 206):
                    r.raise_for_status()

                mode = "ab" if (existing_size > 0 and r.status_code == 206) else "wb"
                if mode == "wb" and existing_size > 0:
                    print(f"[Restart] Server does not support resume, restarting: {file_url}")

                with open(local_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            return

        except requests.exceptions.RequestException as e:
            print(f"[Retry {attempt}/{max_attempts}] {file_url}")
            print(f"  Error: {e}")
            time.sleep(2 * attempt)

    print(f"[Failed] {file_url}")
    failed_files.append(file_url)


def crawl(url: str):
    url = normalize_url(url)

    if should_skip_url(url):
        print(f"[Skip query page] {url}")
        return

    # 對頁面去重時，目錄頁不需要保留 query
    parsed = urlparse(url)
    page_key = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    if page_key in visited_pages:
        return
    visited_pages.add(page_key)

    print(f"[Crawl] {page_key}")
    try:
        r = session.get(page_key, timeout=(15, 60))
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.exceptions.RequestException as e:
        print(f"[Page Failed] {page_key}")
        print(f"  Error: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if should_skip_href(href):
            continue

        full_url = urljoin(page_key, href)
        full_url = normalize_url(full_url)

        if not full_url.startswith(BASE_URL):
            continue

        if should_skip_url(full_url):
            print(f"[Skip query page] {full_url}")
            continue

        if is_directory_link(href):
            crawl(full_url)
        elif has_allowed_extension(full_url):
            download_file(full_url)
        else:
            print(f"[Skip non-target] {full_url}")


if __name__ == "__main__":
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    crawl(BASE_URL)

    failed_log = SAVE_DIR / "failed_downloads.txt"
    with open(failed_log, "w", encoding="utf-8") as f:
        for item in failed_files:
            f.write(item + "\n")

    print("\nDone.")
    print(f"Failed files: {len(failed_files)}")
    print(f"Failure log: {failed_log}")
