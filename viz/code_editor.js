// 1. Parcelle (Zone agricole rurale - Yamoussoukro)
var parcel = ee.Geometry.Polygon([
    [
        [-5.455, 6.880],
        [-5.450, 6.880],
        [-5.450, 6.885],
        [-5.455, 6.885],
        [-5.455, 6.880]
    ]
]);

// 2. Centrer (Zoom 16)
Map.centerObject(parcel, 16);

// 3. Image (Saison Sèche: Jan-Mars)
// Juin est en pleine saison des pluies -> Trop de nuages.
var s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(parcel)
    .filterDate("2024-01-01", "2024-03-30") // Période sèche
    .map(function (img) {
        var scl = img.select("SCL");
        var mask = scl.neq(3).and(scl.neq(7)).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
        return img.updateMask(mask).set('date', img.date().format('YYYY-MM-dd'));
    })
    .sort('CLOUDY_PIXEL_PERCENTAGE')
    .first();

// 4. NDVI
var ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI");

// 5. Palette Contrastée
var ndviVis = {
    min: 0,
    max: 0.8,
    palette: [
        '#d73027',  // rouge stress
        '#f46d43',
        '#fdae61',
        '#fee08b',
        '#a6d96a',
        '#1a9850'   // vert sain
    ]
};

// 6. Affichage
// RGB pour voir le sol réel
Map.addLayer(s2.clip(parcel), { min: 0, max: 3000, bands: ['B4', 'B3', 'B2'] }, "Sentinel-2 RGB", false);
// NDVI (0.6 opacité)
Map.addLayer(ndvi.clip(parcel), ndviVis, "NDVI Janv-Mars 2024", true, 0.6);
// Cadre rouge
Map.addLayer(parcel, { color: "red", fillColor: "00000000" }, "Limite Parcelle");

// 7. Stats
var meanDict = ndvi.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: parcel,
    scale: 10,
    maxPixels: 1e9
});

print("Date Image :", s2.get('date'));
print("NDVI Moyen :", meanDict.get("NDVI"));
