import ee
import psycopg2
from datetime import date, timedelta

# Initialisation GEE
try:
    ee.Initialize()
except Exception as e:
    print(f"Erreur d'initialisation GEE: {e}")
    exit(1)

# --- CONFIG DB ---
DB_CONFIG = dict(
    host="localhost",
    port="5434", # Port mappé dans docker-compose
    dbname="agri_geo",
    user="agri",
    password="agri",
)

# --- PARCEL (same as before) ---
parcel_id = "parcel_demo_001"

coords = [
    [-5.455, 6.880],
    [-5.450, 6.880],
    [-5.450, 6.885],
    [-5.455, 6.885],
    [-5.455, 6.880],
]
parcel = ee.Geometry.Polygon([coords])

# WKT for PostGIS (lon lat)
# Construction de la chaîne LINESTRING pour le polygone
# Format attendu par ST_GeomFromText: 'POLYGON((-4.05 5.28, -4.00 5.28, ...))'
wkt_coords = ", ".join([f"{lon} {lat}" for lon, lat in coords])
wkt = f"POLYGON(({wkt_coords}))"

COL = "COPERNICUS/S2_SR_HARMONIZED"
BAD_SCL = [3, 7, 8, 9, 10, 11]

def mask_s2_scl(img):
    scl = img.select("SCL")
    mask = scl.remap(BAD_SCL, [0]*len(BAD_SCL), 1)
    return img.updateMask(mask)

def get_ndvi(start, end):
    try:
        ic = (ee.ImageCollection(COL)
              .filterBounds(parcel)
              .filterDate(start, end)
              .map(mask_s2_scl))

        # Check size locally avoids some GEE errors if collection is empty
        count = ic.size().getInfo()
        if count == 0:
            print(f"Aucune image pour la période {start} -> {end}")
            return None

        img = ic.median()
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        val = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=parcel,
            scale=10,
            maxPixels=1e9
        ).get("NDVI")
        
        return ee.Number(val).getInfo()
    except Exception as e:
        print(f"Erreur calcul NDVI ({start}->{end}): {e}")
        return None

def risk_score(var_pct):
    if var_pct is None:
        return None
    if var_pct <= -20:
        return 90
    if -20 < var_pct <= -10:
        return 70
    if -10 < var_pct < 0:
        return 40
    return 10

import argparse

def main():
    parser = argparse.ArgumentParser(description="Ingest parcel run for a specific date.")
    parser.add_argument("--date", type=str, default="2024-06-01", help="Start date (YYYY-MM-DD) for T1")
    args = parser.parse_args()

    print("Début de l'ingestion...")
    
    # Fenêtres temporelles (Date cible vs 30 jours avant)
    # T1 = [target_date, target_date + 30j]
    # T0 = [target_date - 30j, target_date]
    
    try:
        t1_start = date.fromisoformat(args.date)
    except ValueError:
        print(f"Erreur: Format de date invalide {args.date}. Utilisez YYYY-MM-DD.")
        return

    t1_end   = t1_start + timedelta(days=30)
    t0_start = t1_start - timedelta(days=30)
    t0_end   = t1_start

    print(f"Calcul NDVI T1: {t1_start} -> {t1_end}")
    ndvi_t1 = get_ndvi(str(t1_start), str(t1_end))
    
    print(f"Calcul NDVI T0: {t0_start} -> {t0_end}")
    ndvi_t0 = get_ndvi(str(t0_start), str(t0_end))

    var_pct = None
    if ndvi_t1 is not None and ndvi_t0 not in (None, 0):
        # Attention à la division par zéro si ndvi_t0 est nul (peu probable pour du NDVI végétal mais possible)
        if ndvi_t0 != 0:
            var_pct = ((ndvi_t1 - ndvi_t0) / ndvi_t0) * 100
        else:
            var_pct = 0 # Convention?

    score = risk_score(var_pct)

    print("-" * 30)
    print(f"ndvi_t1      : {ndvi_t1}")
    print(f"ndvi_t0      : {ndvi_t0}")
    print(f"variation_pct: {var_pct}")
    print(f"risk_score   : {score}")
    print("-" * 30)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("Insertion en base de données...")
        cur.execute(
            """
            INSERT INTO geo.parcel_runs
            (parcel_id, geom, t0_start, t0_end, t1_start, t1_end, ndvi_t0, ndvi_t1, variation_pct, risk_score)
            VALUES
            (%s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING run_id;
            """,
            (parcel_id, wkt, t0_start, t0_end, t1_start, t1_end, ndvi_t0, ndvi_t1, var_pct, score)
        )

        run_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        print(f"Succès! Run inséré avec ID: {run_id}")

    except Exception as e:
        print(f"Erreur Base de Données: {e}")

if __name__ == "__main__":
    main()
