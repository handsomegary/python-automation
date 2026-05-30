import time
from pathlib import Path
from urllib.parse import urljoin, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://twins.ee.nctu.edu.tw/courses/Comm06_I/"
SAVE_DIR = Path(r"C:\Users\linga\Downloads\nctu")

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


def is_directory_link(href: str) -> bool:
    return href.endswith("/") and href not in ("../", "/")


def is_allowed_file(href: str) -> bool:
    return not href.endswith("/")


def local_path_from_url(url: str) -> Path:
    parsed = urlparse(url)
    rel_path = unquote(parsed.path.lstrip("/"))
    return SAVE_DIR / rel_path.replace("archive/AIC/", "", 1)


def download_file(file_url: str, max_attempts: int = 5):
    if file_url in downloaded_files:
        return
    downloaded_files.add(file_url)

    local_path = local_path_from_url(file_url)
    local_path.parent.mkdir(parents=True, exist_ok=True)

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
                # 允許 200（重新下載）或 206（續傳）
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
    if url in visited_pages:
        return
    visited_pages.add(url)

    print(f"[Crawl] {url}")
    try:
        r = session.get(url, timeout=(15, 60))
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.exceptions.RequestException as e:
        print(f"[Page Failed] {url}")
        print(f"  Error: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue

        full_url = urljoin(url, href)

        if not full_url.startswith(BASE_URL):
            continue

        if is_directory_link(href):
            crawl(full_url)
        elif is_allowed_file(href):
            download_file(full_url)


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
