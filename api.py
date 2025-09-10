from pinscrape import scraper, Pinterest
import requests
import numpy as np
import cv2
import os
import hashlib
import time
import re
import unicodedata
import json

keyword = "70s 80s america real life"
output_folder = "output"
proxies = {}
number_of_workers = 5
images_to_download = 100
downloaded_db = "downloaded.json"


def _load_downloaded_db(db_path=downloaded_db):
    """Load the set of downloaded image hashes from file."""
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_downloaded_db(downloaded_set, db_path=downloaded_db):
    """Save the set of downloaded image hashes to file."""
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(list(downloaded_set), f, indent=2)


def _hash_url(url: str) -> str:
    """Generate a hash for the image URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _download_image(url: str, filename: str, output_folder: str = "output", retries: int = 3,
                    downloaded_set=None) -> None:
    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, _sanitize_filename(filename))

    # Hash the URL
    file_hash = _hash_url(url)

    # Skip if already downloaded
    if downloaded_set is not None and file_hash in downloaded_set:
        print(f"[SKIP] Already downloaded previously: {url}")
        return

    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            print(f"[OK] Saved: {filepath}")

            # Mark as downloaded
            if downloaded_set is not None:
                downloaded_set.add(file_hash)
                _save_downloaded_db(downloaded_set)

            return

        except Exception as e:
            attempt += 1
            print(f"[ERROR] Failed to download {url} (Attempt {attempt}/{retries}) - {e}")
            time.sleep(2)

    print(f"[FAIL] Could not download after {retries} attempts: {url}")


def _sanitize_filename(filename: str) -> str:
    filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    filename = re.sub(r'[\/:*?"<>|]', "", filename)
    filename = re.sub(r"\s+", "_", filename)
    filename = re.sub(r"_+", "_", filename).strip("_")
    return filename


def _using_search_engine():
    details = scraper.scrape(keyword, output_folder, proxies, number_of_workers, images_to_download, sleep_time=2)
    if details["isDownloaded"]:
        print("\nDownloading completed !!")
        print(f"\nTotal urls found: {len(details['extracted_urls'])}")
        print(f"\nTotal images downloaded (including duplicate images): {len(details['urls_list'])}")
        print(details)
    else:
        print("\nNothing to download !!", details)


def using_pinterest_apis(keywords, output_folder="output", proxies={}, number_of_workers=10, images_to_download=100):
    downloaded_set = _load_downloaded_db()

    p = Pinterest(proxies=proxies, sleep_time=2)
    results = p.search(keywords, images_to_download)

    titles = [result["title"] for result in results]
    descriptions = [result["description"] for result in results]
    seo_alt_text = [result["seo_alt_text"] for result in results]
    images_url = [result["images"]["orig"]["url"] for result in results]

    assert len(titles) == len(descriptions) == len(seo_alt_text) == len(images_url)

    filenames = [_sanitize_filename(f"{title} {description} {seo}.jpg")
                 for title, description, seo in zip(titles, descriptions, seo_alt_text)]

    for i, url in enumerate(images_url):
        _download_image(url, filenames[i], output_folder=output_folder, downloaded_set=downloaded_set)


if __name__ == "__main__":
    using_pinterest_apis(keyword, output_folder=output_folder, proxies=proxies,
                         number_of_workers=number_of_workers, images_to_download=images_to_download)
