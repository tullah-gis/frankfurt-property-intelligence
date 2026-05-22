from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db

router = APIRouter()

@router.get("/zones")
def get_zones(entwicklungszustand: str = None, db: Session = Depends(get_db)):
    """Alle Bodenrichtwert-Zonen mit Lebensqualität-Index als GeoJSON."""
    if entwicklungszustand:
        sql = text("""
            SELECT bodenrichtwert, entwicklungszustand, "bodenrichtwertzoneName",
                   "ortsteilName", quality_index,
                   poi_supermarket, poi_school, poi_kindergarten, poi_park, poi_cafe,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM bodenrichtwerte_index
            WHERE entwicklungszustand = :ez
        """)
        rows = db.execute(sql, {"ez": entwicklungszustand}).fetchall()
    else:
        sql = text("""
            SELECT bodenrichtwert, entwicklungszustand, "bodenrichtwertzoneName",
                   "ortsteilName", quality_index,
                   poi_supermarket, poi_school, poi_kindergarten, poi_park, poi_cafe,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM bodenrichtwerte_index
        """)
        rows = db.execute(sql).fetchall()

    features = [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {
                "bodenrichtwert": row.bodenrichtwert,
                "entwicklungszustand": row.entwicklungszustand,
                "zoneName": row[2],
                "ortsteil": row[3],
                "quality_index": row.quality_index,
                "poi_supermarket": row.poi_supermarket,
                "poi_school": row.poi_school,
                "poi_kindergarten": row.poi_kindergarten,
                "poi_park": row.poi_park,
                "poi_cafe": row.poi_cafe,
            }
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    sql = text("""
        SELECT
            COUNT(*) as total_zones,
            ROUND(AVG(bodenrichtwert)::numeric, 0) as avg_brw,
            MAX(bodenrichtwert) as max_brw,
            MIN(bodenrichtwert) as min_brw,
            ROUND(AVG(quality_index)::numeric, 1) as avg_quality
        FROM bodenrichtwerte_index
    """)
    row = db.execute(sql).fetchone()
    return {
        "total_zones": row.total_zones,
        "avg_brw": row.avg_brw,
        "max_brw": row.max_brw,
        "min_brw": row.min_brw,
        "avg_quality": row.avg_quality,
    }


@router.get("/stadtteile")
def get_stadtteile(db: Session = Depends(get_db)):
    """Stadtteile Frankfurt als GeoJSON mit Namen."""
    sql = text("""
        SELECT name, ST_AsGeoJSON(geometry)::json AS geometry
        FROM stadtteile
        WHERE name IS NOT NULL
    """)
    rows = db.execute(sql).fetchall()
    features = [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {"name": row.name}
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/export/geojson")
def export_geojson(db: Session = Depends(get_db)):
    """Export als GeoJSON."""
    from fastapi.responses import Response
    import json

    sql = text("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', json_agg(
                json_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geometry)::json,
                    'properties', json_build_object(
                        'bodenrichtwert', bodenrichtwert,
                        'entwicklungszustand', entwicklungszustand,
                        'quality_index', quality_index,
                        'ortsteil', "ortsteilName",
                        'poi_supermarket', poi_supermarket,
                        'poi_school', poi_school,
                        'poi_kindergarten', poi_kindergarten,
                        'poi_park', poi_park,
                        'poi_cafe', poi_cafe
                    )
                )
            )
        ) AS geojson
        FROM bodenrichtwerte_index
    """)
    result = db.execute(sql).fetchone()
    return Response(
        content=json.dumps(result.geojson),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=frankfurt_property_index.geojson"}
    )
