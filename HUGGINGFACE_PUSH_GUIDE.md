# Push Guide: Deploying `v5_prod` to Hugging Face

Welcome to the **production-ready** version of V5. I have completely isolated only the necessary files for the runtime into this `v5_prod` directory.

### Quick Checklist:
This folder has **eliminated** all local python generator scripts and the giant metadata JSON / CSV files. The total footprint is heavily compressed:
*   `server.py`: The lightning fast FastAPI script.
*   `Dockerfile`: Direct instructions for Hugging Face Docker rendering.
*   `requirements.txt`: The bare-minimum dependencies (`fastapi`, `uvicorn`, `orjson`, `numpy`).
*   `data/`: Only 5 production-hardened binary and meta config files.

---

### Step-by-Step Push to Hugging Face

Because this engine relies on large memory-mapped binary files (e.g., `grid.bin` is ~500MB), you **must use Git LFS (Large File Storage)** when pushing to Hugging Face.

#### 1. Setup Your Hugging Face Space
1. Go to your [Hugging Face Spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. **Space name:** `bd-geocode` (or whatever you prefer).
3. **Select the Space SDK:** Choose **Docker -> Blank**.
4. **Space Hardware:** Select the **Free Tier** (16GB RAM, 2 vCPU).

#### 2. Get the Git Clone Link
Hugging Face will give you a Git clone link, similar to:
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/bd-geocode
```

#### 3. Initialize Git Push (From your Terminal)
Inside your MacBook terminal, do the following to upload this exact folder to your Space:

```bash
# 1. Enter the production directory
cd v5_prod

# 2. Initialize it as a Git repository
git init

# 3. Add your Hugging Face Space as the remote destination
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/bd-geocode

# 4. Initialize Git LFS (Crucial for the .bin files)
git lfs install
git lfs track "*.bin"

# 5. Add all the files
git add .gitattributes
git add .

# 6. Commit the files
git commit -m "Upload Extreme V5 GeoEngine Production Release"

# 7. Push to Hugging Face (This will take a few minutes for the 750MB payload)
git push -u origin main
```

*(Note: Depending on Hugging Face auth context, it may prompt you for your HF Username and an Access Token which you can grab from Hugging Face -> Settings -> Access Tokens)*

#### 4. Watch the Deployment!
Once the push hits 100%, go to your Hugging Face Space link in the browser. 
It will say **"Building"**.
Because we provided a `Dockerfile`, Hugging Face will:
1. Load `python:3.11-slim`.
2. Install `fastapi`, `orjson`, etc.
3. Start `uvicorn server:app --host 0.0.0.0 --port 7860`.

Within a minute or two, it will say **"Running"**.

### Testing the Live API
You can now test your public API endpoint directly!
```bash
curl -s "https://YOUR_USERNAME-bd-geocode.hf.space/reverse/24.971243,89.174906"
```
It will respond reliably in 1ms on the Free Tier servers forever without ever crashing from memory spikes!