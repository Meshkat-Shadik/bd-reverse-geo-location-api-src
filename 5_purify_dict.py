import json
import os
import csv
import time

DATA_DIR = "data"
DICT_FILE = "data/master_dict.json"
PURE_DICT_FILE = "data/master_dict_pure.json"
CSV_FILE = "data/master_hierarchy.csv"

# The ONLY keys we actually care about for reverse geocoding
GEOGRAPHIC_KEYS = {
    "__layer__",
    "GEO_CODE",
    "DIVISION_CODE", "DIVISION_NAME",
    "DISTRICT_CODE", "DISTRICT_NAME",
    "CITY_CODE", "CITY_NAME",
    "UPAZILA_CODE", "UPAZILA_NAME",
    "MUNICIPALITY_CODE", "MUNICIPALITY_NAME",
    "UNION_CODE", "UNION_NAME",
    "MAUZA_CODE", "MAUZA_NAME",
    "VILLAGE_CODE", "VILLAGE_NAME",
    "EA_NO", "EA_CODE" # Enumeration Area (Street / Block Level)
}

def purify():
    print(f"[*] Reading massive raw dictionary: {DICT_FILE} ...")
    t0 = time.time()
    
    with open(DICT_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    print(f"    - Loaded {len(raw_data)} records in {time.time() - t0:.2f}s")
    
    pure_data = []
    
    # We will also collect unique rows for the CSV to build the ultimate Master Hierarchy CSV
    # (Since many pixels might share the same dictionary entry, the raw json has unique entries per shape.
    # Actually, the dictionary is already unique per shape, but we want to strip the noise.)
    
    csv_rows = set()
    csv_data = []

    print("[*] Purifying data (stripping population, names of officials, etc)...")
    for row in raw_data:
        if row is None:
            pure_data.append(None)
            continue
            
        clean_row = {}
        for k, v in row.items():
            if k in GEOGRAPHIC_KEYS:
                clean_row[k] = v
                
        pure_data.append(clean_row)
        
        # For the CSV, we'll create a flattened tuple to ensure uniqueness
        # We only want the unique geographic lines in the CSV.
        tup = tuple(clean_row.get(k, "") for k in sorted(GEOGRAPHIC_KEYS) if k != "__layer__")
        if tup not in csv_rows:
            csv_rows.add(tup)
            csv_data.append({k: clean_row.get(k, "") for k in sorted(GEOGRAPHIC_KEYS) if k != "__layer__"})

    print(f"[*] Saving purified JSON ({PURE_DICT_FILE})...")
    with open(PURE_DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(pure_data, f, ensure_ascii=False)
        
    print(f"[*] Saving master CSV goldmine ({CSV_FILE})...")
    if csv_data:
        keys = sorted(GEOGRAPHIC_KEYS - {"__layer__"})
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(csv_data)
            
    print(f"[SUCCESS] Purification complete!")
    
    old_size = os.path.getsize(DICT_FILE) / 1024 / 1024
    new_size = os.path.getsize(PURE_DICT_FILE) / 1024 / 1024
    csv_size = os.path.getsize(CSV_FILE) / 1024 / 1024
    
    print(f"    - Original Size : {old_size:.1f} MB")
    print(f"    - Pure JSON Size: {new_size:.1f} MB")
    print(f"    - Master CSV    : {csv_size:.1f} MB  ({len(csv_data)} unique geo-hierarchies!)")
    
    # Replace old with new
    os.remove(DICT_FILE)
    os.rename(PURE_DICT_FILE, DICT_FILE)
    print(f"[*] Overwrote original dictionary with the purified version.")

if __name__ == "__main__":
    purify()