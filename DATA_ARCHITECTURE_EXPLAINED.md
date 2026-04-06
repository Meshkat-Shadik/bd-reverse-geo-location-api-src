# The V5 Data Architecture: From A to Z

This document explains the exact files inside the `v5_prod/data/` directory. Because this engine is built for extreme speed and zero memory usage, it abandons traditional databases and JSON files. 

We will explain this in three levels: **The Child, The Developer, and The Professor.**

---

## 🟢 Level 1: The Child's Explanation (Simplified)

Imagine you want to find out what village a bird landed in. 

Normally, people use a giant book of maps. They trace the bird's exact coordinates, draw a dot, and then trace the squiggly lines of every village to see which shape the dot is inside. That takes a long time!

We built a **Magic Lego Board** instead.
1. **`grid.bin` (The Lego Board):** We covered all of Bangladesh with millions of tiny Lego pieces. Every Lego piece represents a 55-meter square of land. Instead of colors, we painted a single **Number ID** on every Lego. (e.g., Lego ID: 123).
2. **`meta.json` (The Ruler):** A tiny ruler that helps us instantly snap our GPS coordinate directly to the exact Lego piece, without aiming.
3. **`master_offsets.bin` & `master_lengths.bin` (The Treasure Map):** You found Lego #123. But what does 123 mean? You check the Treasure Map. It says, "The prize for #123 is buried exactly 5,000 steps away, and it is 200 steps long."
4. **`master_response_strings.bin` (The Pre-wrapped Gifts):** This is a giant line of pre-wrapped gifts (the text names of the villages). You walk 5,000 steps, take the 200-step long gift, and immediately hand it to the user. You don't even have to wrap it!

---

## 🟡 Level 2: The Developer's Explanation (The Execution Flow)

If you are a standard software engineer, you might ask: *"Where is the PostgreSQL database? Where is GeoPandas? How does this run on 50MB of RAM?"*

We killed the traditional databases and vector geometry because they consume too much RAM and CPU. Instead of vector math (Point-in-Polygon ray-casting), we use **Rasterization and Static Byte Buffers.**

When you query `lat=24.97, lng=89.17` in the FastAPI server, here is exactly what happens:

1. **`meta.json`**: Reads the max bounding box of Bangladesh and the pixel resolution limit.
2. **`grid.bin`**: A flattened 2D array of integers (`np.uint32`). Using a basic O(1) math formula, we convert the `lat/lng` into a `row` and `column`. We read `grid.bin[row, col]` and get the geographical ID (e.g., `191853`). **This takes 0.01 milliseconds.**
3. **`master_offsets.bin` & `master_lengths.bin`**: Instead of a standard Python Dictionary (`dict[191853]`), which takes 300MB of RAM to hold in memory, we use two 1D binary arrays. We look up index `[191853]` in the offsets file to get a byte start position, and the lengths file to get a byte size.
4. **`master_response_strings.bin`**: This is a massive 237MB text file consisting of purely pre-rendered JSON byte strings (`b'{"match":"exact", ...}'`). We simply slice the file from the start position to the end position, and receive the pre-built JSON response.
5. **Zero Serialization:** We hand those exact bytes directly back to the FastAPI `Response` object. We never use `json.dumps()` or `orjson` at runtime. 

Because all these `.bin` files use **`mmap`** (Memory Mapping), the Python script does not actually loop or load them into RAM. The Operating System loads fragments of the hard drive directly into the CPU cache only when requested.

---

## 🔵 Level 3: The Architecture Build Process (How and Why we made these files)

You might wonder, *how* did we generate these `.bin` files from standard Shapefiles and GeoJSONs? 
In the `v5/` builder directory (which we do not push to production), we ran two specific architectural pipelines.

### Build Step A: The Raster Engine (`2_engine_builder.py`)
*   **The Problem:** Traditional GIS checks "Is this point inside this complex polygon?" If a polygon has 50,000 vertices, the math takes heavy CPU cycles.
*   **The Approach:** We use a technique called the **Painter's Algorithm** via a library called `rasterio`. 
*   **How it works:** We created a gigantic empty 2D NumPy array covering Bangladesh. Every cell is ~55 meters wide. We then looped through all 564,000 polygons (from Divisions down to Villages). For the pixels that fall inside a polygon, we "painted" them with an integer ID representing that village.
*   **The Result:** We dumped this NumPy array to disk using `numpy.tofile()`. This created `grid.bin`. We completely destroyed the need for Vector math at runtime. 

### Build Step B: Extreme Dictionary Compiler (`6_extreme_dict_compiler.py`)
*   **The Problem:** Originally, we had a `master_dict.json` file. But loading a 239MB JSON file into Python takes over 300MB of server RAM. Furthermore, in web APIs, taking a Python dictionary and converting it to a JSON string (Serialization) accounts for a massive chunk of latency. 
*   **The Approach:** Ahead-of-Time (AOT) Byte Encoding.
*   **How it works:** We wrote a script that looped through the original `master_dict.json` item by item. For every single location, it generated the *exact final API string* (e.g., `b'{"match": "exact", "id": 120, "data": {"village": "Dhaka"}}'`). It wrote that string directly into `master_response_strings.bin`.
*   To keep track of where each string was saved, it recorded the starting byte into an array (`master_offsets.bin`) and the length into another array (`master_lengths.bin`). 
*   **The Result:** The API no longer needs to know how to create JSON. It just acts as a fast file-reader, grabbing pre-written JSON strings from the disk.

---

### File Dictionary Reference

| File | Size | Python Equivalent | Purpose |
| :--- | :--- | :--- | :--- |
| `meta.json` | 146 B | `dict` | Stores the math coefficients (Max bounds & cell resolution). |
| `grid.bin` | ~504 MB | `list[list[int]]` | The Map Matrix. Converts a Row/Col straight into a Location ID. |
| `master_offsets.bin` | 4.3 MB | `list[int]` | Array of pointers. Tells us where a string starts. |
| `master_lengths.bin` | 2.2 MB | `list[int]` | Array of sizes. Tells us how long a string is. |
| `master_response_strings.bin` | 237 MB | `bytes` | The pre-serialized, pre-written API JSON responses. |