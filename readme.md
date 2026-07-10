# Damage tags conflator

This script takes a GeoJSON with points and tags and a osm.pbf file with existing ways.

Then, it merges the tags from the points to the ways.

It's designed for adding damage tags to buildings on OSM.

## Install

pip install osmium geopandas

## Config

Edit conflate.py

```py
    # 🔧 CONFIGURATION
    pbf_file = "buildings.osm.pbf"
    geojson_file = "damage_points.geojson"
    output_osm = "updated_buildings.osm"
    damage_field = "damaged"  # Column in GeoJSON with damage values
    damage_tag_field = "damage:VenEarthquake"
    damage_tag_assessment = ("damage:VenEarthquake:assessment","2026-06-26")
    damage_tag_source = ("source:damage:VenEarthquake", "ChatMap;Vantor")
```

## Run

```py
python conflate.py
```

## Copyright

(c) Emilio Mariscal 2026. This code was written making extensive use of Qwen3.6:27b.



