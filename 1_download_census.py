import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO_URL = "https://github.com/justinelliotmeyers/bangladesh_2022_census_gis/raw/main/"
DATA_DIR = "data"

DATASETS = {
    "division": {"parts": 0},
    "district": {"parts": 0},
    "upazila": {"parts": 1},
    "union": {"parts": 3},    
    "mauza": {"parts": 9},    
    "village": {"parts": 11},
    "municipality": {"parts": 0},
    "citycorporation": {"parts": 0},
    "enumerationarea": {"parts": 21}
}

def download_file(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"[-] Already exists: {filename}")
        return filepath
        
    url = REPO_URL + filename
    print(f"[*] Downloading {filename} ...")
    try:
        urllib.request.urlretrieve(url, filepath)
        print(f"[+] Downloaded: {filename} ({os.path.getsize(filepath) // 1024 // 1024} MB)")
        return filepath
    except Exception as e:
        print(f"[!] Error downloading {filename}: {e}")
        return None

def process_dataset(name, config):
    print(f"\n=== Processing {name.upper()} ===")
    parts_count = config["parts"]
    files_to_dl = []
    
    if parts_count == 0:
        files_to_dl.append(f"{name}.zip")
    else:
        for i in range(1, parts_count + 1):
            files_to_dl.append(f"{name}.z{i:02d}")
        files_to_dl.append(f"{name}.zip")
        
    # Download parts
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(download_file, files_to_dl))
        
    gpkg_path = os.path.join(DATA_DIR, f"{name}.gpkg")
    if os.path.exists(gpkg_path):
        print(f"[*] {gpkg_path} already extracted.")
        return
        
    # Concatenate if multipart
    if parts_count > 0:
        concat_zip = os.path.join(DATA_DIR, f"{name}_full.zip")
        if not os.path.exists(concat_zip):
            print(f"[*] Concatenating multipart zip for {name}...")
            cat_cmd = ["cat"] + [os.path.join(DATA_DIR, f) for f in files_to_dl]
            with open(concat_zip, "wb") as outfile:
                subprocess.run(cat_cmd, stdout=outfile)
            print(f"[+] Created {concat_zip}")
        
        print(f"[*] Extracting {concat_zip}...")
        subprocess.run(["unzip", "-o", concat_zip, "-d", DATA_DIR], capture_output=True)
    else:
        dl_zip = os.path.join(DATA_DIR, f"{name}.zip")
        print(f"[*] Extracting {dl_zip}...")
        subprocess.run(["unzip", "-o", dl_zip, "-d", DATA_DIR], capture_output=True)

    print(f"[+] Finished {name}")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    for name, config in DATASETS.items():
        process_dataset(name, config)
    
    print("\n[SUCCESS] V5 Datasets Downloaded and Extracted!")
