# How the Pieces Fit: Scripts and Funding

Mermaid diagrams render on GitHub. Open this file on github.com to see them drawn.

## 1. Data pipeline: raw downloads to QGIS project

```mermaid
flowchart LR
    subgraph sources["External sources"]
        TIGER[(Census TIGER 2024<br/>county, place, tract,<br/>block group, roads, water)]
        ACS[(Census ACS 2023 5-yr<br/>summary file .dat<br/>B01003 B17021 B19013)]
        OSM[(OpenStreetMap<br/>Overpass API)]
        TAH[(Take-a-Hikev2 repo<br/>east_carroll_parish.geojson)]
    end

    subgraph raw["gis/data/raw (gitignored)"]
        Z[tl_2024_*.zip]
        D[acs_*.dat]
        J1[osm_rec.json]
        J2[osm_rail_levee.json]
        J3[takeahike_east_carroll_trails.geojson]
    end

    TIGER --> Z
    ACS --> D
    OSM -- "leisure, amenity,<br/>tourism, historic" --> J1
    OSM -- "railway, dyke,<br/>embankment" --> J2
    TAH --> J3

    BUILD[["gis/build_project.py<br/>(PyQGIS, headless)"]]
    Z & D & J1 & J2 & J3 --> BUILD

    subgraph out["Outputs (committed)"]
        GPKG[(east_carroll.gpkg<br/>20+ layers)]
        QGZ[east_carroll_parks.qgz<br/>styled project + print layout]
        PNG[east_carroll_overview.png]
        MAP[east_carroll_parks_map.pdf / .png<br/>with legend]
        ACSJ[acs_2023_east_carroll.json]
    end
    BUILD --> GPKG & QGZ & PNG & MAP & ACSJ
    QGZ ==> QGIS[[QGIS Desktop]]
    MAP ==> GRANTS[[Grant applications]]
```

## 2. Inside build_project.py

```mermaid
flowchart TD
    A[initQgis + Processing] --> B[Unzip TIGER shapefiles]
    B --> C[Extract parish 22035:<br/>boundary, tracts, block groups,<br/>roads, water, Lake Providence]
    C --> D[Read ACS .dat tables<br/>filter rows containing US22035]
    D --> E[Join population, median income,<br/>poverty_pct to tracts and block groups]
    E --> F[Statewide: all 64 parishes +<br/>1,388 LA tracts with poverty]
    F --> G[OSM points -> rec_assets<br/>collapse tags to asset_class]
    G --> H[Buffer parks 0.5 mi<br/>EPSG:26915 -> walkshed]
    H --> I[Block groups disjoint from walkshed<br/>-> no_park_access]
    I --> J[Clip Take-a-Hike lines to parish<br/>split: named / paths / tracks<br/>add length_km_clipped]
    J --> K[OSM rail + levee ways<br/>clip, length, 1 mi rail catchment]
    K --> L[Style every layer<br/>tan poverty ramp, asset classes,<br/>plain-English names]
    L --> M[Layer tree order<br/>points on top, basemap bottom<br/>statewide group unchecked]
    M --> N[Default view extent = parish]
    N --> O[Print layout: title, map,<br/>legend, scale bar, north arrow]
    O --> P[Export PDF + PNG<br/>write .qgz]
    P --> Q[Print summary stats<br/>exitQgis]
```

## 3. Layer stack as it draws in QGIS

```mermaid
flowchart TB
    direction TB
    L1["Parks, fields, schools and other sites (points, labelled)"]
    L2["Lake Providence town limits"]
    L3["Named trails and tracks (red) / Paths (orange) / Farm tracks (dotted, off)"]
    L4["Rail corridor (black dash) / Mississippi River levee (brown)"]
    L5["Within one mile of the rail corridor (pale blue)"]
    L6["Roads / Streams / Lakes and rivers"]
    L7["Within a half mile of a park (green) / No park block group (gold outline)"]
    L8["Poverty rate by census tract (tan ramp, 60% opacity)"]
    L9["Census block groups / School district (off)"]
    L10["East Carroll Parish boundary"]
    L11["Louisiana statewide (toggle, off): parishes + tracts"]
    L12["OpenStreetMap basemap"]
    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7 --> L8 --> L9 --> L10 --> L11 --> L12
```

## 4. Funding: who pays for what

```mermaid
flowchart LR
    subgraph setup["Step 0: become fundable"]
        RD[Recreation District<br/>La. R.S. 33:4562]
        SAM[SAM.gov UEI]
        PLAN[Parks & Trails Master Plan<br/>NPS RTCA help]
        RD --> SAM --> PLAN
    end

    subgraph fed["Federal via state"]
        LCDBG[LCDBG Public Facilities<br/>LA OCD, ~0-10% match]
        LWCF[LWCF<br/>State Parks, 50% match, Apr 1]
        RTP[Recreational Trails Program<br/>State Parks, 20% match, Jul 1]
        TAP[Transportation Alternatives<br/>LA DOTD, 20% match, early 2027]
        BFA[Boating & Fishing Access<br/>LDWF, 25% match]
        SEDAP[DRA SEDAP<br/>via North Delta LDD, ~Jul]
    end

    subgraph feddirect["Federal direct"]
        USDA[USDA Community Facilities<br/>rolling, up to 75% grant]
        USGS[USGS 3DEP lidar<br/>Nov 13 / Dec 4, 2026]
        FEMA[FEMA CTP / HMGP 5%<br/>via GOHSEP]
    end

    subgraph state["State"]
        LOF[Louisiana Outdoors Forever<br/>LDWF, match money]
        CO[Capital Outlay<br/>legislator sponsor, Nov 1]
    end

    subgraph private["Private"]
        RTC[Rails-to-Trails Conservancy]
        AARP[AARP Community Challenge]
        PFB[PeopleForBikes]
        ESRI[Esri nonprofit grant]
        QGIS[QGIS Grant Programme]
    end

    PLAN --> fed & feddirect & state & private

    LOOP[["A. Lakeshore Loop"]]
    LEVEE[["B. Levee Bike Trail"]]
    RAIL[["C. Rail-with-Trail"]]
    BAYOU[["D. Brushy Bayou / WMA"]]
    SRTS[["E. Safe Routes to School"]]
    FAC[["Rec center / fields / pier"]]
    GIS[["QGIS platform + lidar"]]

    TAP --> LOOP & LEVEE & RAIL & SRTS
    RTP --> LOOP & LEVEE & BAYOU
    LWCF --> LOOP & BAYOU & FAC
    LOF -. match .-> LWCF & RTP & BFA
    BFA --> FAC
    LCDBG --> FAC
    USDA --> FAC & GIS
    SEDAP --> LEVEE & RAIL & GIS
    CO --> FAC & GIS
    RTC --> LEVEE & RAIL
    AARP --> LOOP & SRTS
    PFB --> LOOP & LEVEE
    USGS --> GIS
    FEMA --> GIS
    QGIS --> GIS
    ESRI -. bridge .-> GIS
```

## 5. Rail corridor decision tree

```mermaid
flowchart TD
    S[Lake Providence Line<br/>55 km, disused, owned by Delta Southern / Patriot Rail] --> Q1{Formally abandoned<br/>at the STB?}
    Q1 -- No (today) --> RWT[Ask Patriot Rail for a<br/>rail-with-trail license<br/>on 3-4 mi through town]
    RWT --> Q2{License granted?}
    Q2 -- Yes --> BUILD1[Design + fund with<br/>TAP / RTP / RTC / DRA]
    Q2 -- No --> ALT[Fall back to lakeshore loop<br/>and levee trail; keep monitoring<br/>STB docket FD 36443]
    Q1 -- Yes (future filing) --> RB[File railbanking request<br/>16 U.S.C. 1247(d)<br/>within the comment window]
    RB --> NITU[STB issues NITU /<br/>interim trail use order]
    NITU --> ACQ[Negotiate corridor transfer<br/>to Recreation District]
    ACQ --> BUILD2[Full rail-trail<br/>TAP + LWCF + RTP + DRA]
```

## 6. Twelve-month timeline

```mermaid
gantt
    title East Carroll Parks & Trails: first year
    dateFormat  YYYY-MM-DD
    axisFormat  %b %Y
    section Setup
    Create Recreation District          :a1, 2026-11-01, 45d
    SAM.gov registration                :a2, 2026-11-01, 40d
    Capital Outlay request (Nov 1)      :milestone, 2026-11-01, 0d
    Rail-with-trail letter to Patriot   :a3, 2026-11-15, 15d
    section GIS
    USGS 3DEP planning estimate         :milestone, 2026-11-13, 0d
    USGS 3DEP submission                :milestone, 2026-12-04, 0d
    QField asset inventory              :g1, 2026-12-01, 60d
    PostGIS hub + public web map        :g2, 2027-02-01, 120d
    section Planning
    NPS RTCA application                :p1, 2027-01-15, 45d
    Public meetings + master plan       :p2, 2027-01-01, 150d
    section Applications
    AARP Community Challenge            :milestone, 2027-03-04, 0d
    TAP call (expected)                 :f1, 2027-02-15, 45d
    LWCF (Apr 1)                        :milestone, 2027-04-01, 0d
    RTC trail grants (spring)           :f2, 2027-04-01, 40d
    RTP (Jul 1)                         :milestone, 2027-07-01, 0d
    DRA SEDAP NOFA                      :f3, 2027-06-01, 60d
    Louisiana Outdoors Forever pre-app  :f4, 2027-07-06, 60d
    LCDBG FY28 needs hearing            :f5, 2027-08-01, 30d
```
