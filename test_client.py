import urllib.request
import urllib.parse
import json
import csv
import math
import random
import time
import uuid

BASE_URL = "http://10.1.75.51:4247/search/"

# Load local locations for ground-truth verification
locations = {}
with open("/home/charithreddy/Desktop/CSD_Assisgnment/locations.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        loc_id = int(r["ID"])
        locations[loc_id] = {
            "lat": float(r["Latitude"]),
            "lng": float(r["Longitude"]),
            "cat": r["Category"].strip().lower()
        }

# Generate a synthetic grid road network with random missing links
def generate_road_network(missing_ratio=0.15):
    edges = []
    random.seed(42)
    for i in range(100):
        for j in range(100):
            u = i * 100 + j + 1
            # Horizontal link
            if j + 1 < 100:
                v = i * 100 + (j + 1) + 1
                if random.random() >= missing_ratio:
                    edges.append(f"{u} {v}")
            # Vertical link
            if i + 1 < 100:
                v = (i + 1) * 100 + j + 1
                if random.random() >= missing_ratio:
                    edges.append(f"{u} {v}")
    return "\n".join(edges)

def query_api_with_retry(make_req_fn, max_attempts=8):
    last_err = None
    for attempt in range(max_attempts):
        try:
            req = make_req_fn()
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except Exception as e:
            last_err = e
            time.sleep(0.3)
    raise RuntimeError(f"Failed to query API after {max_attempts} attempts: {last_err}")

def main():
    print("Generating test road network...")
    network_str = generate_road_network()
    print(f"Network has {len(network_str.splitlines())} road links.\n")

    test_queries = [
        {"lat": 0.0, "long": 0.0, "cat": "bank", "rad": 0.3, "method": "json"},
        {"lat": 0.505051, "long": 0.505051, "cat": "hospital", "rad": 0.25, "method": "json"},
        {"lat": 0.202020, "long": 0.202020, "cat": "restaurant", "rad": 0.35, "method": "form"},
        {"lat": 0.707071, "long": 0.707071, "cat": "store", "rad": 0.3, "method": "multipart"},
        {"lat": 0.101010, "long": 0.808081, "cat": "park", "rad": 0.4, "method": "get"},
        {"lat": 0.909091, "long": 0.101010, "cat": "school", "rad": 0.35, "method": "json"},
        {"lat": 0.353535, "long": 0.656566, "cat": "cafe", "rad": 0.3, "method": "form"},
        {"lat": 0.606061, "long": 0.404040, "cat": "pharmacy", "rad": 0.35, "method": "multipart"},
        {"lat": 0.858586, "long": 0.858586, "cat": "bank", "rad": 0.4, "method": "get"},
        {"lat": 0.454545, "long": 0.454545, "cat": "store", "rad": 0.3, "method": "json"},
    ]

    for idx, q in enumerate(test_queries, 1):
        lat = q["lat"]
        lng = q["long"]
        cat = q["cat"]
        rad = q["rad"]
        method = q["method"]

        print(f"Running Test Query {idx}/10: ({lat:.4f}, {lng:.4f}), cat='{cat}', rad={rad}, via {method}...")

        def create_request():
            if method == "json":
                payload = json.dumps({
                    "lat": lat, "long": lng, "cat": cat, "rad": rad, "link": network_str
                }).encode("utf-8")
                return urllib.request.Request(
                    BASE_URL, data=payload,
                    headers={"Content-Type": "application/json", "Connection": "close"}
                )
            elif method == "form":
                post_data = urllib.parse.urlencode({
                    "lat": str(lat), "long": str(lng), "cat": cat, "rad": str(rad), "link": network_str
                }).encode("utf-8")
                return urllib.request.Request(
                    BASE_URL, data=post_data,
                    headers={"Connection": "close"}
                )
            elif method == "multipart":
                boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
                body = (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="lat"\r\n\r\n{lat}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="long"\r\n\r\n{lng}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="cat"\r\n\r\n{cat}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="rad"\r\n\r\n{rad}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="link"; filename="roads.txt"\r\n'
                    f"Content-Type: text/plain\r\n\r\n{network_str}\r\n"
                    f"--{boundary}--\r\n"
                ).encode("utf-8")
                return urllib.request.Request(
                    BASE_URL, data=body,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Connection": "close"}
                )
            elif method == "get":
                params = urllib.parse.urlencode({
                    "lat": str(lat), "long": str(lng), "cat": cat, "rad": str(rad), "link": "roads.txt"
                })
                return urllib.request.Request(
                    f"{BASE_URL}?{params}",
                    headers={"Connection": "close"}
                )

        res = query_api_with_retry(create_request)

        # Verification
        assert isinstance(res, list), f"Response must be a list, got {type(res)}"
        assert len(res) == 10, f"Expected 10 locations, got {len(res)}"

        for loc_id in res:
            assert loc_id in locations, f"Location ID {loc_id} not in dataset"
            actual_cat = locations[loc_id]["cat"]
            assert actual_cat == cat, f"Location ID {loc_id} category mismatch: {actual_cat} != {cat}"
            nlat = locations[loc_id]["lat"]
            nlng = locations[loc_id]["lng"]
            circ = math.hypot(nlat - lat, nlng - lng)
            assert circ <= rad + 1e-9, f"Location ID {loc_id} outside radius: {circ} > {rad}"

        print(f"  ✓ Query {idx} Passed: Returned {res}")

    print("\n==========================================")
    print("ALL 10 TEST QUERIES PASSED WITH 100% ACCURACY!")
    print("==========================================")

if __name__ == "__main__":
    main()
