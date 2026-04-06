import numpy as np
import mmap
import os
import json
import time

def compress_to_sparse():
    t0 = time.perf_counter()
    print("Loading meta.json...")
    with open("data/meta.json", "r") as f:
        meta = json.load(f)
        
    ROWS = meta["rows"]
    COLS = meta["cols"]
    TILE_SIZE = 64 # Small 64x64 tiles (approx 3.5km x 3.5km patches)
    
    TILES_ROWS = (ROWS + TILE_SIZE - 1) // TILE_SIZE
    TILES_COLS = (COLS + TILE_SIZE - 1) // TILE_SIZE
    
    print(f"Original Grid: {ROWS}x{COLS}. Divides into {TILES_ROWS}x{TILES_COLS} Tiles.")
    
    print("Memory mapping original grid.bin...")
    with open("data/grid.bin", "rb") as f:
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        grid = np.ndarray(shape=(ROWS, COLS), dtype=np.uint32, buffer=m)

    index_array = np.full((TILES_ROWS, TILES_COLS), -1, dtype=np.int32)
    
    sparse_grid_file = open("data/sparse_grid.bin", "wb")
    
    current_tile_index = 0
    empty_tiles = 0
    valid_tiles = 0
    
    print("Executing Sparse Matrix Chunking...")
    for tr in range(TILES_ROWS):
        for tc in range(TILES_COLS):
            r_start = tr * TILE_SIZE
            r_end = min(r_start + TILE_SIZE, ROWS)
            c_start = tc * TILE_SIZE
            c_end = min(c_start + TILE_SIZE, COLS)
            
            tile = grid[r_start:r_end, c_start:c_end]
            
            if not np.any(tile):
                empty_tiles += 1
            else:
                valid_tiles += 1
                # To ensure uniform stride math, we MUST pad edge tiles to TILE_SIZE x TILE_SIZE
                padded_tile = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.uint32)
                padded_tile[:r_end-r_start, :c_end-c_start] = tile
                
                # Write to disk
                sparse_grid_file.write(padded_tile.tobytes())
                index_array[tr, tc] = current_tile_index
                current_tile_index += 1

    sparse_grid_file.close()
    
    print("Writing index array...")
    index_array.tofile("data/sparse_index.bin")
    
    meta["tile_size"] = TILE_SIZE
    meta["tiles_rows"] = TILES_ROWS
    meta["tiles_cols"] = TILES_COLS
    
    with open("data/meta.json", "w") as f:
        json.dump(meta, f, indent=2)
        
    print(f"DONE! Compressed in {time.perf_counter() - t0:.2f}s")
    print(f"Total Tiles: {TILES_ROWS * TILES_COLS}")
    print(f"Empty Ocean/India Tiles Discarded: {empty_tiles} ({empty_tiles/(TILES_ROWS*TILES_COLS)*100:.1f}%)")
    print(f"Valid Land Tiles Saved: {valid_tiles}")
    
    orig_mb = (ROWS * COLS * 4) / (1024*1024)
    new_mb = (valid_tiles * TILE_SIZE * TILE_SIZE * 4) / (1024*1024)
    print(f"Storage Shrinkage: {orig_mb:.1f} MB -> {new_mb:.1f} MB! 🚀")
    
    print("Optimization Complete! You can now safely delete the original `grid.bin` permanently!")

if __name__ == "__main__":
    compress_to_sparse()