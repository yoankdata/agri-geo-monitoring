import ee
from datetime import date, timedelta
import sys

def main():
    try:
        ee.Initialize()
    except Exception as e:
        print(f"Erreur d'initialisation GEE: {e}")
        return

    # Polygone test (zone agricole approximative Côte d'Ivoire)
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

    def ndvi_from_window(start, end, cloud_pct=60):
        try:
            print(f"Recherche images pour {start} -> {end}...")
            # Strict cloud filter
            ic = (ee.ImageCollection(COL)
                  .filterBounds(parcel)
                  .filterDate(start, end)
                  .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_pct)))

            count = ic.size().getInfo()
            if count is None: count = 0
            print(f"  > Images trouvées (cloud<={cloud_pct}%): {count}")

            # Fallback: si 0 image, enlève le filtre nuages
            if count == 0:
                print("  > Fallback: Tentative sans filtre nuages...")
                ic = (ee.ImageCollection(COL)
                      .filterBounds(parcel)
                      .filterDate(start, end))
                count2 = ic.size().getInfo()
                if count2 is None: count2 = 0
                print(f"  > Images trouvées (sans filtre): {count2}")
                if count2 == 0:
                    return None

            img = ic.median()
            ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")

            val = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=parcel,
                scale=10,
                maxPixels=1e9
            ).get("NDVI")

            out = val.getInfo()
            return out
            
        except Exception as e:
            print(f"Erreur lors du calcul pour la fenêtre {start}->{end}: {e}")
            return None

    # Fenêtres élargies 30 jours (robuste)
    # Période Actuelle
    t1_start = date(2024, 6, 1)
    t1_end   = t1_start + timedelta(days=30)
    
    # Période Passée (30 jours avant)
    t0_start = t1_start - timedelta(days=30)
    t0_end   = t1_start

    print("-" * 40)
    print(f"PERIODE ACTUELLE: {t1_start} au {t1_end}")
    ndvi_current = ndvi_from_window(str(t1_start), str(t1_end), cloud_pct=60)

    print("-" * 40)
    print(f"PERIODE PASSEE:   {t0_start} au {t0_end}")
    ndvi_past = ndvi_from_window(str(t0_start), str(t0_end), cloud_pct=60)

    print("-" * 40)
    print("RESULTATS:")
    print(f"NDVI current ({t1_start}): {ndvi_current}")
    print(f"NDVI past    ({t0_start}): {ndvi_past}")

    if ndvi_current is not None and ndvi_past not in (None, 0):
        variation = ((ndvi_current - ndvi_past) / ndvi_past) * 100
        print(f"Variation %: {round(variation, 2)}%")
    else:
        print("Impossible de calculer la variation (données manquantes ou nulles).")
    print("-" * 40)

if __name__ == "__main__":
    main()
