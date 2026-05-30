import os
from pathlib import Path
from urllib.parse import urljoin, unquote, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://nthuee.org/archive/AIC/"
SAVE_DIR = Path(r"C:\Users\linga\Downloads\AIC")
ALLOWED_EXTS = {".pdf", ".docx", ".pptx", ".png"}

visited_pages = set()
downloaded_files = set()

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

def is_directory_link(href: str) -> bool:
    return href.endswith("/") and href not in ("../", "/")

def is_allowed_file(href: str) -> bool:
    path = urlparse(href).path.lower()
    return any(path.endswith(ext) for ext in ALLOWED_EXTS)

def local_path_from_url(url: str) -> Path:
    parsed = urlparse(url)
    rel_path = unquote(parsed.path.lstrip("/"))  # 保留中文
    return SAVE_DIR / rel_path.replace("archive/AIC/", "", 1)

def download_file(file_url: str):
    if file_url in downloaded_files:
        return
    downloaded_files.add(file_url)

    local_path = local_path_from_url(file_url)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists():
        print(f"[Skip] {local_path}")
        return

    print(f"[Download] {file_url}")
    r = session.get(file_url, stream=True, timeout=30)
    r.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def crawl(url: str):
    if url in visited_pages:
        return
    visited_pages.add(url)

    print(f"[Crawl] {url}")
    r = session.get(url, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue

        full_url = urljoin(url, href)

        # 只限制在 AIC 底下
        if not full_url.startswith(BASE_URL):
            continue

        if is_directory_link(href):
            crawl(full_url)
        elif is_allowed_file(href):
            download_file(full_url)

if __name__ == "__main__":
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    crawl(BASE_URL)
    print("\nDone.")
