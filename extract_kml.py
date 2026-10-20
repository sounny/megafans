import xml.etree.ElementTree as ET
import json

tree = ET.parse('/Users/sounny/Library/CloudStorage/GoogleDrive-sounny@gmail.com/My Drive/Megafans/GIS/EarthEngine/MJRMegafans.kml')
root = tree.getroot()

ns = {'kml': 'http://www.opengis.net/kml/2.2'}

megafans = []

for placemark in root.findall('.//kml:Placemark', ns):
    name_el = placemark.find('kml:name', ns)
    if name_el is None: continue
    name = name_el.text
    
    coords_el = placemark.find('.//kml:coordinates', ns)
    if coords_el is not None:
        coords_str = coords_el.text.strip().split()
        lats = []
        lons = []
        for c in coords_str:
            parts = c.split(',')
            if len(parts) >= 2:
                lons.append(float(parts[0]))
                lats.append(float(parts[1]))
        if lats and lons:
            avg_lat = sum(lats) / len(lats)
            avg_lon = sum(lons) / len(lons)
            
            megafans.append({
                "id": name.lower().replace(' ', '-'),
                "name": name + " Megafan",
                "location": "TBD",
                "coords": [round(avg_lat, 4), round(avg_lon, 4)],
                "description": f"The {name} megafan was mapped in Dr. Sounny's dissertation research on terrestrial megafans.",
                "tags": ["Terrestrial", "Dissertation Data"]
            })

print(json.dumps(megafans, indent=2))
