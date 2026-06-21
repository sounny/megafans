import csv
import json
import os

input_csv = '/Users/sounny/Library/CloudStorage/GoogleDrive-sounny@gmail.com/My Drive/Megafans/student work/luis/Fans_JMars_3.csv'
output_json = '/Users/sounny/Library/CloudStorage/GoogleDrive-sounny@gmail.com/My Drive/git/megafans/public/data/mars_catalog.json'

fans = []

with open(input_csv, 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        try:
            lat = float(row['latitude'])
            lon = float(row['longitude'])
        except ValueError:
            continue
            
        crater = row.get('crater_name', '').strip()
        crater_name = crater if crater else f"Unnamed Crater {i}"
        
        unit = row.get('TANAKA_UNIT', '').strip()
        desc = row.get('TANAKA_UNIT_DESCRIPTION', '').strip()
        azimuth = row.get('AZIMUTH_BEARING', '').strip()
        
        description_text = f"Located in geologic unit {unit} ({desc})."
        if azimuth:
            description_text += f" Azimuth Bearing: {azimuth}°."

        fan = {
            "id": f"mars-fan-{i}",
            "name": f"Martian Fan at {crater_name}",
            "location": f"Mars ({unit})",
            "coords": [lat, lon],
            "description": description_text,
            "tags": ["Mars", unit]
        }
        fans.append(fan)

with open(output_json, 'w') as f:
    json.dump(fans, f, indent=2)

print(f"Successfully converted {len(fans)} Martian fans to {output_json}")
