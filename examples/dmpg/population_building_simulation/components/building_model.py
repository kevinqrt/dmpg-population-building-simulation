from __future__ import annotations
import json
from pyparsing import Path
import requests
from peewee import Model, CharField, FloatField, IntegerField
from shapely.geometry import Polygon, MultiPolygon
from examples.dmpg.population_building_simulation.db import db
from examples.dmpg.population_building_simulation.enums import BuildingType


class Building(Model):
    osm_id = IntegerField()
    osm_type = CharField(null=True)
    name = CharField(null=True)
    building_type = CharField(null=True)
    lat = FloatField(null=True)  # centroid latitude
    lon = FloatField(null=True)  # centroid longitude

    class Meta:
        database = db

    def __str__(self) -> str:
        return f"Building(centroid=({self.lat}, {self.lon}))"

    @staticmethod
    def _map_osm_element_to_building(element: dict) -> Building:
        osm_id = element.get("id")
        osm_type = element.get("type")

        lat, lon = Building._compute_centroid(element) or (None, None)

        return Building(
            osm_id=osm_id,
            osm_type=osm_type,
            building_type="residential",
            lat=lat,
            lon=lon,
        )

    @staticmethod
    def _compute_centroid(element: dict) -> tuple[float, float] | None:
        if element.get("type") == "way":
            geometry = element.get("geometry")
            if geometry:
                coords = [(g["lon"], g["lat"]) for g in geometry]
                try:
                    poly = Polygon(coords)
                    c = poly.centroid
                    return c.y, c.x
                except:
                    return None

        elif element.get("type") == "relation":
            outers = []
            for m in element.get("members", []):
                if m.get("role") == "outer" and "geometry" in m:
                    coords = [(g["lon"], g["lat"]) for g in m["geometry"]]
                    outers.append(Polygon(coords))

            if outers:
                try:
                    mp = MultiPolygon(outers)
                    c = mp.centroid
                    return c.y, c.x
                except:
                    return None

        return None
    
    @staticmethod
    def _map_unternehmen_lingen_to_building(data: dict) -> Building:
        return Building(
            osm_id=data["id"],
            name=data.get("name", "Unnamed Company"),
            building_type="company",
            lat=data.get("lat"),
            lon=data.get("lon"),
        )
    
    @staticmethod
    def get_living_buildings() -> list[Building]:
        return list(Building.select().where(Building.building_type == "residential"))
    
    @staticmethod
    def get_workplace_buildings() -> list[Building]:
        return list(Building.select().where(Building.building_type == "company"))    
    
    @staticmethod
    def get_osm_houses_from_api(city_name: str, building_type: BuildingType) -> None:
        """
        Fetches building data from the Overpass API and returns
        a list of building elements (OSM raw dicts).
        """

        url = "http://overpass-api.de/api/interpreter"

        # Docs: https://dev.overpass-api.de/
        overpass_query = f"""
            [out:json][timeout:90];

            /* Germany (robust via ISO code) */
            area
            ["ISO3166-1"="DE"]
            ["boundary"="administrative"]
            ->.germany;

            /* City inside Germany (any valid admin_level) */
            area
            ["name"="{city_name}"]
            ["boundary"="administrative"]
            (area.germany)
            ->.searchArea;

            (
                way["building"~"{building_type.overpass_building_regex}"](area.searchArea);
                relation["building"~"{building_type.overpass_building_regex}"](area.searchArea);
            );

            out geom;
            """

        response = requests.get(url, params={"data": overpass_query})

        if response.status_code != 200:
            raise RuntimeError(
                f"Overpass API request failed with {response.status_code}"
            )

        data = response.json()
        
        base_dir = Path(__file__).resolve().parent.parent
        output_dir = base_dir / "interfaces"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_file = output_dir / f"{building_type.value}_{city_name}.json"

        with raw_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def save_in_db(file_path: Path, isOSMData: bool) -> None:
        if not file_path.exists():
            raise FileNotFoundError(f"OSM file not found: {file_path}")
        
        if isOSMData == True:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            living_buildings = [
                Building._map_osm_element_to_building(e) for e in data.get("elements", [])
            ]
            with db.atomic():
                for building in living_buildings:
                    building.save()
        elif isOSMData == False:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            commercial_buildings = [
                Building._map_unternehmen_lingen_to_building(entry)
                for entry in data
            ]
            with db.atomic():
                for building in commercial_buildings:
                    building.save()