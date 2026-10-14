import urllib.request
import json
import time
from pathlib import Path


def run_test(name, b_file, a_file):
    boundary = "----WebKitFormBoundaryXyZ123456789"
    with open(b_file, "rb") as f:
        b_bytes = f.read()
    with open(a_file, "rb") as f:
        a_bytes = f.read()

    b_name = Path(b_file).name
    a_name = Path(a_file).name
    b_mime = "image/tiff" if b_name.endswith((".tif", ".tiff")) else "image/png"
    a_mime = "image/tiff" if a_name.endswith((".tif", ".tiff")) else "image/png"

    body = bytearray()
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="before"; filename="{b_name}"\r\nContent-Type: {b_mime}\r\n\r\n'.encode())
    body.extend(b_bytes)
    body.extend(b"\r\n")

    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="after"; filename="{a_name}"\r\nContent-Type: {a_mime}\r\n\r\n'.encode())
    body.extend(a_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"historical_date\"\r\n\r\n2023-01-01\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"current_date\"\r\n\r\n2024-01-01\r\n".encode())
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request("http://localhost:8080/api/investigations/upload", data=bytes(body))
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    with urllib.request.urlopen(req) as resp:
        upload_res = json.loads(resp.read().decode())
        inv_id = upload_res["id"]
        print(f"[{name}] Created investigation {inv_id}")

    # Call /run
    run_req = urllib.request.Request(f"http://localhost:8080/api/investigations/{inv_id}/run", data=b"", method="POST")
    t0 = time.time()
    with urllib.request.urlopen(run_req) as resp:
        print(f"[{name}] Run triggered: HTTP {resp.status}")

    # Poll status
    for i in range(40):
        time.sleep(1.0)
        with urllib.request.urlopen(f"http://localhost:8080/api/investigations/{inv_id}") as resp:
            data = json.loads(resp.read().decode())
            st = data.get("status")
            if st in ("completed", "failed"):
                elapsed = time.time() - t0
                ml_res = data.get("detection") or {}
                print(f"[{name}] Status: {st} in {elapsed:.2f}s")
                print(f"[{name}] ML Change Detected: {ml_res.get('change_detected')}")
                print(f"[{name}] ML Confidence: {ml_res.get('confidence')}")
                print(f"[{name}] ML Classification: {ml_res.get('classification')}")
                print(f"[{name}] ML Region Count: {len(ml_res.get('change_regions', []))}")
                print(f"[{name}] ML Changed Pixels: {ml_res.get('changed_area_pixels')}")
                print(f"[{name}] ML Model Version: {ml_res.get('model_version')}")
                if data.get("error"):
                    print(f"[{name}] Error: {data.get('error')}")
                return data
    print(f"[{name}] Timeout waiting for completion")
    return None


if __name__ == "__main__":
    print("=== TESTING SAMPLE 1: CONSTRUCTION ===")
    s1 = run_test("Sample 1", "sample_data/pairs/pair_01_construction/before.png", "sample_data/pairs/pair_01_construction/after.png")

    print("\n=== TESTING SAMPLE 2: FOREST CLEARING (DEFORESTATION) ===")
    s2 = run_test("Sample 2", "sample_data/pairs/pair_02_deforestation/before.png", "sample_data/pairs/pair_02_deforestation/after.png")
