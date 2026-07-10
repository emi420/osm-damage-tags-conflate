import osmium
import geopandas as gpd
from shapely.geometry import Polygon
import sys

def main():
    # 🔧 CONFIGURATION
    pbf_file = "buildings.osm.pbf"
    geojson_file = "damage_points.geojson"
    output_osm = "updated_buildings.osm"
    damage_field = "damaged"  # Column in GeoJSON with damage values
    damage_tag_field = "damage:VenEarthquake"
    damage_tag_assessment = ("damage:VenEarthquake:assessment","2026-06-26")
    damage_tag_source = ("source:damage:VenEarthquake", "ChatMap;Vantor")
    
    # 🔹 PASS 1: Extract building ways as polygons
    class BuildingExtractor(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {}
            self.building_data = []

        def node(self, node):
            self.nodes[node.id] = (node.lon, node.lat)

        def way(self, way):
            if any(tag.k == "building" for tag in way.tags):
                coords = []
                for nr in way.nodes:
                    if nr.ref in self.nodes:
                        coords.append(self.nodes[nr.ref])
                    else:
                        coords = None
                        break
                
                if coords and len(coords) > 2 and coords[0] == coords[-1]:
                    poly = Polygon(coords)
                    if not poly.is_empty and poly.is_valid:
                        self.building_data.append({"id": way.id, "geometry": poly})

    print("🔹 Pass 1: Reading PBF & extracting building polygons...")
    extractor = BuildingExtractor()
    try:
        extractor.apply_file(pbf_file, locations=True)
    except Exception as e:
        print(f"❌ Error reading PBF: {e}")
        sys.exit(1)

    if not extractor.building_data:
        print("⚠️ No buildings with 'building=*' tag found.")
        sys.exit(1)

    gdf_buildings = gpd.GeoDataFrame(extractor.building_data)
    gdf_buildings.crs = "EPSG:4326"

    # 🔹 PASS 2: Spatial join with damage points
    print(f"🔹 Pass 2: Reading GeoJSON & performing spatial join...")
    try:
        gdf_points = gpd.read_file(geojson_file)
    except Exception as e:
        print(f"❌ Error reading GeoJSON: {e}")
        sys.exit(1)

    if damage_field not in gdf_points.columns:
        print(f"❌ Column '{damage_field}' not found. Available: {gdf_points.columns.tolist()}")
        sys.exit(1)

    gdf_points = gdf_points[gdf_points[damage_field].notna()].copy()
    if gdf_points.empty:
        print("⚠️ No valid damage points found.")
        sys.exit(1)

    if gdf_points.crs is not None and gdf_points.crs != "EPSG:4326":
        gdf_points = gdf_points.to_crs("EPSG:4326")

    joined = gpd.sjoin(gdf_points, gdf_buildings, how="inner", predicate="intersects")

    priority = {"complete": 3, "significant": 2, "minimal": 1}
    way_damage_map = {}
    for _, row in joined.iterrows():
        wid = int(row["id_right"])
        dmg = row[damage_field]
        current = way_damage_map.get(wid)
        if current is None or priority.get(dmg, 0) > priority.get(current, 0):
            way_damage_map[wid] = dmg

    print(f"✅ Found {len(way_damage_map)} buildings to tag.")

    # 🔹 PASS 3: Inject tags & write valid .osm file
    class TagModifier(osmium.SimpleHandler):
        def __init__(self, damage_map, output_path):
            super().__init__()
            self.damage_map = damage_map
            self.writer = osmium.SimpleWriter(output_path)

        def way(self, way):
            # start with a set of tags without name:fr
            tags = {k: v for k, v in way.tags}
            # replace the name tag with the French version
            way_id = int(way.id)
            if way_id in self.damage_map:
                tags[damage_tag_field] = self.damage_map[way_id]
                tags[damage_tag_assessment[0]] = damage_tag_assessment[1]
                tags[damage_tag_source[0]] = damage_tag_source[1]
                # Write back the object with the modified tags
                self.writer.add(way.replace(tags=tags))
                    
        def node(self, node):
            self.writer.add_node(node)

        def relation(self, rel):
            self.writer.add_relation(rel)

    print("🔹 Pass 3: Applying tags & writing output OSM file...")
    try:
        modifier = TagModifier(way_damage_map, output_osm)
        modifier.apply_file(pbf_file, locations=True)
        modifier.writer.close()
    except Exception as e:
        print(f"❌ Error writing OSM: {e}")
        sys.exit(1)

    print(f"🎉 Done! Output saved to: {output_osm}")
    print("📌 Open in JOSM, validate changes, and upload via File > Upload Data")

if __name__ == "__main__":
    main()
