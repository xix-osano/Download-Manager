import os
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

NUM_THREADS = 4  # You can increase this

def get_file_size(url):
    response = requests.head(url, allow_redirects=True)
    return int(response.headers.get('content-length', 0))

def download_range(url, start, end, part_num, tmp_dir):
    filename = os.path.join(tmp_dir, f'part{part_num}')
    headers = {'Range': f'bytes={start}-{end}'}

    # Resume support: check if part already exists and is complete
    if os.path.exists(filename):
        existing_size = os.path.getsize(filename)
        expected_size = end - start + 1
        if existing_size >= expected_size:
            return  # Part already fully downloaded

    response = requests.get(url, headers=headers, stream=True)
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

def merge_files(filename, num_parts, tmp_dir):
    with open(filename, 'wb') as outfile:
        for i in range(num_parts):
            part_file = os.path.join(tmp_dir, f'part{i}')
            with open(part_file, 'rb') as pf:
                outfile.write(pf.read())
            os.remove(part_file)

def download_file(url, filename=None):
    if not filename:
        filename = url.split('/')[-1]

    file_size = get_file_size(url)
    if file_size == 0:
        print(f"❌ Could not retrieve file size: {url}")
        return

    print(f"⬇️ Downloading: {filename} ({file_size / 1024 / 1024:.2f} MB)")

    part_size = file_size // NUM_THREADS
    ranges = []
    for i in range(NUM_THREADS):
        start = i * part_size
        end = file_size - 1 if i == NUM_THREADS - 1 else (start + part_size - 1)
        ranges.append((start, end))

    tmp_dir = f"{filename}_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        list(tqdm(
            executor.map(
                lambda args: download_range(url, *args, tmp_dir),
                [(r[0], r[1], i) for i, r in enumerate(ranges)]
            ),
            total=NUM_THREADS,
            desc="Downloading"
        ))

    merge_files(filename, NUM_THREADS, tmp_dir)
    os.rmdir(tmp_dir)
    print(f"✅ Done: {filename}")

def download_queue(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Queue file not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            download_file(url)
        except Exception as e:
            print(f"⚠️ Failed to download {url}: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1].endswith(".txt"):
        # Download queue from file
        download_queue(sys.argv[1])
    elif len(sys.argv) >= 2:
        # Single file
        url = sys.argv[1]
        filename = sys.argv[2] if len(sys.argv) >= 3 else None
        download_file(url, filename)
    else:
        print("Usage:")
        print("  python multi_download.py <URL> [output_filename]")
        print("  python multi_download.py urls.txt")