"""
ETL Pipeline: OpenStreetMap POIs → PostGIS
Lädt Points of Interest für Frankfurt: Supermärkte, Schulen, Kitas, Parks, Cafés.
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from backend.database import engine

CITY = "Frankfurt am Main, Germany"

POI_TAGS = {
    "supermarket": {"shop": "supermarket"},
    "school":      {"amenity": "school"},
    "kindergarten":{"amenity": "kindergarten"},
    "park":        {"leisure": "park"},
    "cafe":        {"amenity": ["cafe", "restaurant"]},
}

def load_pois():
    all_pois = []

    for category, tags in POI_TAGS.items():
        print(f"[ETL] Lade {category} ...")
        try:
            gdf = ox.features_from_place(CITY, tags=tags)
            gdf = gdf.reset_index()
            gdf["category"] = category
            gdf["name"] = gdf["name"] if "name" in gdf.columns else None

            # Nur Punkte und Zentroide von Polygonen
            gdf["geometry"] = gdf.geometry.to_crs("EPSG:25832").centroid.to_crs("EPSG:4326")
            gdf = gdf[["category", "name", "geometry"]].copy()
            gdf = gdf.set_crs("EPSG:4326")
            all_pois.append(gdf)
            print(f"      → {len(gdf)} {category} gefunden")
        except Exception as e:
            print(f"      ✗ Fehler: {e}")

    combined = pd.concat(all_pois, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")

    print(f"\n[ETL] Speichere {len(combined)} POIs in Supabase ...")
    combined.to_postgis(
        name="pois",
        con=engine,
        if_exists="replace",
        index=False,
    )

    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS pois_geom_idx ON pois USING GIST(geometry);"
        ))
        conn.commit()

    print(f"✓ Fertig — {len(combined)} POIs geladen.")
    return len(combined)

if __name__ == "__main__":
    load_pois()
