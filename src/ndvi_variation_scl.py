import ee
from datetime import date, timedelta
import sys

def main():
    try:
        ee.Initialize()
    except Exception as e:
        print(f"Erreur d'initialisation GEE: {e}")
        return

    parcel = ee.Geometry.Polygon([
        [
            [-5.455, 6.880],
            [-5.450, 6.880],
            [-5.450, 6.885],
            [-5.455, 6.885],
            [-5.455, 6.880],
        ]
    ])

    COL = "COPERNICUS/S2_SR_HARMONIZED"

    # SCL classes to REMOVE:
    # 3 = Cloud shadow
    # 7 = Unclassified
    # 8 = Cloud medium probability
    # 9 = Cloud high probability
    # 10 = Thin cirrus
    # 11 = Snow/ice (rare ici mais safe)
    BAD_SCL = [3, 7, 8, 9, 10, 11]

    def mask_s2_scl(img):
        scl = img.select("SCL")
        mask = scl.remap(BAD_SCL, [0]*len(BAD_SCL), 1)  # 1 = keep, 0 = drop
        return img.updateMask(mask)

    def get_ndvi_window(start, end):
        try:
            ic = (ee.ImageCollection(COL)
                  .filterBounds(parcel)
                  .filterDate(start, end)
                  .map(mask_s2_scl))

            count = ic.size().getInfo()
            if count is None: count = 0
            print(f"Images SCL-masked trouvées pour {start}->{end}: {count}")
            
            if count == 0:
                return None

            img = ic.median()
            ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")

            val = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=parcel,
                scale=10,
                maxPixels=1e9
            ).get("NDVI")

            result = val.getInfo()
            return result
        except Exception as e:
            print(f"Erreur lors du calcul NDVI: {e}")
            return None

    def risk_score_from_variation(var_pct):
        # V1 simple, monotone
        if var_pct is None:
            return None
        if var_pct <= -20:
            return 90
        if -20 < var_pct <= -10:
            return 70
        if -10 < var_pct < 0:
            return 40
        return 10

    # Fenêtres temporelles
    t1_start = date(2024, 6, 1)
    t1_end   = t1_start + timedelta(days=30)
    t0_start = t1_start - timedelta(days=30)
    t0_end   = t1_start

    print("----------------------------------------")
    print(f"PERIODE ACTUELLE (SCL): {t1_start} -> {t1_end}")
    ndvi_current = get_ndvi_window(str(t1_start), str(t1_end))

    print("----------------------------------------")
    print(f"PERIODE PASSEE (SCL):   {t0_start} -> {t0_end}")
    ndvi_past = get_ndvi_window(str(t0_start), str(t0_end))

    print("----------------------------------------")
    print("NDVI current:", ndvi_current)
    print("NDVI past   :", ndvi_past)

    variation = None
    if ndvi_current is not None and ndvi_past not in (None, 0):
        variation = ((ndvi_current - ndvi_past) / ndvi_past) * 100

    print("Variation % :", None if variation is None else round(variation, 2))
    
    risk = risk_score_from_variation(variation)
    print("Risk score  :", risk)
    print("----------------------------------------")

if __name__ == "__main__":
    main()
