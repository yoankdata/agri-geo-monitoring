import ee
import os

def main():
    try:
        ee.Initialize()
        print("Authentification GEE reussie.")
    except Exception as e:
        print(f"Erreur d'initialisation GEE: {e}")
        print("Essayez de lancer 'earthengine authenticate' dans votre terminal.")
        return

    # Point de test (à défaut d'Abidjan, point neutre)
    # Latitude, Longitude (Note: ee.Geometry.Point takes [longitude, latitude])
    # Abidjan est approx à -4.0 (lon), 5.3 (lat)
    pt = ee.Geometry.Point([-4.0, 5.3]) 

    # Fenêtre temporelle courte
    start = "2024-01-01"
    end   = "2024-01-31"

    print(f"Test d'acces aux donnees Sentinel-2 pour la periode {start} a {end}...")

    try:
        # Sentinel-2 SR (surface reflectance)
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
              .filterBounds(pt)
              .filterDate(start, end)
              .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 20))
              .median())

        # NDVI = (B8 - B4) / (B8 + B4)
        ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")

        # Récupération de la valeur moyenne
        val = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=pt.buffer(50),
            scale=10,
            maxPixels=1e8
        ).get("NDVI")
        
        ndvi_value = val.getInfo()
        
        if ndvi_value is not None:
            print(f"Succes! NDVI mean: {ndvi_value}")
        else:
            print("Succes de la requete, mais aucune valeur NDVI trouvee (peut-etre pas d'image sans nuages?).")

    except Exception as e:
        print(f"Erreur lors de la requete GEE: {e}")

if __name__ == "__main__":
    main()
