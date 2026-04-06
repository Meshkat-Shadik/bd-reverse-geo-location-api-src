import os
import glob

DATA_DIR = "v5/data"

def optimize_storage():
    print(f"[*] Analyzing Storage in {DATA_DIR} ...")
    
    saved_bytes = 0
    
    # 1. We ONLY want to keep grid.bin, master_dict.json, and meta.json
    keep_files = ["grid.bin", "master_dict.json", "meta.json"]
    
    # Target all raw zip chunks, extracted zip archives, and heavy gpkgs
    patterns_to_delete = [
        "*.z[0-9][0-9]",  # .z01, .z02, etc.
        "*.zip",          # division.zip, upazila_full.zip, etc
        "*.gpkg",         # The 600MB+ vector databases
    ]
    
    for pattern in patterns_to_delete:
        paths = glob.glob(os.path.join(DATA_DIR, pattern))
        for p in paths:
            filename = os.path.basename(p)
            if filename not in keep_files:
                size = os.path.getsize(p)
                os.remove(p)
                saved_bytes += size
                print(f"    - Removed {filename} ({round(size / 1024 / 1024, 1)} MB)")
                
    print(f"\n[SUCCESS] Storage Optimized!")
    print(f"[*] Total Space Freed for Hugging Face: {round(saved_bytes / 1024 / 1024 / 1024, 2)} GB")

if __name__ == "__main__":
    optimize_storage()