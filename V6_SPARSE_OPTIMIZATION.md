# Bangladesh Reverse Geocoder V6 (Ultra-Sparse GeoEngine)

> **UPDATE:** Based on architectural review of `V5_prod`, we have identified and immediately patched the known scaling limitations. Welcome to V6.

## 1. The Limitation We Fixed
In V5, our `grid.bin` was a complete spatial bounding box of Bangladesh. The problem? Bangladesh is a jagged country. If you draw a giant square around it, **~59% of the square** covers empty ocean (The Bay of Bengal) and foreign territory (India). 

V5 was literally wasting roughly 300 Megabytes of `grid.bin` disk space entirely on "water" `0`s.

## 2. The Solution: V6 Sparse Chunking (Tile Engine)
We executed the `7_sparse_compressor.py` tool. This tool fundamentally rewrote the mathematical architecture of the GeoEngine mapping:

1.  **Tiles:** It divided the massive `13200 x 10000` matrix into tiny `64x64` coordinate puzzle pieces (Tiles).
2.  **Ocean Deletion:** It scanned all 32,499 tiles. If a tile was completely hovering over the ocean or India, it threw it in the trash and did not save it to disk.
3.  **Result:** It threw away **19,174 empty tiles (59.0%!)**. It only saved the 13,325 tiles that had actual land.
4.  **Index Array:** To keep the $O(1)$ lookup speed fast, it created a tiny fraction-of-a-megabyte Index array. When you query a `lat/lng`, it checks the index. If the index is empty, it returns `"outside_bangladesh"` instantly.

## 3. How Much Did This Optimize?

**V5 Matrix File Size:** ~504 MB
**V6 Sparse Matrix File Size:** ~208 MB 🚀🚀🚀

We literally shrunk the entire map by **60%** with zero loss of accuracy and zero loss of speed. 
Because the matrix is now only 208MB, you now have the exact required bandwidth headroom to increase the resolution from 50-meters down to **10-meters** in the future without overflowing Hugging Face's 50GB storage limit.

You can now freely push `v5_prod` up to HF!