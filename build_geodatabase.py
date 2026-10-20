import csv
import json
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
import openpyxl

MEGAFANS_ROOT = r"g:\My Drive\Megafans"
REPO_ROOT = r"g:\My Drive\git\megafans"
SITE_ROOT = r"g:\My Drive\megafans_site"

# Clean up any accidental shell redirection artifacts in MEGAFANS_ROOT
for bad_name in ["=3", "I'", "name"]:
    bad_path = os.path.join(MEGAFANS_ROOT, bad_name)
    if os.path.exists(bad_path) and os.path.isfile(bad_path):
        try:
            os.remove(bad_path)
        except Exception:
            pass

# 1. Copy authentic dissertation regional maps & hero image into public/assets
assets_dst = os.path.join(REPO_ROOT, "public", "assets")
os.makedirs(assets_dst, exist_ok=True)

sitemap_copies = [
    (os.path.join(MEGAFANS_ROOT, "SiteMap", "Chaco.png"), "chaco_map.png"),
    (os.path.join(MEGAFANS_ROOT, "SiteMap", "Okavango.png"), "okavango_map.png"),
    (os.path.join(MEGAFANS_ROOT, "SiteMap", "Pantanal3.png"), "pantanal_map.png"),
    (os.path.join(MEGAFANS_ROOT, "SiteMap", "Himalayas.png"), "himalayas_map.png"),
    (os.path.join(MEGAFANS_ROOT, "SiteMap", "Sahel.png"), "sahel_map.png"),
    (os.path.join(MEGAFANS_ROOT, "BeutifulFans", "MegafanDatabase.jpg"), "megafan_database.jpg"),
    (os.path.join(MEGAFANS_ROOT, "Maps", "Pico_Polu_color.jpg"), "pilcomayo.jpg"),
]

for src, dst_name in sitemap_copies:
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(assets_dst, dst_name))

# 2. Extract polygon footprints from MJRMegafans.kml and Megafans.kmz
ns = {"kml": "http://www.opengis.net/kml/2.2"}
geojson_features = []
seen_poly_names = set()

kml_path = os.path.join(MEGAFANS_ROOT, "GIS", "EarthEngine", "MJRMegafans.kml")
if os.path.exists(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()
    for pm in root.findall(".//kml:Placemark", ns):
        name_el = pm.find("kml:name", ns)
        if name_el is None or not name_el.text:
            continue
        name = name_el.text.strip()
        coords_el = pm.find(".//kml:coordinates", ns)
        if coords_el is None or not coords_el.text:
            continue
        ring = []
        for token in coords_el.text.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                lon, lat = round(float(parts[0]), 5), round(float(parts[1]), 5)
                ring.append([lon, lat])
        # Simplify very dense rings slightly to keep GeoJSON fast while preserving shape
        if len(ring) > 600:
            step = max(1, len(ring) // 400)
            simplified = ring[::step]
            if simplified[-1] != ring[-1]:
                simplified.append(ring[-1])
            ring = simplified
        if len(ring) >= 4:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            seen_poly_names.add(name.lower())
            geojson_features.append({
                "type": "Feature",
                "properties": {
                    "name": f"{name} Megafan",
                    "shortName": name,
                    "source": "Sounny-Slitine (2020) Dissertation KML"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring]
                }
            })

# Also extract additional polygons from Megafans.kmz
kmz_path = os.path.join(MEGAFANS_ROOT, "GIS", "GEarth", "Megafans.kmz")
if os.path.exists(kmz_path):
    with zipfile.ZipFile(kmz_path, "r") as z:
        raw_kml = z.read("doc.kml").decode("utf-8", errors="ignore")
        # Strip unbound xsi prefix if present
        raw_kml = re.sub(r'\s+xsi:[a-zA-Z0-9_]+="[^"]*"', "", raw_kml)
        try:
            kroot = ET.fromstring(raw_kml)
            for pm in kroot.findall(".//kml:Placemark", ns):
                name_el = pm.find("kml:name", ns)
                if name_el is None or not name_el.text:
                    continue
                raw_name = name_el.text.strip()
                clean_name = re.sub(r"(_vec|_eder|\.shp)+", "", raw_name, flags=re.IGNORECASE).strip()
                if clean_name.lower() in seen_poly_names:
                    continue
                poly_el = pm.find(".//kml:Polygon//kml:coordinates", ns)
                if poly_el is None or not poly_el.text:
                    continue
                ring = []
                for token in poly_el.text.strip().split():
                    parts = token.split(",")
                    if len(parts) >= 2:
                        lon, lat = round(float(parts[0]), 5), round(float(parts[1]), 5)
                        ring.append([lon, lat])
                if len(ring) > 600:
                    step = max(1, len(ring) // 400)
                    simplified = ring[::step]
                    if simplified[-1] != ring[-1]:
                        simplified.append(ring[-1])
                    ring = simplified
                if len(ring) >= 4:
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                    seen_poly_names.add(clean_name.lower())
                    geojson_features.append({
                        "type": "Feature",
                        "properties": {
                            "name": f"{clean_name} Megafan",
                            "shortName": clean_name,
                            "source": "Sounny-Slitine (2020) Vector Geodatabase"
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [ring]
                        }
                    })
        except Exception as e:
            print("KMZ parse note:", e)

geojson_out = os.path.join(REPO_ROOT, "public", "data", "megafans_polygons.geojson")
with open(geojson_out, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": geojson_features}, f)
print(f"Exported {len(geojson_features)} megafan polygon footprints to megafans_polygons.geojson")

# 3. Inspect and load all rows from Metrics5.xlsx, Apexs1.csv, APEXTOES3.csv, and original curated catalog.json
orig_catalog_path = os.path.join(SITE_ROOT, "public", "data", "catalog.json")
existing_catalog_path = os.path.join(REPO_ROOT, "public", "data", "catalog.json")
existing_catalog = json.load(open(orig_catalog_path, encoding="utf-8"))

# Build lookup of existing curated catalog entries by normalized name
def norm_key(s):
    if not s:
        return ""
    s = s.lower().replace("megafan", "").replace("delta", "").replace("river", "").replace("fan", "")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s.strip()

curated_by_key = {}
for item in existing_catalog:
    k = norm_key(item["name"])
    curated_by_key[k] = item
    # Also alias common variations
    if item["id"] == "rio-grande":
        curated_by_key["grande"] = item
    elif item["id"] == "salado-juramento":
        curated_by_key["juramento"] = item
    elif item["id"] == "sharda":
        curated_by_key["sarda"] = item
    elif item["id"] == "ganga":
        curated_by_key["gangayamuna"] = item
    elif item["id"] == "ili-megafan":
        curated_by_key["ili"] = item

# Load fallback coordinates from Apexs1.csv and APEXTOES3.csv
apexs1_coords = {}
for csv_name in ["Apexs1.csv", "APEXTOES3.csv"]:
    csv_path = os.path.join(MEGAFANS_ROOT, "MegafanDB", csv_name)
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8", errors="ignore") as f:
            for row in list(csv.reader(f))[1:]:
                if len(row) >= 3 and row[0].strip():
                    try:
                        lon = float(row[1])
                        lat = float(row[2])
                        apexs1_coords[row[0].strip().lower()] = (round(lat, 4), round(lon, 4))
                        apexs1_coords[norm_key(row[0])] = (round(lat, 4), round(lon, 4))
                    except ValueError:
                        pass

# Also compute centroids from MJRMegafans.kml / Megafans.kmz polygons as fallback
for feat in geojson_features:
    sname = feat["properties"]["shortName"]
    ring = feat["geometry"]["coordinates"][0]
    avg_lon = round(sum(p[0] for p in ring) / len(ring), 4)
    avg_lat = round(sum(p[1] for p in ring) / len(ring), 4)
    if norm_key(sname) not in apexs1_coords:
        apexs1_coords[norm_key(sname)] = (avg_lat, avg_lon)

# Literature coordinates (Wilkinson et al. 2006/2010; Sounny-Slitine 2020) for rows without inline lat/lon
lit_coords = {
    "tsondab": (-23.90, 15.35, "Africa", "Namibia", "Namib Erg"),
    "brenta": (45.65, 11.78, "Europe", "Italy", "Alps"),
    "cunene": (-17.25, 14.50, "Africa", "Angola / Namibia", "Ovambo Basin"),
    "demini": (0.75, -62.60, "South America", "Brazil", "Northern Amazon"),
    "farhana": (12.60, 21.90, "Africa", "Chad", "Sahel"),
    "otuquis": (-19.50, -58.50, "South America", "Bolivia", "Pantanal"),
    "sobat": (8.80, 32.50, "Africa", "South Sudan", "White Nile / Sudd"),
    "sudd": (7.50, 30.50, "Africa", "South Sudan", "White Nile / Sudd"),
    "tarimnnorth": (41.10, 82.50, "Asia", "China", "Tarim Basin"),
    "tarimsouth": (37.20, 81.50, "Asia", "China", "Tarim Basin"),
    "virua": (1.30, -61.15, "South America", "Brazil", "Northern Amazon"),
    "viru": (1.30, -61.15, "South America", "Brazil", "Northern Amazon"),
    "wadiarab": (12.00, 25.00, "Africa", "Sudan", "Sahel"),
}
for lk, (llat, llon, _, _, _) in lit_coords.items():
    apexs1_coords[lk] = (llat, llon)

# Read Metrics5.xlsx DB sheet
wb5 = openpyxl.load_workbook(os.path.join(MEGAFANS_ROOT, "MegafanDB", "Metrics5.xlsx"), read_only=True, data_only=True)
ws5 = wb5["DB"]
rows5 = list(ws5.iter_rows(values_only=True, max_row=600))
headers5 = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows5[0])]

def safe_float(v, digits=4):
    if v is None or v == "":
        return None
    try:
        val = float(v)
        if val != val:  # NaN check
            return None
        return round(val, digits)
    except (ValueError, TypeError):
        return None

def safe_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() != "none" else None

# Regional map image fallback by system/region
def get_regional_image(fan_name, continent, system, country):
    fn_low = (fan_name or "").lower()
    sys_low = (system or "").lower()
    if any(k in fn_low for k in ["pilcomayo"]):
        return "public/assets/pilcomayo.jpg", "NASA / Chaco DEM Analysis"
    if any(k in fn_low for k in ["okavango", "cuando", "zambezi"]):
        return "public/assets/okavango_map.png", "Sounny-Slitine (2020) Dissertation Atlas"
    if any(k in fn_low for k in ["taquari", "paraguay", "são lourenço", "sao lourenco", "cuiaba", "aquiduana", "taboco", "tucavaca", "lomarina", "san fernando"]):
        return "public/assets/pantanal_map.png", "Sounny-Slitine (2020) Dissertation Atlas"
    if any(k in fn_low for k in ["grande", "parapeti", "bermejo", "juramento", "salado", "dulce", "itiyura", "horcones", "delvalle"]):
        return "public/assets/chaco_map.png", "Sounny-Slitine (2020) Dissertation Atlas"
    if "himalaya" in sys_low or any(k in fn_low for k in ["kosi", "gandak", "tista", "sarda", "sharda", "ganga", "son"]):
        return "public/assets/himalayas_map.png", "Sounny-Slitine (2020) Dissertation Atlas"
    if any(k in fn_low for k in ["bahr", "batha", "chari", "logone", "ouham", "wadi howar", "white nile", "blue nile", "khor", "yedseram", "kidepo", "lol", "jur"]):
        return "public/assets/sahel_map.png", "Sounny-Slitine (2020) Dissertation Atlas"
    return None, None

all_earth_fans = []
used_curated_ids = set()

for idx, r in enumerate(rows5[1:]):
    if not r or not r[0]:
        continue
    raw_name = str(r[0]).strip()
    lon = safe_float(r[1], 4)
    lat = safe_float(r[2], 4)
    apex_lat = safe_float(r[8], 4)
    apex_lon = safe_float(r[9], 4)
    toe_lat = safe_float(r[10], 4)
    toe_lon = safe_float(r[11], 4)

    if lat is None or lon is None:
        if apex_lat is not None and apex_lon is not None:
            lat, lon = apex_lat, apex_lon
        elif toe_lat is not None and toe_lon is not None:
            lat, lon = toe_lat, toe_lon
        elif raw_name.lower() in apexs1_coords:
            lat, lon = apexs1_coords[raw_name.lower()]
        elif norm_key(raw_name) in apexs1_coords:
            lat, lon = apexs1_coords[norm_key(raw_name)]

    # Fix swapped lat/lon if lat is out of [-90, 90] (e.g. Limpopo in spreadsheet had Long=-24.54, Lat=33.6)
    if raw_name.lower() == "limpopo" and lat == 33.6 and lon == -24.54:
        lat, lon = -24.54, 33.6

    if lat is None or lon is None:
        print("Un-georeferenced row in Metrics5.xlsx:", raw_name, r[3], r[4], r[5])
        continue

    lit_meta = lit_coords.get(norm_key(raw_name))
    continent = safe_str(r[3]) or (lit_meta[2] if lit_meta else None)
    country = safe_str(r[4]) or (lit_meta[3] if lit_meta else None)
    system = safe_str(r[5]) or (lit_meta[4] if lit_meta else None)
    length_km = safe_float(r[6], 1)
    gradient = safe_float(r[7], 6)
    elev_apex = safe_float(r[12], 0)
    elev_toe = safe_float(r[13], 0)
    relief_m = safe_float(r[14], 0)
    area_km2 = safe_float(r[15], 1)
    catchment_km2 = safe_float(r[16], 1) or safe_float(r[17], 1)
    stream_len_km = safe_float(r[18], 1)
    drainage_density = safe_float(r[19], 3)
    circularity = safe_float(r[21], 3)
    apex_type = safe_str(r[22])
    basin_type = safe_str(r[23])
    tectonic = safe_str(r[24])
    drainage_type = safe_str(r[25])
    termination = safe_str(r[26])
    climate_catchment = safe_str(r[28])
    climate_basin = safe_str(r[29])
    channel_pattern = safe_str(r[31])

    key = norm_key(raw_name)
    curated = curated_by_key.get(key)
    if curated:
        used_curated_ids.add(curated["id"])

    # Build human-readable location
    loc_parts = [p for p in [country, continent] if p and p.lower() != "okavango"]
    location_str = curated["location"] if (curated and curated.get("location")) else (", ".join(loc_parts) if loc_parts else (system or "Global Terrestrial Database"))

    # Build display name
    display_name = curated["name"] if curated else (raw_name if "fan" in raw_name.lower() else f"{raw_name} Megafan")

    # Build rich description grounded in actual metrics
    if curated and curated.get("description") and not curated["description"].endswith("research on terrestrial megafans."):
        desc = curated["description"]
    else:
        metrics_clauses = []
        if area_km2:
            metrics_clauses.append(f"a planform area of {area_km2:,.1f} km²")
        if length_km:
            metrics_clauses.append(f"an apex-to-toe length of {length_km:,.1f} km")
        if catchment_km2:
            metrics_clauses.append(f"a contributing catchment basin of {catchment_km2:,.1f} km²")
        if relief_m is not None and elev_apex is not None and elev_toe is not None:
            metrics_clauses.append(f"vertical relief of {int(relief_m)} m ({int(elev_apex)} m apex to {int(elev_toe)} m toe)")
        elif relief_m is not None:
            metrics_clauses.append(f"vertical relief of {int(relief_m)} m")
        sys_phrase = f" associated with the {system} system" if system else ""
        loc_phrase = f" in {location_str}" if location_str and location_str != "Global Terrestrial Database" else ""
        if metrics_clauses:
            desc = f"{display_name}{loc_phrase}{sys_phrase}, characterized in the Sounny-Slitine (2020) Global Megafan Geodatabase with {', '.join(metrics_clauses)}."
        else:
            desc = f"{display_name}{loc_phrase}{sys_phrase}, cataloged in the Sounny-Slitine (2020) Global Megafan Geodatabase."

    # Image & sensor
    img_url = curated.get("imageUrl") if curated else None
    img_src = curated.get("imageSource") if curated else None
    sensor = curated.get("sensor") if curated else None

    if img_url and not os.path.exists(os.path.join(REPO_ROOT, img_url)):
        img_url = None

    if not img_url:
        reg_img, reg_src = get_regional_image(raw_name, continent, system, country)
        if reg_img:
            img_url = reg_img
            img_src = reg_src
            sensor = sensor or "Landsat / SRTM DEM"

    # Tags
    tags = list(curated.get("tags", [])) if curated else []
    for cand_tag in [system, continent, country, channel_pattern, termination]:
        if cand_tag and cand_tag not in tags and len(tags) < 4:
            tags.append(cand_tag)
    if not tags:
        tags = ["Terrestrial Megafan", "Geodatabase"]

    has_custom_photo = bool(img_url and not img_url.endswith("_map.png"))
    is_featured = has_custom_photo or (area_km2 is not None and area_km2 >= 2000) or (raw_name.lower() in seen_poly_names)

    fan_entry = {
        "id": curated["id"] if curated else f"earth-{idx+1}-{re.sub(r'[^a-z0-9]+', '-', raw_name.lower()).strip('-')}",
        "name": display_name,
        "rawName": raw_name,
        "location": location_str,
        "continent": continent or "Unspecified",
        "country": country or "Unspecified",
        "system": system or "Continental Foreland",
        "coords": [lat, lon],
        "apexCoords": [apex_lat, apex_lon] if (apex_lat is not None and apex_lon is not None) else None,
        "toeCoords": [toe_lat, toe_lon] if (toe_lat is not None and toe_lon is not None) else None,
        "lengthKm": length_km,
        "gradient": gradient,
        "elevApexM": elev_apex,
        "elevToeM": elev_toe,
        "reliefM": relief_m,
        "areaKm2": area_km2,
        "catchmentKm2": catchment_km2,
        "streamLengthKm": stream_len_km,
        "drainageDensity": drainage_density,
        "circularity": circularity,
        "channelPattern": channel_pattern,
        "termination": termination,
        "climate": climate_basin or climate_catchment,
        "imageUrl": img_url,
        "imageSource": img_src,
        "sensor": sensor or ("Landsat / SRTM DEM" if area_km2 else "Global Geodatabase"),
        "description": desc,
        "tags": tags,
        "featured": is_featured,
        "hasPolygon": raw_name.lower() in seen_poly_names
    }
    all_earth_fans.append(fan_entry)

# Also preserve any curated entries from existing catalog.json that weren't in Metrics5.xlsx (e.g. NASA Earth Observatory featured fans)
for item in existing_catalog:
    if item["id"] not in used_curated_ids:
        img_url = item.get("imageUrl")
        if img_url and not os.path.exists(os.path.join(REPO_ROOT, img_url)):
            img_url = "public/assets/chaco_map.png"
        all_earth_fans.insert(0, {
            "id": item["id"],
            "name": item["name"],
            "rawName": item["name"],
            "location": item["location"],
            "continent": "Asia" if any(k in item["location"] for k in ["Iran", "Kazakhstan", "China", "India"]) else "South America",
            "country": item["location"].split(",")[-1].strip(),
            "system": item["tags"][0] if item.get("tags") else "Featured System",
            "coords": item["coords"],
            "apexCoords": None,
            "toeCoords": None,
            "lengthKm": 230.0 if item["id"] == "ili-megafan" else None,
            "gradient": None,
            "elevApexM": None,
            "elevToeM": None,
            "reliefM": None,
            "areaKm2": None,
            "catchmentKm2": None,
            "streamLengthKm": None,
            "drainageDensity": None,
            "circularity": None,
            "channelPattern": None,
            "termination": None,
            "climate": None,
            "imageUrl": img_url,
            "imageSource": item.get("imageSource"),
            "sensor": item.get("sensor", "Satellite Imagery"),
            "description": item["description"],
            "tags": item.get("tags", []),
            "featured": True,
            "hasPolygon": False
        })

# Sort so featured fans with imagery appear first in the sidebar, followed by largest planform area, then alphabetical
all_earth_fans.sort(key=lambda x: (
    0 if (x.get("featured") and x.get("imageUrl") and not x["imageUrl"].endswith("_map.png")) else (1 if x.get("featured") else 2),
    -(x.get("areaKm2") or 0),
    -(x.get("lengthKm") or 0),
    x["name"]
))

with open(existing_catalog_path, "w", encoding="utf-8") as f:
    json.dump(all_earth_fans, f, indent=2)

print(f"Total Earth fans written to catalog.json: {len(all_earth_fans)}")
print(f"Featured Earth fans: {sum(1 for x in all_earth_fans if x.get('featured'))}")
print(f"With Area (km2): {sum(1 for x in all_earth_fans if x.get('areaKm2'))}")
print(f"With Length (km): {sum(1 for x in all_earth_fans if x.get('lengthKm'))}")
