"""
ETL Pipeline: Bodenrichtwerte Frankfurt → PostGIS
Lädt Bodenrichtwert-Zonen vom WFS Hessen und speichert sie in Supabase.
"""

import geopandas as gpd
from owslib.wfs import WebFeatureService
from sqlalchemy import text
from io import BytesIO
from backend.database import engine

WFS_URL = "https://www.geoportal.hessen.de/mapbender/php/wfs.php?INSPIRE=1&FEATURETYPE_ID=5721&SERVICE=WFS&VERSION=2.0.0"
FRANKFURT_BBOX = (461000, 5541000, 498000, 5584000)  # UTM 25832

def load_bodenrichtwerte():
    print("[1/3] Lade Bodenrichtwerte vom WFS Hessen ...")
    wfs = WebFeatureService(url=WFS_URL, version="2.0.0")
    response = wfs.getfeature(
        typename="boris:BR_BodenrichtwertZonal",
        bbox=FRANKFURT_BBOX,
        srsname="EPSG:25832",
        outputFormat="text/xml"
    )
    data = response.read()
    print(f"      → {len(data)//1024}KB empfangen")

    print("[2/3] Verarbeite Daten ...")
    gdf = gpd.read_file(BytesIO(data))
    gdf_ffm = gdf[gdf["kreis"] == 12].copy()
    gdf_ffm = gdf_ffm[[
        "bodenrichtwert",
        "entwicklungszustand",
        "bodenrichtwertzoneName",
        "ortsteilName",
        "stichtag",
        "art",
        "geometry"
    ]].copy()
    gdf_ffm = gdf_ffm.to_crs("EPSG:4326")
    print(f"      → {len(gdf_ffm)} Zonen gefunden")

    print("[3/3] Speichere in Supabase ...")
    gdf_ffm.to_postgis(
        name="bodenrichtwerte",
        con=engine,
        if_exists="replace",
        index=False,
    )
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS brw_geom_idx ON bodenrichtwerte USING GIST(geometry);"
        ))
        conn.commit()

    print(f"✓ Fertig — {len(gdf_ffm)} Zonen in Supabase geladen.")
    return len(gdf_ffm)

if __name__ == "__main__":
    load_bodenrichtwerte()
