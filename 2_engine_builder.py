import os
import json
import mmap
import time
import numpy as np
import geopandas as gpd
from rasterio import features
from affine import Affine

DATA_DIR = "data"
# Layers ordered from largest to smallest. Smallest will overwrite parents.
# This ensures that even if you click in a remote area without a village, 
# it falls back to the union/upazila/district.
LAYERS = [
    "division",
    "district",
    "upazila",
    "municipality",
    "citycorporation",
    "union",
    "mauza",
    "village",
    "enumerationarea"
]

# ALIEN-LEVEL RESOLUTION:
# 1 degree = ~111km. 
# 0.0005 degrees = ~55.5 meters. 500MB grid, Lightning fast build.
CELL_SIZE = 0.0005
MIN_LAT = 20.3
MAX_LAT = 26.9
MIN_LNG = 87.8
MAX_LNG = 92.8

ROWS = int(round((MAX_LAT - MIN_LAT) / CELL_SIZE))
COLS = int(round((MAX_LNG - MIN_LNG) / CELL_SIZE))

GRID_FILE = "data/grid.bin"
DICT_FILE = "data/master_dict.json"
META_FILE = "data/meta.json"

def build():
    print(f"[*] GRID Dimensions: {ROWS} rows x {COLS} cols ({ROWS * COLS} pixels, ~27m resolution)")
    
    # Allocate entirely in standard Python RAM because 500MB is nothing.
    print(f"[*] Allocating {round((ROWS*COLS*4)/(1024**2), 2)} MB array in RAM...")
    grid = np.zeros((ROWS, COLS), dtype=np.uint32)
    
    # Standard GIS Affine: Top-Left corner is (MIN_LNG, MAX_LAT). 
    # Y-coordinate decreases as row increases. X-coordinate increases as col increases.
    transform = Affine.translation(MIN_LNG, MAX_LAT) * Affine.scale(CELL_SIZE, -CELL_SIZE)
    
    master_dict = [None] # Index 0 is "outside" / reserved
    global_id = 1
    
    t00 = time.perf_counter()
    for layer in LAYERS:
        gpkg_path = f"data/{layer}.gpkg"
        if not os.path.exists(gpkg_path):
            print(f"[!] Warning: {gpkg_path} missing, skipping.")
            continue
            
        print(f"[*] Loading {layer.upper()} ...")
        t0 = time.perf_counter()
        gdf = gpd.read_file(gpkg_path)[["geometry"] + [c for c in gpd.read_file(gpkg_path, rows=1).columns if c != "geometry"]]
        
        shapes = []
        # Assign IDs and build polygons
        for idx, row in gdf.iterrows():
            geom = row["geometry"]
            if geom is None or geom.is_empty:
                continue
            
            # Serialize all string attributes from the row
            attr_dict = {}
            for col in gdf.columns:
                if col != "geometry" and row[col] is not None:
                    val = str(row[col])
                    if val.strip() and val.lower() != "nan" and val.lower() != "none":
                        attr_dict[col] = val
                        
            attr_dict["__layer__"] = layer  # Mark the resolution level
            
            master_dict.append(attr_dict)
            shapes.append((geom, global_id))
            global_id += 1
            
        print(f"    - Parsed {len(shapes)} polygons. Burning to Matrix...")
        # Pure C-level Rasterio Speed. We write directly to the 
        # OS memory-mapped disk buffer! O(0) heap RAM usage! 👽
        features.rasterize(
            shapes,
            out=grid,
            transform=transform,
            default_value=0, # untouched cells remain
            dtype=np.uint32
        )
        
        print(f"    - Done in {time.perf_counter() - t0:.1f}s")
        
    print(f"[*] Dumping grid binary...")
    grid.tofile(GRID_FILE)
    
    print(f"[*] Dumping global dictionary ({len(master_dict)} items)...")
    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_dict, f, ensure_ascii=False)
        
    print(f"[*] Saving metadata...")
    meta = {
        "min_lat": MIN_LAT,
        "max_lat": MAX_LAT,
        "min_lng": MIN_LNG,
        "max_lng": MAX_LNG,
        "cell_size": CELL_SIZE,
        "rows": ROWS,
        "cols": COLS,
        "total_locations": len(master_dict) - 1
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f)
        
    print(f"[SUCCESS] GEO ENGINE BUILT in {time.perf_counter() - t00:.1f}s! 🛸")

if __name__ == "__main__":
    build()