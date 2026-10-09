import os
from flask import Flask, request, jsonify
from service import LocationService

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "locations.csv")
DEFAULT_LINK_PATH = os.path.join(BASE_DIR, "link.txt")

service = LocationService(CSV_PATH, DEFAULT_LINK_PATH)

def get_field(names, default=None):
    for name in names:
        if name in request.args:
            return request.args.get(name)
    if request.form:
        for name in names:
            if name in request.form:
                return request.form.get(name)
    if request.is_json:
        data = request.get_json(silent=True) or {}
        for name in names:
            if name in data:
                return data.get(name)
    return default

def get_link_content():
    for key in ["link", "linkage", "file", "links"]:
        if key in request.files:
            file_obj = request.files[key]
            return file_obj.read()
    raw_val = get_field(["link", "linkage", "links", "linkage_info", "road_network"])
    return raw_val if raw_val else None

@app.route("/search/", methods=["GET", "POST"])
@app.route("/search", methods=["GET", "POST"])
def search():
    try:
        lat_val = get_field(["lat", "latitude", "current_latitude"])
        long_val = get_field(["long", "lng", "lon", "longitude", "current_longitude"])
        cat_val = get_field(["cat", "category", "type"])
        rad_val = get_field(["rad", "radius", "search_radius"])

        if lat_val is None or long_val is None or cat_val is None or rad_val is None:
            return jsonify({"error": "Missing required parameters: lat, long, cat, rad"}), 400

        lat = float(lat_val)
        lon = float(long_val)
        cat = str(cat_val).strip()
        rad = float(rad_val)
        link = get_link_content()

        top_10 = service.search(lat=lat, lon=lon, cat=cat, rad=rad, link=link, top_k=10)

        fmt = get_field(["format"], "").lower()
        if fmt in ("dict", "object", "json_object"):
            return jsonify({
                "recommended_locations": top_10,
                "locations": top_10,
                "ids": top_10
            })

        return jsonify(top_10)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Location Recommendation API", "locations_count": service.total_locations})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    app.run(host="0.0.0.0", port=port)
