# Bangladesh Reverse Geocoder

A highly efficient, fast, and resource-friendly reverse geocoding API for Bangladesh.

This project is built to process thousands of geographic requests without needing expensive servers or heavy databases like PostGIS. By changing how maps are processed, we designed a system that runs smoothly on free cloud hardware (like Hugging Face Spaces).

**Features at a glance:** Very fast response times, almost no RAM usage, covers 564,000+ regions, and it is 100% free to host.

---

## ⚡ How it works (The Problem & Our Solution)

Usually, finding the exact Village, Union, Upazila, District, and Division for a GPS coordinate (`lat`, `lng`) requires complex math (Vector Geometry). Databases have to draw a point and calculate if it falls inside a complex shape. 

*   **The Challenge:** Doing this math for thousands of users at once requires a lot of CPU power. Loading all 564,000 detailed boundaries takes up too much RAM. This makes it expensive to host.
*   **Our Solution:** We changed the approach entirely. We converted the map of Bangladesh into a hidden grid of pixels (where 1 pixel = ~55 meters). Every pixel is assigned a Location ID. To save space, we cut the grid into small parts and removed all the empty ocean and regions outside the country.

Now, when you send a location, the server doesn't do complex math. It just checks the grid file on the hard drive to find the matching ID.

## ✨ Key Features

*   🚀 **Extremely Fast:** API responses take about 0.5 to 1.5 milliseconds. The speed stays stable even if many users request data at the same time.
*   🧠 **Very Low Memory Usage:** The server uses almost zero RAM. We use a technique called memory mapping. The system reads only the small piece of data it needs directly from the storage.
*   📦 **Ready-to-use JSON:** Generating JSON data on the fly takes computer time. We pre-generated all 564,000 JSON responses and saved them. The API just reads the exact text and sends it to the user.
*   💸 **Free to Host:** Since it needs very little CPU, almost no RAM, and the data size is only ~208MB, you can easily host this on free platforms like the Hugging Face Free Tier (16GB RAM, 2 vCPU, 50GB Disk).

## 📊 Comparison

| Feature | Traditional GIS (PostGIS / GeoPandas) | Our GeoEngine |
| :--- | :--- | :--- |
| **Logic** | Complex Vector Geometry | Simple Grid Array Lookup |
| **Speed** | Moderate (10ms - 50ms) | **Very Fast** (~0.5ms - 1ms) |
| **Memory** | High (Gigabytes required) | **Almost Zero** |
| **Disk Space** | Very Large | **Small (~208MB)** |
| **Concurrency** | CPU can struggle under load | **Handles high load easily** |

## 🛠️ How to build the data pipeline yourself

If you want to build this system from the raw Government Census data from scratch, you can run these scripts in order:

1. `python 1_download_census.py` *(Downloads the shapefiles)*
2. `python 2_engine_builder.py` *(Creates the main grid from the shapes)*
3. `python 4_storage_optimizer.py` *(Deletes the massive raw files to save disk space)*
4. `python 5_purify_dict.py` *(Organizes the census metadata)*
5. `python 6_extreme_dict_compiler.py` *(Pre-generates all JSON responses)*
6. `python 7_sparse_compressor.py` *(Compresses the grid by removing ocean areas)*
7. `python server.py` *(Starts the fast API server)*

---
**Feel free to explore the code, fork the project, and host it for your own use.**
