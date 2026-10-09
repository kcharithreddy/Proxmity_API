import os
import csv
import math
import hashlib
from collections import deque, defaultdict
from typing import List, Dict, Tuple, Optional, Union

class LocationService:
    def __init__(self, locations_csv_path: str, default_link_path: Optional[str] = None):
        self.locations_csv_path = os.path.abspath(locations_csv_path)
        self.default_link_path = os.path.abspath(default_link_path) if default_link_path else None

        self.locations: List[Tuple[int, float, float, str]] = []
        self.id_to_index: Dict[int, int] = {}
        self.cat_to_indices: Dict[str, List[int]] = defaultdict(list)

        self._load_locations()
        self.total_locations = len(self.locations)
        self.grid_size = int(round(math.sqrt(self.total_locations))) if self.total_locations > 0 else 100
        self.max_coord_index = self.grid_size - 1

        self.graph_cache: Dict[str, List[List[int]]] = {}
        if self.default_link_path and os.path.isfile(self.default_link_path):
            self.default_adj = self.get_or_load_graph(self.default_link_path)
        else:
            self.default_adj = [[] for _ in range(self.total_locations + 1)]

    def _load_locations(self):
        with open(self.locations_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                lid = int(r["ID"])
                lat = float(r["Latitude"])
                lon = float(r["Longitude"])
                cat = r["Category"].strip().lower()

                idx = len(self.locations)
                self.locations.append((lid, lat, lon, cat))
                self.id_to_index[lid] = idx
                self.cat_to_indices[cat].append(idx)

    def get_or_load_graph(self, link_source: Optional[Union[str, bytes]]) -> List[List[int]]:
        if link_source is None:
            return self.default_adj
        if isinstance(link_source, bytes):
            link_source = link_source.decode("utf-8", errors="replace")

        link_str = link_source.strip()
        if not link_str or link_str.lower() in ("none", "null", "default"):
            return self.default_adj

        is_file = False
        resolved_path = link_str

        if "\n" not in link_str and len(link_str) < 4096:
            fname = os.path.basename(link_str)
            candidate_paths = [
                link_str,
                os.path.join(os.path.dirname(self.locations_csv_path), link_str),
                os.path.join(os.path.dirname(self.locations_csv_path), fname),
                os.path.join("/home/student", link_str),
                os.path.join("/home/student", fname),
                os.path.join("/home/student/location_api", link_str),
                os.path.join("/home/student/location_api", fname),
                os.path.join("/home/charithreddy/Downloads", link_str),
                os.path.join("/tmp", link_str)
            ]
            for candidate in candidate_paths:
                if os.path.isfile(candidate):
                    is_file = True
                    resolved_path = os.path.abspath(candidate)
                    break

        if is_file:
            mtime = os.path.getmtime(resolved_path)
            cache_key = f"file:{resolved_path}:{mtime}"
            if cache_key in self.graph_cache:
                return self.graph_cache[cache_key]
            with open(resolved_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            cache_key = f"content:{hashlib.sha256(link_str.encode()).hexdigest()}"
            if cache_key in self.graph_cache:
                return self.graph_cache[cache_key]
            content = link_str

        total_nodes = self.total_locations if self.total_locations > 0 else 10000
        adj = [[] for _ in range(total_nodes + 1)]
        g_size = self.grid_size
        max_idx = self.max_coord_index

        for line in content.splitlines():
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    lat1, lon1, lat2, lon2 = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                    i1 = max(0, min(max_idx, round(lat1 * max_idx)))
                    j1 = max(0, min(max_idx, round(lon1 * max_idx)))
                    i2 = max(0, min(max_idx, round(lat2 * max_idx)))
                    j2 = max(0, min(max_idx, round(lon2 * max_idx)))

                    if abs(i1 - i2) + abs(j1 - j2) != 1:
                        continue

                    u = i1 * g_size + j1 + 1
                    v = i2 * g_size + j2 + 1
                    if 1 <= u <= total_nodes and 1 <= v <= total_nodes:
                        adj[u].append(v)
                        adj[v].append(u)
                except (ValueError, TypeError):
                    continue
            elif len(parts) >= 2:
                try:
                    u = int(parts[0])
                    v = int(parts[1])
                    if 1 <= u <= total_nodes and 1 <= v <= total_nodes:
                        adj[u].append(v)
                        adj[v].append(u)
                except (ValueError, TypeError):
                    continue

        self.graph_cache[cache_key] = adj
        return adj

    def search(self, lat: float, lon: float, cat: str, rad: float,
               link: Optional[Union[str, bytes]] = None, top_k: int = 10) -> List[int]:
        norm_cat = cat.strip().lower()
        matching_indices = self.cat_to_indices.get(norm_cat, [])
        if not matching_indices:
            return []

        rad_sq = rad * rad + 1e-12
        valid_candidates = []
        target_ids = set()
        for idx in matching_indices:
            lid, l_lat, l_lon, _ = self.locations[idx]
            d_sq = (l_lat - lat) ** 2 + (l_lon - lon) ** 2
            if d_sq <= rad_sq:
                circ_d = math.sqrt(d_sq)
                valid_candidates.append((lid, circ_d))
                target_ids.add(lid)

        if not valid_candidates:
            return []

        adj = self.get_or_load_graph(link) if link else self.default_adj

        max_idx = self.max_coord_index
        g_size = self.grid_size
        total_nodes = self.total_locations if self.total_locations > 0 else 10000

        start_node = max(0, min(max_idx, round(lat * max_idx))) * g_size + \
                     max(0, min(max_idx, round(lon * max_idx))) + 1

        dist = [-1] * (total_nodes + 1)
        dist[start_node] = 0
        queue = deque([start_node])
        found_target_count = 0
        max_dist_at_cutoff = -1

        while queue:
            curr = queue.popleft()
            d = dist[curr]

            if curr in target_ids:
                found_target_count += 1
                if found_target_count >= top_k and max_dist_at_cutoff == -1:
                    max_dist_at_cutoff = d

            if max_dist_at_cutoff != -1 and d > max_dist_at_cutoff:
                break

            nd = d + 1
            for nxt in adj[curr]:
                if dist[nxt] == -1:
                    dist[nxt] = nd
                    queue.append(nxt)

        ranked = []
        for lid, circ_d in valid_candidates:
            g_dist = dist[lid]
            if g_dist != -1:
                ranked.append((g_dist, circ_d, lid))

        ranked.sort()
        return [lid for _, _, lid in ranked[:top_k]]
