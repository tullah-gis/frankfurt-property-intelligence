"""
Berechnet den Lebensqualität-Index für jede Bodenrichtwert-Zone.
Zählt POIs im Umkreis des Zentroiden jeder Zone und berechnet einen gewichteten Score.
"""

import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from backend.database import engine

WEIGHTS = {
    "supermarket":  0.20,
    "school":       0.25,
    "kindergarten": 0.20,
    "park":         0.15,
    "cafe":         0.20,
}

RADIUS = 500  # Meter

def calculate_index():
    print("[1/4] Lade Bodenrichtwerte aus Supabase ...")
    brw = gpd.read_postgis(
        "SELECT * FROM bodenrichtwerte WHERE art = 'W'",
        con=engine,
        geom_col="geometry"
    )
    print(f"      → {len(brw)} Wohnzonen")

    print("[2/4] Lade POIs aus Supabase ...")
    pois = gpd.read_postgis(
        "SELECT * FROM pois",
        con=engine,
        geom_col="geometry"
    )
    print(f"      → {len(pois)} POIs")

    # In metrisches CRS umwandeln für korrekte Distanzberechnung
    brw_proj = brw.to_crs("EPSG:25832")
    pois_proj = pois.to_crs("EPSG:25832")

    print("[3/4] Berechne Index pro Zone ...")
    results = []

    for idx, zone in brw_proj.iterrows():
        centroid = zone.geometry.centroid
        centroid_buf = centroid.buffer(RADIUS)

        scores = {}
        for category in WEIGHTS.keys():
            cat_pois = pois_proj[pois_proj["category"] == category]
            count = cat_pois[cat_pois.geometry.within(centroid_buf)].shape[0]
            scores[f"poi_{category}"] = count

        # Normalisierter Score 0-100
        raw_score = sum(
            min(scores[f"poi_{cat}"] / 3, 1.0) * weight
            for cat, weight in WEIGHTS.items()
        )
        scores["quality_index"] = round(raw_score * 100, 1)
        scores["zone_idx"] = idx
        results.append(scores)

    results_df = pd.DataFrame(results).set_index("zone_idx")
    brw_result = brw.join(results_df)

    print("[4/4] Speichere Ergebnisse in Supabase ...")
    brw_result.to_postgis(
        name="bodenrichtwerte_index",
        con=engine,
        if_exists="replace",
        index=False,
    )

    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS brw_idx_geom ON bodenrichtwerte_index USING GIST(geometry);"
        ))
        conn.commit()

    print(f"\n✓ Fertig!")
    print(f"Ø Qualitätsindex: {brw_result['quality_index'].mean():.1f}")
    print(f"Max: {brw_result['quality_index'].max()}")
    print(f"Min: {brw_result['quality_index'].min()}")
    return brw_result

if __name__ == "__main__":
    calculate_index()
