import os
import json
import mmap
import time
from contextlib import asynccontextmanager
import orjson
from fastapi import FastAPI, Query, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))

class GeoEngine:
    def __init__(self, data_dir="data/"):
        self.data_dir = os.path.join(base_dir, data_dir)
        
        t0 = time.perf_counter()
        # 1. Load Meta
        with open(os.path.join(self.data_dir, "meta.json"), "r") as f:
            self.meta = json.load(f)
            
        self.min_lat = self.meta["min_lat"]
        self.max_lat = self.meta["max_lat"]
        self.min_lng = self.meta["min_lng"]
        self.max_lng = self.meta["max_lng"]
        self.cell_size = self.meta["cell_size"]
        self.rows = self.meta["rows"]
        self.cols = self.meta["cols"]
        self.tile_size = self.meta.get("tile_size", 64)
        self.tiles_rows = self.meta.get("tiles_rows", 0)
        self.tiles_cols = self.meta.get("tiles_cols", 0)
        self.total_locations = self.meta["total_locations"]
        
        # 2. Memory-Map the SPARSE Block Grid (Crushes empty ocean waste)
        gp = os.path.join(self.data_dir, "sparse_grid.bin")
        self.f_grid = open(gp, "rb")
        self.mmap_grid = mmap.mmap(self.f_grid.fileno(), 0, access=mmap.ACCESS_READ)
        
        # Load Sparse Index Array
        ip = os.path.join(self.data_dir, "sparse_index.bin")
        self.f_index = open(ip, "rb")
        self.mmap_index = mmap.mmap(self.f_index.fileno(), 0, access=mmap.ACCESS_READ)
        self.sparse_index = np.ndarray(
            shape=(self.tiles_rows, self.tiles_cols),
            dtype=np.int32,
            buffer=self.mmap_index
        )
        
        # 3. EXTREME ZERO-RAM MEMORY MAP dictionaries
        # Load binary index arrays (O(1) seek offset overhead without json dicts in RAM!)
        f_offs = os.path.join(self.data_dir, "master_offsets.bin")
        self.f_offsets = open(f_offs, "rb")
        self.m_offsets = mmap.mmap(self.f_offsets.fileno(), 0, access=mmap.ACCESS_READ)
        self.num_entries = len(self.m_offsets) // 8
        self.offsets = np.ndarray(shape=(self.num_entries,), dtype=np.uint64, buffer=self.m_offsets)
        
        f_lens = os.path.join(self.data_dir, "master_lengths.bin")
        self.f_lengths = open(f_lens, "rb")
        self.m_lengths = mmap.mmap(self.f_lengths.fileno(), 0, access=mmap.ACCESS_READ)
        self.lengths = np.ndarray(shape=(self.num_entries,), dtype=np.uint32, buffer=self.m_lengths)
        
        f_strs = os.path.join(self.data_dir, "master_response_strings.bin")
        self.f_strings = open(f_strs, "rb")
        self.m_strings = mmap.mmap(self.f_strings.fileno(), 0, access=mmap.ACCESS_READ)
            
        ms = (time.perf_counter() - t0) * 1000
        print(f"[geo] Extreme Engine Booted in {ms:.0f}ms | 0 RAM footprint | GEO ENGINE ACTIVE")

    def lookup(self, lat: float, lng: float):
        t0 = time.perf_counter_ns()
        
        try:
            import math
            if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
                return Response(
                    content=b'{"match":"outside_bangladesh","performance_ms":0.0}',
                    media_type="application/json"
                )
            
            row = int((self.max_lat - lat) / self.cell_size)
            col = int((lng - self.min_lng) / self.cell_size)
        except (ValueError, OverflowError, TypeError):
            return Response(
                content=b'{"match":"outside_bangladesh","performance_ms":0.0}',
                media_type="application/json"
            )
        
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            lookup_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return Response(
                content=b'{"match":"outside_bangladesh","performance_ms":' + str(lookup_ms).encode() + b'}',
                media_type="application/json"
            )
            
        # O(1) Tiled Sparse Matrix Lookup
        tile_r = row // self.tile_size
        tile_c = col // self.tile_size
        
        # Check index
        tile_offset = int(self.sparse_index[tile_r, tile_c])
        
        if tile_offset == -1:
            # We are inside the bounding box, but the tile is completely empty ocean/india!
            uid = 0
        else:
            sub_r = row % self.tile_size
            sub_c = col % self.tile_size
            # 4 bytes per uint32. The offset points to the chunk.
            byte_start = tile_offset * (self.tile_size * self.tile_size * 4) + ((sub_r * self.tile_size + sub_c) * 4)
            # Read exactly 4 bytes instantly using standard slicing or struct!
            chunk = self.mmap_grid[byte_start : byte_start + 4]
            uid = int.from_bytes(chunk, byteorder='little')
        
        if uid == 0:
            lookup_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return Response(
                content=b'{"match":"outside_bangladesh","reason":"unmapped_area","performance_ms":' + str(lookup_ms).encode() + b'}',
                media_type="application/json"
            )
            
        # O(1) Binary Dict Pull
        offset = int(self.offsets[uid])
        length = int(self.lengths[uid])
        
        # Directly extract the baked JSON byte payload from the memory-mapped string block
        base_json_bytes = self.m_strings[offset: offset+length]
        
        lookup_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        
        # Inject dynamic performance metadata string! Zero serialization!
        final_bytes = base_json_bytes + b', "performance_ms": ' + str(lookup_ms).encode() + b'}'
        
        return Response(content=final_bytes, media_type="application/json")

engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = GeoEngine()
    yield
    engine = None

app = FastAPI(
    title="BD Reverse Geocoder V5",
    version="5.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/reverse/{lat},{lng}")
async def reverse_path_comma(lat: float, lng: float):
    return engine.lookup(lat, lng)

@app.get("/reverse")
async def reverse_query(lat: float = Query(..., ge=-90.0, le=90.0), lng: float = Query(..., ge=-180.0, le=180.0)):
    # Basic FastAPI validation ensures numbers are roughly geographic.
    # Returns raw compiled C-style byte strings natively inside a FastAPI Response.
    return engine.lookup(lat, lng)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860, log_level="info")