"""
ETL Pipeline: Stadtteile Frankfurt → PostGIS
Lädt Verwaltungsgrenzen via osmnx von OpenStreetMap.
"""

import osmnx as ox
from sqlalchemy import text
from backend.database import engine

def load_stadtteile():
    print("[1/2] Lade Stadtteile Frankfurt via osmnx ...")
    stadtteile = ox.features_from_place(
        "Frankfurt am Main, Germany",
        tags={"boundary": "administrative", "admin_level": "9"}
    )
    stadtteile = stadtteile.reset_index()
    stadtteile = stadtteile[
        stadtteile.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ]
    stadtteile = stadtteile[["name", "geometry"]].dropna(subset=["name"])
    stadtteile = stadtteile.set_crs("EPSG:4326")
    print(f"      → {len(stadtteile)} Stadtteile gefunden")

    print("[2/2] Speichere in Supabase ...")
    stadtteile.to_postgis(
        name="stadtteile",
        con=engine,
        if_exists="replace",
        index=False,
    )
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS stadtteile_geom_idx ON stadtteile USING GIST(geometry);"
        ))
        conn.commit()
    print(f"✓ Fertig — {len(stadtteile)} Stadtteile geladen.")

if __name__ == "__main__":
    load_stadtteile()
