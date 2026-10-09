# Proximity Search Recommendation API (CS559)

A high-performance RESTful Location Recommendation API developed for **CS559: Computer Systems Design** at IIT Bhilai.

The engine recommends the **10 closest valid locations** matching a specified category and search radius across a road network overlaid on a $100 \times 100$ spatial grid of 10,000 points.

---

## Architecture Overview

- **Spatial Indexing:** $O(1)$ bijective coordinate snapping over a uniform $[0.0, 1.0] \times [0.0, 1.0]$ planar grid ($s = \frac{1}{99} \approx 0.010101$).
- **Dual-Distance Constraint:**
  - *Circular Spatial Filtering:* $d_{\text{circ}} \le \text{rad}$
  - *Graph Traversal Ranking:* $d_{\text{road}}$ via Breadth-First Search (BFS) / Dijkstra with early level-cutoff.
- **Hardware Optimization:** Memory footprint $< 40$ MB RSS per worker process, operating well within a 512 MB RAM ceiling.
- **Production Server:** Gunicorn WSGI server (2 workers) supervised by a persistent watchdog daemon.

---

## Live Endpoint

- **Host & Port:** `http://10.1.75.51:4247/search/` (maps to Container 3 `stu12_sys3:4000`)
- **HTTP Methods:** `GET`, `POST`
- **Supported Encodings:** `application/json`, `multipart/form-data`, `application/x-www-form-urlencoded`, URL query parameters.

### Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `lat` | Float | Query latitude $[0.0, 1.0]$ |
| `long` | Float | Query longitude $[0.0, 1.0]$ |
| `cat` | String | Target category (`bank`, `hospital`, `store`, `school`, `cafe`, `pharmacy`, `restaurant`, `park`) |
| `rad` | Float | Maximum circular search radius |
| `link` | Text / File | Road network linkage data (text string or `.txt` file upload) |

### Example cURL Request

```bash
curl -X POST "http://10.1.75.51:4247/search/" \
  -F "lat=0.505051" \
  -F "long=0.505051" \
  -F "cat=hospital" \
  -F "rad=0.2" \
  -F "link=@link.txt"
```

### Example Response

```json
[5151, 5248, 5553, 4855, 5455, 4554, 5245, 5549, 5145, 5456]
```

---

## Project Structure

```
.
├── app.py                                 # Flask REST API endpoints and parameter parser
├── service.py                             # Core spatial indexing, road linkage validation & BFS search engine
├── locations.csv                          # In-memory spatial dataset (10,000 locations)
├── test_app.py                            # Automated unit tests for API and graph validation
├── test_client.py                         # 10-query regression test client across categories and radii
├── Location_Recommendation_API_Report.pdf # Comprehensive technical lab report (PDF)
├── REPORT.md                              # Technical documentation in Markdown
└── README.md                              # Project documentation
```

---

## Author

- **Student Name:** Kakarla Soma Charith Reddy
- **Student ID:** 12341040
- **Course:** CS559: Computer Systems Design
