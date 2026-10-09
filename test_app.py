import unittest
import json
import math
import io
from app import app, coords, categories

class LocationApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_check(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["locations_count"], 10000)

    def test_grid_search_with_links(self):
        # Create a linear road network around node 1
        # 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> ... -> 25
        links = []
        for i in range(1, 200):
            links.append(f"{i} {i+1}")
            # Also vertical links
            if i + 100 <= 10000:
                links.append(f"{i} {i+100}")
        link_str = "\n".join(links)

        # Test query
        # Current location at node 1 (0.0, 0.0), looking for banks within radius 0.2
        params = {
            "lat": 0.0,
            "long": 0.0,
            "cat": "bank",
            "rad": 0.3,
            "link": link_str
        }

        # Query via JSON POST
        res = self.client.post("/search/", json=params)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertLessEqual(len(data), 10)

        # Verify each returned ID
        for loc_id in data:
            self.assertEqual(categories[loc_id], "bank")
            lat, lng = coords[loc_id]
            dist = math.hypot(lat - 0.0, lng - 0.0)
            self.assertLessEqual(dist, 0.3 + 1e-9)

    def test_search_multipart_file_upload(self):
        # Road linkage file upload test
        links = "1 2\n2 3\n3 4\n4 5\n5 6\n6 7\n7 8\n8 9\n9 10\n10 11\n11 12\n12 13\n13 14\n14 15\n15 16\n16 17\n17 18\n18 19\n19 20\n20 21\n21 22\n22 23\n23 24\n24 25"
        data = {
            "lat": "0.0",
            "long": "0.0",
            "cat": "school",
            "rad": "0.5",
            "link": (io.BytesIO(links.encode("utf-8")), "network.txt")
        }
        res = self.client.post("/search/", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        result = res.get_json()
        self.assertIsInstance(result, list)
        for loc_id in result:
            self.assertEqual(categories[loc_id], "school")

    def test_missing_params(self):
        res = self.client.get("/search/?lat=0.0&long=0.0")
        self.assertEqual(res.status_code, 400)

if __name__ == "__main__":
    unittest.main()
