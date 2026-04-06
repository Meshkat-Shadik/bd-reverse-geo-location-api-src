import json
import orjson
import numpy as np
import os
import time

def build_extreme_binary_dict():
    t0 = time.perf_counter()
    print("Loading master_dict.json...")
    with open("data/master_dict.json", "r", encoding="utf-8") as f:
        master_dict = json.load(f)
        
    print("Finding max ID...")
    max_id = len(master_dict) - 1
    
    # We will store a uint64 offset array: size max_id + 1
    # uint32 for length
    offsets = np.zeros(max_id + 1, dtype=np.uint64)
    lengths = np.zeros(max_id + 1, dtype=np.uint32)
    
    dict_strings_file = open("data/master_response_strings.bin", "wb")
    
    current_offset = 0
    print(f"Baking {len(master_dict)} JSON payloads...")
    # Since it's a list, we enumerate!
    for uid, data in enumerate(master_dict):
        if data is None:
            # Handle uid=0 or unmapped
            continue
        
        layer = data.pop("__layer__", "unknown")
        
        api_response = {
            "match": "exact",
            "layer": layer,
            "id": uid,
            "data": data,
        }
        
        # Serialize the JSON to bytes using orjson
        raw_json_bytes = orjson.dumps(api_response)
        
        # We strip the closing brace '}' so we can dynamically append the performance benchmark in the server!
        # Example original: b'{"match":"exact","id":123,"data":{}}'
        # Clipped: b'{"match":"exact","id":123,"data":{}'
        raw_json_bytes = raw_json_bytes[:-1]
        
        length = len(raw_json_bytes)
        
        offsets[uid] = current_offset
        lengths[uid] = length
        
        dict_strings_file.write(raw_json_bytes)
        current_offset += length
        
    dict_strings_file.close()
    
    print("Saving offset and length arrays...")
    offsets.tofile("data/master_offsets.bin")
    lengths.tofile("data/master_lengths.bin")
    
    print(f"Data conversion completed in {time.perf_counter() - t0:.2f}s!")
    print(f"Max ID is {max_id}. Offset Array Size: {offsets.nbytes/1024/1024:.2f}MB, String block size: {current_offset/1024/1024:.2f}MB")

if __name__ == "__main__":
    build_extreme_binary_dict()