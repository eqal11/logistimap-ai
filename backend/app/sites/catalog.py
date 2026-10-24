"""Dataset semantics: mapped proxies are never statutory land suitability."""
CATALOG={
 "road_distance_m":("Distance to mapped major road","m","cost","gis","Geodesic footprint separation within 100 km; not driveway or highway interchange access."),
 "warehouse_distance_m":("Distance to other mapped warehouse","m","cost","gis","Nearest different mapped footprint within 100 km; dataset coverage only."),
 "hub_distance_m":("Distance to mapped logistics hub","m","cost","gis","Nearest mapped hub within 100 km; coverage may be sparse."),
 "industrial_count":("Mapped industrial facilities nearby","objects","benefit","gis","Unique industrial objects within configured anchor radius; candidate itself excluded."),
 "industrial_density_km2":("Mapped industrial facility density","objects/km²","benefit","gis","Count divided by geodesic circular catchment area; not economic demand."),
 "industrial_overlap_pct":("Mapped industrial land-use / park overlap","%","benefit","gis","Polygon overlap by geodesic area; point coverage is 0/100. Not verified zoning or land availability."),
 "parcel_area_m2":("Mapped candidate footprint area","m²","benefit","gis","Geodesic area for polygons; a point has unknown parcel area."),
 "port_time_s":("Driving time to selected port reference","s","cost","network","User-selected reference, not verified freight terminal gate; OSRM car."),
 "airport_time_s":("Driving time to selected airport reference","s","cost","network","Not verified cargo gate; OSRM car, no traffic or truck guarantees."),
 "network_time_s":("Driving time to selected network reference","s","cost","network","OSRM car to an explicitly selected logistics/network reference."),
 "infrastructure":("Infrastructure availability","user score","benefit","unavailable","No verified utility/infrastructure dataset configured."),
 "flood_risk":("Flood hazard","user score","cost","unavailable","No authoritative flood dataset configured."),
 "environment":("Environmental restriction severity","user score","cost","unavailable","No authoritative environmental constraints dataset configured."),
 "land_cost":("Land cost","MYR","cost","unavailable","No verified property price/availability dataset configured."),
 "zoning":("Regulatory / zoning compatibility","user score","benefit","unavailable","No authoritative zoning or development permission data configured."),
}
WARNINGS=[
 "Candidate-based relative suitability, not continuous raster suitability or an investment recommendation.",
 "OSM features are mapped references, not legally available land, verified entrances or developable parcels.",
 "Mapped facility concentration is not verified economic demand. Coverage depends on the imported dataset.",
 "OSRM standard car profile, not truck verified. No tolls or live traffic. User-selected targets are not verified gates.",
 "Scores depend on candidate set, criterion direction, normalization, weights and user assumptions; rank reversal is possible.",
]
def catalog():
 return [{"id":k,"label":v[0],"unit":v[1],"direction":v[2],"availability":v[3],"description":v[4],"user_supplied_allowed":True} for k,v in CATALOG.items()]
