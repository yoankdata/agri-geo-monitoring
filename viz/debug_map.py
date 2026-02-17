import ee
import geemap

# Initialisation
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# --- INPUTS (identiques projet) ---
parcel = ee.Geometry.Polygon([
    [
        [-4.05, 5.28],
        [-4.00, 5.28],
        [-4.00, 5.33],
        [-4.05, 5.33],
        [-4.05, 5.28]
    ]
])

def mask_s2_scl(img):
    scl = img.select("SCL")
    # 3=shadow, 7=unclassified, 8,9,10,11=cloud/cirrus/snow
    mask = scl.neq(3).And(scl.neq(7)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
    return img.updateMask(mask)

# --- MAP SETUP ---
Map = geemap.Map()
Map.centerObject(parcel, 13)

# --- LAYERS ---

# 1. Parcel boundaries
Map.addLayer(parcel, {"color": "red"}, "Parcel")

# 2. Sentinel-2 Image (Juin 2024)
start = "2024-06-01"
end   = "2024-07-01"

s2_raw = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(parcel)
          .filterDate(start, end))

# Mosaïque brute (RGB) pour voir les nuages
rgb_vis = {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]}
Map.addLayer(s2_raw.median().clip(parcel.buffer(5000)), rgb_vis, f"S2 RGB Raw {start}")

# 3. NDVI Masked
s2_masked = s2_raw.map(mask_s2_scl).median()
ndvi = s2_masked.normalizedDifference(["B8", "B4"]).rename("NDVI")

ndvi_vis = {
  "min": 0,
  "max": 0.8,
  "palette": [
    'white',
    'yellow',
    'orange',
    'green',
    'darkgreen'
  ]
}

Map.addLayer(ndvi.clip(parcel), ndvi_vis, f"NDVI Masked {start}")

# Export HTML
output_file = "viz/debug_map.html"
Map.to_html(output_file)
print(f"Map saved to {output_file}")
