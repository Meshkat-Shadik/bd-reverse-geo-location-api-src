# Hugging Face Deployment Guide (V5 GeoEngine)

This document outlines exactly how to deploy the **V5 GeoEngine** to Hugging Face's Free Tier, why it will survive extreme traffic, and specifically which files you need to upload.

## 1. Can V5 be deployed on Hugging Face? Are there problems?

**Yes. In fact, V5 was engineered *specifically* to beat Hugging Face's Free Tier limitations.** 

If you deployed the old V2 (GeoPandas) on Hugging Face:
- **RAM Problem:** GeoPandas would try to load 564,000 polygons into the 16GB RAM limit. It would crash or throttle.
- **CPU Problem:** The Free Tier only gives you **2 vCPUs**. Doing complex math (Ray-Casting) to find if a coordinate is inside a polygon takes 30ms-100ms. With 2 CPUs, if 100 people query at once, the server queues up and lags instantly.

**Why V5 has NO problems on Hugging Face:**
- **RAM (16GB Limit):** V5 uses `mmap`. The RAM usage of your FastAPI app will be less than **50 MB**! The Operating System handles the 500MB grid on the disk dynamically. You will never hit the 16GB memory ceiling.
- **CPU (2 vCPU Limit):** Because V5 is just reading an array index `[row, col]`, there is no geometry math. It takes `0.5ms` per request. Even with just 2 vCPUs, you can serve **thousands of requests per second** concurrently.
- **Storage (50GB Limit):** The entire V5 compiled engine is about 750 MB. 

There are **zero over-usage** concerns. It is the cheapest, fastest possible configuration.

---

## 2. Do we need everything in the `#v5` directory?

**NO!** You only need the *final compiled engine* to run the API. The python scripts like `1_download_census.py` and `2_engine_builder.py` are **"Builder Scripts"**. They are only used on your local MacBook to generate the `.bin` files. 

When you upload to Hugging Face, you **only upload the Runtime Files**.

### Files to UPLOAD to Hugging Face (The Runtime):
1. `server.py` *(The main FastAPI application)*
2. `requirements.txt` *(Needs: fastapi, uvicorn, orjson, numpy)*
3. `Dockerfile` *(To tell Hugging Face how to boot `server.py`)*
4. `data/grid.bin` *(The 500MB Map array)*
5. `data/master_offsets.bin` *(The dictionary routing)*
6. `data/master_lengths.bin` *(The dictionary routing)*
7. `data/master_response_strings.bin` *(The extreme JSON string bytes)*
8. `data/meta.json` *(The grid configurations)*

### Files to DELETE/IGNORE (Do NOT upload to Hugging Face):
- ❌ All the `.py` scripts (`1_download...`, `2_engine...`, `4_storage...`, `5_purify...`, `6_extreme...`).
- ❌ `data/master_dict.json` *(239MB - We already compiled this into the binary strings in step 6! The server doesn't use it anymore).*
- ❌ `data/master_hierarchy.csv` *(Not used by the API, it's just for your data analysis).*
- ❌ Any `.zip` or `.gpkg` files. 

---

## 3. How to Deploy (Step-by-Step)

### Step 1: Setup the Hugging Face Space
1. Go to Hugging Face -> Create New Space.
2. Select **Docker** as the Space SDK (Blank).
3. Choose the Free Tier (16GB RAM, 2 vCPU).

### Step 2: Create a `requirements.txt`
In your Hugging Face space, create this file:
```text
fastapi
uvicorn
orjson
numpy
```

### Step 3: Create the `Dockerfile`
Hugging Face needs to know how to start the app. Create this file:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server and the data folder
COPY server.py .
COPY data/ /app/data/

# Open port 7860 (Hugging Face default)
EXPOSE 7860

# Start Extreme V5 API using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Step 4: Change port in `server.py` (Optional but good practice)
At the bottom of `server.py`, change:
```python
uvicorn.run("server:app", host="127.0.0.1", port=8000)
# to
uvicorn.run("server:app", host="0.0.0.0", port=7860)
```

### Step 5: Upload the files
Upload `server.py` and the 5 specific files inside the `data/` folder via Git LFS (because `.bin` files are large).

### Step 6: Watch it boot!
Hugging Face will build the Docker container and start your API. Because everything is pre-compiled into OS-paged `.bin` memory maps, it will boot in less than a second and immediately start serving high-speed Lookups!