# East Carroll Parish Parks & Recreation

Working repository for standing up a parks and recreation program in East Carroll Parish, Louisiana, and securing federal, state, and private funding for it.

## Contents

| Path | What it is |
|---|---|
| `docs/FUNDING_ROADMAP.md` | Step-by-step plan: entity setup, priority grant programs, GIS funding, 12-month calendar, sources |
| `docs/TRAILS_PLAN.md` | Hiking, biking, levee, and rail-trail corridors ranked, with legal status of the Lake Providence rail line and trail-specific funding |
| `docs/QGIS_PLATFORM_PLAN.md` | Plan for QGIS plugins and open-source servers that reach ArcGIS parity, and the grants that can pay for it |
| `docs/ONE_PAGER.pdf` | One-page handout for the Police Jury meeting (built by `scripts/build_one_pager.py`) |
| `docs/POLICE_JURY_PLAN.md` | Organizing parks and trails as a Police Jury division: juror roster and who to talk to first, the one-page pitch, and road and bridge funding the Jury can pursue alongside |
| `docs/ARCHITECTURE.md` | Mermaid diagrams: data pipeline, build script logic, layer stack, funding map, rail decision tree, 12-month Gantt |
| `gis/east_carroll_parks_map.pdf` | Letter-size map with legend, scale bar, and north arrow, from the saved print layout |
| `grants/grant_tracker.csv` | One row per program with deadline, match, contact, and status. Update `status` as applications move |
| `gis/east_carroll_parks.qgz` | QGIS project (open with QGIS 3.x LTR) |
| `gis/data/processed/east_carroll.gpkg` | GeoPackage with all layers below |
| `gis/data/processed/acs_2023_east_carroll.json` | Census ACS 2023 5-year population, income, and poverty for parish, tracts, block groups, and places |
| `gis/east_carroll_overview.png` | Rendered parish map: poverty by tract, existing recreation assets, half-mile park walksheds |
| `gis/build_project.py` | Script that downloads nothing but rebuilds everything from `gis/data/raw` |
| `scripts/check_mermaid.py` | Validates every Mermaid block in the repo; CI runs it with `--render` via `.github/workflows/mermaid.yml`; `.github/workflows/ruff.yml` lints and format-checks all Python with Ruff (config in `pyproject.toml`) |

## GIS layers in the GeoPackage

- `parish_boundary`, `municipalities` (Lake Providence), `census_tracts`, `block_groups`, `school_district` from Census TIGER 2024
- `roads`, `water_areas`, `water_lines` from Census TIGER 2024
- `rec_assets`: 44 points from OpenStreetMap: ball fields, tennis courts, pool, two boat ramps, schools, the Louisiana State Cotton Museum, Bayou Macon WMA, and named lakes
- `trails_named`, `trails_paths`, `trails_tracks`: OpenStreetMap trail and track linework from the Take-a-Hike repo (`gis/find_trails.py` output), clipped to the parish, with `length_km_clipped`
- `rail_corridors` (54.9 km, all disused), `levees` (47.9 km), `rail_corridor_1mi_catchment` from OpenStreetMap
- `la_parishes` (64) and `la_tracts` (1,388, with ACS poverty) in a "Louisiana statewide (toggle)" group, off by default
- `park_walkshed_half_mile`: half-mile buffers around existing parks and fields
- `block_groups_no_park_access`: block groups entirely outside those buffers

The tract and block-group layers carry `population`, `med_hh_income`, and `poverty_pct` columns from ACS 2023.

## Rebuilding the GIS project

Raw data is not committed (see `.gitignore`). To rebuild:

```
# Census TIGER 2024 shapefiles (county, LA place/tract/bg/unsd, 22035 roads/areawater/linearwater) -> gis/data/raw/
# ACS 2023 5-yr summary-file tables b01003, b17021, b19013 -> gis/data/raw/acs_<table>.dat
# Overpass JSON of recreation features -> gis/data/raw/osm_rec.json
# Overpass JSON of railway/dyke/embankment ways -> gis/data/raw/osm_rail_levee.json
# Take-a-Hikev2/gis/data/east_carroll_parish.geojson -> gis/data/raw/takeahike_east_carroll_trails.geojson
C:\OSGeo4W\bin\python-qgis-ltr.bat gis\build_project.py
```

## Key facts for grant narratives (ACS 2023 5-year)

- Population 7,195; median household income $28,321; poverty rate 35.7 percent
- All three census tracts are low-to-moderate income; the south side of Lake Providence (tract 3) has a 40.3 percent poverty rate
- Persistent-poverty county (USDA) and Delta Regional Authority distressed parish
