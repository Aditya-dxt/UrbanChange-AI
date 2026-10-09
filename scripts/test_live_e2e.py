import urllib.request
import json
import time
import uuid
import sys

def run_pair(name, before_file, after_file, content_type='image/png', pixel_size='0.5', bbox=None):
    print(f'\n======================================================')
    print(f'Testing: {name}')
    print(f'======================================================')
    fields = {'name': name}
    if pixel_size:
        fields['pixel_size_m'] = pixel_size
    if bbox:
        fields['bbox'] = json.dumps(bbox)
        
    upload_res = post_multipart(
        'http://localhost:8080/api/investigations/upload',
        files={'before': before_file, 'after': after_file},
        fields=fields,
        content_type=content_type
    )
    inv_id = upload_res['id']
    print(f'1. Created investigation {inv_id}')
    
    req = urllib.request.Request(f'http://localhost:8080/api/investigations/{inv_id}/run', data=b'', method='POST')
    urllib.request.urlopen(req)
    print(f'2. Enqueued detection pipeline...')
    
    final_res = {}
    for i in range(45):
        time.sleep(1)
        res = json.loads(urllib.request.urlopen(f'http://localhost:8080/api/investigations/{inv_id}').read().decode())
        if res.get('status') in ('completed', 'failed'):
            final_res = res
            print(f'3. Pipeline finished in {i+1}s with status: {res.get("status")}')
            break
            
    det = final_res.get('detection', {})
    print(f'   Change Detected: {det.get("change_detected")}')
    print(f'   Confidence: {det.get("confidence")}')
    print(f'   Changed Pixels: {det.get("changed_area_pixels")}')
    print(f'   Regions: {len(det.get("change_regions", []))}')
    print(f'   Classification: {det.get("classification")}')
    
    gis_res = final_res.get('gis', {})
    if gis_res:
        print(f'   GIS Overlaps: {len(gis_res.get("sensitive_overlaps", []))}')
    
    fp = final_res.get('fingerprint', {})
    if fp:
        print(f'   Fingerprint: {fp.get("fingerprint_id")} | {fp.get("change_type")} | {fp.get("temporal_behavior")}')
    return final_res

def post_multipart(url, files, fields, content_type='image/png'):
    boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8'))
    for name, filepath in files.items():
        filename = filepath.split('/')[-1].split('\\')[-1]
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode('utf-8'))
        with open(filepath, 'rb') as f:
            body.extend(f.read())
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_test():
    # Test 1: Urban Construction Pair
    run_pair(
        'Pair 01: Urban Construction',
        'sample_data/pairs/pair_01_construction/before.png',
        'sample_data/pairs/pair_01_construction/after.png',
        content_type='image/png',
        pixel_size='0.5'
    )
    
    # Test 2: Stable / No-Change Pair
    run_pair(
        'Pair 04: Stable No Change',
        'sample_data/pairs/pair_04_no_change/before.png',
        'sample_data/pairs/pair_04_no_change/after.png',
        content_type='image/png',
        pixel_size='0.5'
    )

    # Test 3: Real Sentinel-2 4-Band GeoTIFF Stack
    run_pair(
        'Pair 05: Sentinel-2 GeoTIFF Stack (Kanpur, India)',
        'sample_data/pairs/pair_05_sentinel2_geotiff/before.tif',
        'sample_data/pairs/pair_05_sentinel2_geotiff/after.tif',
        content_type='image/tiff',
        pixel_size=None,
        bbox=[80.30, 26.40, 80.40, 26.50]
    )

if __name__ == '__main__':
    run_test()
