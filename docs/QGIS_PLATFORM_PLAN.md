# QGIS Platform Plan: Building ArcGIS-Equivalent Capability for East Carroll Parish

Prepared 2026-10-29. Purpose: give the parish (and the parks and recreation program) a GIS platform on free software that does what a small government normally buys from Esri, and position that work so state and federal money pays for it.

## 1. The honest comparison

For a parish of 7,000 people, an Esri Small Government Enterprise Agreement runs in the low five figures per year, every year, and still needs a person to run it. QGIS plus a few open-source servers covers the same ground. The gaps are not in analysis; they are in the polished web, mobile, and administrative layers that Esri bundles. The plan below closes those gaps in order of value.

| Esri product | What the parish would use it for | Open-source equivalent | Gap today |
|---|---|---|---|
| ArcGIS Pro | Desktop mapping and analysis | QGIS 3.40 LTR | None for this use. Already installed and producing this repo's maps. |
| ArcGIS Online / Hub | Public web maps, open data | QGIS Server or pg_tileserv + a static site (MapLibre), or QGIS Cloud | Needs a server and a few plugins. |
| Field Maps / Survey123 | Field inventory of trail conditions, park assets, drainage | QField + QFieldCloud (or Mergin Maps) | Mature. Needs setup and forms. |
| Enterprise geodatabase | Shared authoritative data | PostgreSQL + PostGIS | Mature. Needs a host and backups. |
| ModelBuilder | Repeatable analysis | QGIS Processing Modeler + PyQGIS scripts | Mature. This repo's build script is one. |
| StoryMaps | Grant narratives with maps | QGIS Atlas layouts to PDF, or a static web page | Partial. Template needed. |
| Network Analyst | Trail and walk-shed routing | QNEAT3 plugin, pgRouting | Mature. |
| Dashboards | Grant tracker, asset status | Grafana or a simple web page on PostGIS | Needs building. |
| Parcel fabric | Assessor parcels | PostGIS tables + QGIS editing | Adequate for parish scale. |

## 2. Extensions to write (the parity work)

Each item is a QGIS plugin, processing script, or QField form the parish owns, published open-source under this GitHub organization. Each is sized so one developer or a university capstone team can finish it in weeks, not years.

### Tier 1: parks and trails operations (first 6 months)
1. **Parish Asset Inventory QField project.** Forms for parks, trailheads, benches, signs, lighting, boat ramps, with photo capture and condition rating. Syncs to PostGIS. Replaces Field Maps.
2. **Trail Corridor Analyzer plugin.** Buffers a candidate line, intersects block groups with ACS population and poverty, counts schools and parks within reach, and outputs the numbers grant forms ask for. Generalizes the walk-shed and rail-catchment logic already in `gis/build_project.py`.
3. **Grant Map Atlas templates.** QGIS print layouts for LWCF, RTP, TAP, and LCDBG site maps with the required elements (north arrow, scale, parcel boundary, project limits, photo keys). One click per application.
4. **Data refresh script.** Scheduled PyQGIS job that re-pulls Census TIGER, ACS, OpenStreetMap, LSU Atlas lidar and imagery, and rebuilds the GeoPackage. Already half-built in this repo.

### Tier 2: parish-wide platform (months 6 to 18)
5. **PostGIS hub** on a small cloud VM or a parish server, with nightly backups, hosting parcels, roads, drainage, addresses, zoning, parks, and trails.
6. **Public web map** using QGIS Server (WMS/WFS) or pg_tileserv behind MapLibre, with a parks and trails viewer the public can open on a phone. Replaces ArcGIS Online.
7. **Address and 911 support layer.** The same hub serves the parish's E911 and assessor needs, which widens the funder base beyond recreation.
8. **Dashboard** for the grant tracker and asset conditions.

### Tier 3: regional and reusable (18 months and beyond)
9. **Delta Parish GIS Starter Kit.** Package tiers 1 and 2 as an installable bundle any Louisiana or Delta parish can adopt. This is what turns a local project into a regional grant.
10. **Lidar derivatives.** Once 3DEP lidar covers the parish, scripted DEM, contour, and flood-depth products for trail and park siting.
11. **QField trail counter and citizen reporting.** Public form for trail issues and usage counts.

## 3. People

- A half-time GIS coordinator (shared with the assessor, E911, or the town) is the minimum. Fund through LCDBG administrative allowance, DRA workforce money, or a USDA Rural Development Community Facilities technical assistance grant.
- Louisiana Delta Community College and ULM (University of Louisiana Monroe) geography programs can supply interns and capstone teams for tiers 1 and 2.
- The QGIS and OSGeo communities have working groups that review plugins before publication, which is free quality control.

## 4. Funding the platform

No federal program says "pay for QGIS plugins." Several pay for the outcomes those plugins deliver. Frame every request as data, mapping, public safety, or workforce, never as software development.

| Program | Agency | What to ask for | Notes |
|---|---|---|---|
| USGS 3DEP Data Collaboration Announcement | USGS | Lidar for the parish as part of a statewide or multi-parish proposal | FY27 estimates due Nov 13, 2026; submissions Dec 4, 2026. Lidar is the single most valuable dataset for trail and park design. |
| FEMA Cooperating Technical Partners | FEMA Region 6 | Flood mapping, base-level engineering, elevation data | Requires a partnership agreement. The parish's PostGIS hub becomes the delivery platform. |
| FEMA Hazard Mitigation Grant Program, 5 percent initiative | GOHSEP | GIS capability for mitigation planning | HMGP allows up to 5 percent of a disaster's allocation for GIS and warning systems. Ask GOHSEP after the next Louisiana declaration. |
| LCDBG Public Facilities | LA OCD | Allowable administration and engineering costs include mapping | Fund the asset inventory as part of a facilities application. |
| DRA SEDAP, workforce category | Delta Regional Authority | GIS technician training program with LDCC | Frames the platform as workforce development. |
| USDA Rural Development Community Facilities | USDA RD | Server hardware, field tablets, GPS units | Equipment is an eligible community facility cost. |
| USDA Rural Business Development Grant | USDA RD | Regional GIS starter kit as a technical assistance project through a regional nonprofit | Works best in Tier 3 with North Delta RPDD as applicant. |
| EDA Planning and Local Technical Assistance | US Economic Development Administration | Regional GIS as economic development infrastructure | Apply through North Delta RPDD. |
| NTIA and Louisiana ConnectLA broadband mapping | NTIA via state | Address and serviceable-location mapping | Parishes that maintain their own address points can get state support for that work. |
| Louisiana Capital Outlay | LA Legislature | Server, network, and office build-out | Bundle into the recreation facility request. |
| QGIS Grant Programme and OSGeo | QGIS.org | Funding for plugin work that benefits the whole QGIS community | Small (tens of thousands of dollars), annual, competitive. Realistic for Tier 1 item 2 if it is generic. |
| Sloan Foundation, Mozilla, NSF POSE | Private and federal | Open-source ecosystem grants | Only at Tier 3 with a university partner. |
| Esri Small Nonprofit Grant | Esri | Free ArcGIS for a Friends-of-Parks nonprofit | Keep as a bridge for any partner that must deliver in Esri formats; QGIS reads and writes file geodatabases. |

## 5. Interoperability with Esri partners

State agencies (LDWF, DOTD, OCD, GOHSEP) run ArcGIS. The parish will be asked for Esri-format deliverables. QGIS handles this: it reads and writes file geodatabases through GDAL's OpenFileGDB driver, consumes ArcGIS REST feature services directly as layers, and exports shapefiles, GeoPackages, and GeoJSON. Nothing in this plan requires an Esri license to exchange data with the state.

## 6. First 90 days

1. Stand up a PostGIS database (a $10 to $20 per month VM or a parish server) and load this repo's GeoPackage into it.
2. Build the QField asset inventory form and walk every park, ramp, and trail candidate with a phone.
3. Write the Trail Corridor Analyzer as a Processing script from `gis/build_project.py`, publish it to the QGIS plugin repository.
4. Add the parish to the USGS 3DEP FY27 partner list through LSU's Louisiana Geographic Information Center before November 13, 2026.
5. Ask GOHSEP and FEMA Region 6 what it takes to sign a Cooperating Technical Partner agreement.

## 7. Sources

- USGS FY27 3DEP Data Collaboration Announcement: https://www.usgs.gov/3d-national-topography-model/fy27-3dep-data-collaboration-announcement-dca
- FEMA Cooperating Technical Partners: https://www.fema.gov/flood-maps/cooperating-technical-partners
- Esri Small Government EA (for cost comparison): https://www.esri.com/smallgovela
- Esri Small Nonprofit Grant: https://www.esri.com/about/newsroom/arcuser/whats-in-the-esri-small-nonprofit-organization-grant
- QGIS Grant Programme: https://www.qgis.org/funding/grant-programme/
- QField: https://qfield.org
- pg_tileserv: https://github.com/CrunchyData/pg_tileserv
- GDAL OpenFileGDB driver: https://gdal.org/drivers/vector/openfilegdb.html
- LSU Atlas statewide data: https://atlas.ga.lsu.edu
