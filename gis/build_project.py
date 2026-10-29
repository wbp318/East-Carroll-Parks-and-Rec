"""Build the East Carroll Parish parks & rec QGIS project.

Run with:  C:\\OSGeo4W\\bin\\python-qgis-ltr.bat gis\\build_project.py

Inputs (gis/data/raw):  Census TIGER 2024 shapefiles, ACS 2023 5-yr tract JSON,
OpenStreetMap recreation features (Overpass JSON).
Outputs: gis/data/processed/east_carroll.gpkg, gis/east_carroll_parks.qgz,
gis/east_carroll_overview.png
"""
import os, sys, json, zipfile, glob
from collections import Counter

from qgis.core import *
from qgis.PyQt.QtCore import QSize, QVariant
from qgis.PyQt.QtGui import QColor, QFont

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed")
GPKG = os.path.join(OUT, "east_carroll.gpkg")
os.makedirs(OUT, exist_ok=True)

QgsApplication.setPrefixPath(r"C:\OSGeo4W\apps\qgis-ltr", True)
app = QgsApplication([], False)
app.initQgis()
sys.path.append(r"C:\OSGeo4W\apps\qgis-ltr\python\plugins")
import processing
from processing.core.Processing import Processing
Processing.initialize()

for z in glob.glob(os.path.join(RAW, "*.zip")):
    d = os.path.join(RAW, os.path.basename(z)[:-4])
    if not os.path.isdir(d):
        zipfile.ZipFile(z).extractall(d)


def shp(name):
    return glob.glob(os.path.join(RAW, name, "*.shp"))[0]


if os.path.exists(GPKG):
    os.remove(GPKG)


def save(layer, name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = name
    opts.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(GPKG)
                                 else QgsVectorFileWriter.CreateOrOverwriteFile)
    r = QgsVectorFileWriter.writeAsVectorFormatV3(layer, GPKG, QgsProject.instance().transformContext(), opts)
    assert r[0] == QgsVectorFileWriter.NoError, (name, r)
    return QgsVectorLayer(f"{GPKG}|layername={name}", name, "ogr")


def run(alg, **params):
    params.setdefault("OUTPUT", "memory:")
    return processing.run(alg, params)["OUTPUT"]


def extract(path, expr, name):
    lyr = QgsVectorLayer(path, name, "ogr")
    assert lyr.isValid(), path
    return save(run("native:extractbyexpression", INPUT=lyr, EXPRESSION=expr), name)


parish = extract(shp("tl_2024_us_county"), "\"GEOID\" = '22035'", "parish_boundary")
tracts = extract(shp("tl_2024_22_tract"), "\"COUNTYFP\" = '035'", "census_tracts")
bgs = extract(shp("tl_2024_22_bg"), "\"COUNTYFP\" = '035'", "block_groups")
roads = save(QgsVectorLayer(shp("tl_2024_22035_roads"), "roads", "ogr"), "roads")
awater = save(QgsVectorLayer(shp("tl_2024_22035_areawater"), "water_areas", "ogr"), "water_areas")
lwater = save(QgsVectorLayer(shp("tl_2024_22035_linearwater"), "water_lines", "ogr"), "water_lines")
places = save(run("native:extractbylocation", INPUT=QgsVectorLayer(shp("tl_2024_22_place"), "p", "ogr"),
                  PREDICATE=[6], INTERSECT=parish), "municipalities")
schools_d = save(run("native:extractbylocation", INPUT=QgsVectorLayer(shp("tl_2024_22_unsd"), "u", "ogr"),
                     PREDICATE=[0], INTERSECT=parish), "school_district")

# ---- ACS join to tracts ----
def acs_table(table, cols):
    """Read an ACS 2023 5-yr summary-file table (pipe-delimited) for East Carroll geographies."""
    out = {}
    with open(os.path.join(RAW, f"acs_{table}.dat")) as fh:
        hdr = fh.readline().rstrip("\n").split("|")
        idx = [hdr.index(c) for c in cols]
        for line in fh:
            if "US22035" not in line:
                continue
            parts = line.rstrip("\n").split("|")
            vals = []
            for i in idx:
                try:
                    x = float(parts[i])
                    vals.append(None if x < 0 else x)
                except ValueError:
                    vals.append(None)
            out[parts[0]] = vals
    return out


mhi = acs_table("b19013", ["B19013_E001"])                      # median household income
pov = acs_table("b17021", ["B17021_E001", "B17021_E002"])       # poverty universe, below poverty
pop = acs_table("b01003", ["B01003_E001"])                      # total population
acs_summary = {}
for geo in pop:
    p = pov.get(geo, [None, None])
    acs_summary[geo] = {
        "population": pop[geo][0],
        "med_hh_income": mhi.get(geo, [None])[0],
        "poverty_pct": round(100 * p[1] / p[0], 1) if p[0] else None,
    }
json.dump(acs_summary, open(os.path.join(OUT, "acs_2023_east_carroll.json"), "w"), indent=1)
fields = ["population", "med_hh_income", "poverty_pct"]
tracts.dataProvider().addAttributes([QgsField(k, QVariant.Double) for k in fields])
tracts.updateFields()
gi = tracts.fields().indexOf("GEOID")
tracts.startEditing()
for f in tracts.getFeatures():
    r = acs_summary.get("1400000US" + f[gi])
    if not r:
        continue
    for k in fields:
        tracts.changeAttributeValue(f.id(), tracts.fields().indexOf(k), r[k])
tracts.commitChanges()
bgs.dataProvider().addAttributes([QgsField(k, QVariant.Double) for k in fields])
bgs.updateFields()
bgs.startEditing()
for f in bgs.getFeatures():
    r = acs_summary.get("1500000US" + f["GEOID"])
    if r:
        for k in fields:
            bgs.changeAttributeValue(f.id(), bgs.fields().indexOf(k), r[k])
bgs.commitChanges()

# ---- Statewide context: all LA parishes + all LA tracts with poverty (toggle group) ----
def acs_state(table, cols, prefix="1400000US22"):
    out = {}
    with open(os.path.join(RAW, f"acs_{table}.dat")) as fh:
        hdr = fh.readline().rstrip("\n").split("|")
        idx = [hdr.index(c) for c in cols]
        for line in fh:
            if not line.startswith(prefix):
                continue
            parts = line.rstrip("\n").split("|")
            vals = []
            for i in idx:
                try:
                    x = float(parts[i])
                    vals.append(None if x < 0 else x)
                except ValueError:
                    vals.append(None)
            out[parts[0][len("1400000US"):]] = vals
    return out


la_parishes = extract(shp("tl_2024_us_county"), "\"STATEFP\" = '22'", "la_parishes")
la_tracts = save(QgsVectorLayer(shp("tl_2024_22_tract"), "t", "ogr"), "la_tracts")
st_pov = acs_state("b17021", ["B17021_E001", "B17021_E002"])
st_mhi = acs_state("b19013", ["B19013_E001"])
st_pop = acs_state("b01003", ["B01003_E001"])
la_tracts.dataProvider().addAttributes([QgsField(k, QVariant.Double) for k in ("population", "med_hh_income", "poverty_pct")])
la_tracts.updateFields()
la_tracts.startEditing()
for f in la_tracts.getFeatures():
    g = f["GEOID"]
    pv = st_pov.get(g, [None, None])
    vals = {"population": st_pop.get(g, [None])[0], "med_hh_income": st_mhi.get(g, [None])[0],
            "poverty_pct": round(100 * pv[1] / pv[0], 1) if pv[0] else None}
    for k, v in vals.items():
        la_tracts.changeAttributeValue(f.id(), la_tracts.fields().indexOf(k), v)
la_tracts.commitChanges()

# ---- OSM recreation assets ----
osm = json.load(open(os.path.join(RAW, "osm_rec.json")))["elements"]
assets = QgsVectorLayer("Point?crs=EPSG:4326&field=osm_id:string&field=name:string&field=category:string&field=tag:string",
                        "rec_assets", "memory")
feats = []
for e in osm:
    t = e.get("tags", {})
    lat = e.get("lat") or e.get("center", {}).get("lat")
    lon = e.get("lon") or e.get("center", {}).get("lon")
    if lat is None:
        continue
    cat = tag = ""
    for k in ("leisure", "amenity", "tourism", "historic", "boundary", "natural"):
        if k in t:
            cat, tag = k, t[k]
            break
    f = QgsFeature(assets.fields())
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
    f.setAttributes([f"{e['type']}/{e['id']}", t.get("name", ""), cat, tag])
    feats.append(f)
assets.dataProvider().addFeatures(feats)
assets.updateExtents()
assets = save(assets, "rec_assets")

# ---- Half-mile (10-minute walk) service areas around existing parks/fields ----
parks = run("native:extractbyexpression", INPUT=assets,
            EXPRESSION="\"tag\" in ('park','playground','pitch','sports_centre','swimming_pool','track')")
parks_utm = run("native:reprojectlayer", INPUT=parks, TARGET_CRS="EPSG:26915")
buf = run("native:buffer", INPUT=parks_utm, DISTANCE=804.67, DISSOLVE=True)
walk = save(run("native:reprojectlayer", INPUT=buf, TARGET_CRS="EPSG:4326"), "park_walkshed_half_mile")
gap = save(run("native:extractbylocation", INPUT=bgs, PREDICATE=[2], INTERSECT=walk), "block_groups_no_park_access")

# ---- Trail linework from the Take-a-Hike repo (OSM paths/tracks/footways, bbox search) ----
trail_src = os.path.join(RAW, "takeahike_east_carroll_trails.geojson")
trail_layers = {}
if os.path.exists(trail_src):
    tl = QgsVectorLayer(trail_src + "|geometrytype=LineString", "trails_src", "ogr")
    assert tl.isValid(), trail_src
    clipped = run("native:clip", INPUT=tl, OVERLAY=parish)
    clipped = run("native:fieldcalculator", INPUT=clipped, FIELD_NAME="length_km_clipped",
                  FIELD_TYPE=0, FIELD_LENGTH=10, FIELD_PRECISION=2,
                  FORMULA="round(length(transform($geometry,'EPSG:4326','EPSG:26915'))/1000, 2)")
    for name, expr in (("trails_named", "\"name\" IS NOT NULL AND \"name\" <> ''"),
                       ("trails_paths", "(\"name\" IS NULL OR \"name\" = '') AND \"kind\" IN ('path','footway','cycleway','bridleway','steps')"),
                       ("trails_tracks", "(\"name\" IS NULL OR \"name\" = '') AND \"kind\" = 'track'")):
        trail_layers[name] = save(run("native:extractbyexpression", INPUT=clipped, EXPRESSION=expr), name)

# ---- Rail corridors and levees (OSM) ----
rail_src = os.path.join(RAW, "osm_rail_levee.json")
rail = levee = None
if os.path.exists(rail_src):
    els = json.load(open(rail_src))["elements"]
    rail_mem = QgsVectorLayer("LineString?crs=EPSG:4326&field=osm_id:string&field=name:string&field=operator:string"
                              "&field=railway:string&field=usage:string", "rail", "memory")
    levee_mem = QgsVectorLayer("LineString?crs=EPSG:4326&field=osm_id:string&field=name:string&field=feature:string",
                               "levee", "memory")
    rf, lf = [], []
    for e in els:
        if e["type"] != "way" or "geometry" not in e:
            continue
        t = e.get("tags", {})
        line = QgsGeometry.fromPolylineXY([QgsPointXY(p["lon"], p["lat"]) for p in e["geometry"]])
        if "railway" in t:
            f = QgsFeature(rail_mem.fields())
            f.setGeometry(line)
            f.setAttributes([f"way/{e['id']}", t.get("name", ""), t.get("operator", ""), t["railway"], t.get("usage", "")])
            rf.append(f)
        elif t.get("man_made") in ("dyke", "embankment"):
            f = QgsFeature(levee_mem.fields())
            f.setGeometry(line)
            f.setAttributes([f"way/{e['id']}", t.get("name", ""), t["man_made"]])
            lf.append(f)
    rail_mem.dataProvider().addFeatures(rf)
    levee_mem.dataProvider().addFeatures(lf)
    for m in (rail_mem, levee_mem):
        m.updateExtents()
    rail = save(run("native:fieldcalculator", INPUT=run("native:clip", INPUT=rail_mem, OVERLAY=parish),
                    FIELD_NAME="length_km", FIELD_TYPE=0, FIELD_LENGTH=10, FIELD_PRECISION=2,
                    FORMULA="round(length(transform($geometry,'EPSG:4326','EPSG:26915'))/1000, 2)"), "rail_corridors")
    levee = save(run("native:fieldcalculator", INPUT=run("native:clip", INPUT=levee_mem, OVERLAY=parish),
                     FIELD_NAME="length_km", FIELD_TYPE=0, FIELD_LENGTH=10, FIELD_PRECISION=2,
                     FORMULA="round(length(transform($geometry,'EPSG:4326','EPSG:26915'))/1000, 2)"), "levees")
    # 1-mile catchment around the rail corridor for population served
    rail_buf = run("native:reprojectlayer", INPUT=run("native:buffer", INPUT=run("native:reprojectlayer", INPUT=rail,
                   TARGET_CRS="EPSG:26915"), DISTANCE=1609.34, DISSOLVE=True), TARGET_CRS="EPSG:4326")
    rail_buf = save(rail_buf, "rail_corridor_1mi_catchment")

# ---- Project + styling ----
proj = QgsProject.instance()
proj.setCrs(QgsCoordinateReferenceSystem("EPSG:4269"))
proj.setTitle("East Carroll Parish Parks & Recreation")


# ---------- Styling: calm palette, plain-English names ----------
def style_fill(l, color, outline="#333333", width=0.3, opacity=1.0):
    s = QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width)})
    s.setOpacity(opacity)
    l.renderer().setSymbol(s)


def style_line(l, color, width, style="solid"):
    l.renderer().setSymbol(QgsLineSymbol.createSimple({"color": color, "width": str(width), "line_style": style}))


def label(l, field, size=8, color="#222222", italic=False, halo=True, along_line=False):
    ls = QgsPalLayerSettings()
    ls.fieldName = field
    ls.enabled = True
    if along_line:
        ls.placement = Qgis.LabelPlacement.Line
    tf = QgsTextFormat()
    tf.setSize(size)
    tf.setColor(QColor(color))
    f = QFont("Arial")
    f.setItalic(italic)
    tf.setFont(f)
    if halo:
        buf = tf.buffer()
        buf.setEnabled(True)
        buf.setSize(0.8)
        buf.setColor(QColor("#ffffff"))
        tf.setBuffer(buf)
    ls.setFormat(tf)
    l.setLabelsEnabled(True)
    l.setLabeling(QgsVectorLayerSimpleLabeling(ls))


# Poverty: muted tan-to-brown sequential, same breaks parish and statewide
POVERTY_BREAKS = [(0, 10, "#fbf6ee"), (10, 20, "#efdfc2"), (20, 30, "#dbbb8a"), (30, 40, "#c0905a"), (40, 100, "#9a6a38")]


def poverty_renderer():
    ranges = []
    for lo, hi, col in POVERTY_BREAKS:
        sym = QgsFillSymbol.createSimple({"color": col, "outline_color": "#b0a090", "outline_width": "0.15"})
        lbl = f"{lo} to {hi}% of residents below poverty" if hi < 100 else f"{lo}% or more below poverty"
        ranges.append(QgsRendererRange(lo, hi, sym, lbl))
    r = QgsGraduatedSymbolRenderer("poverty_pct", ranges)
    r.setClassAttribute("poverty_pct")
    return r


tracts.setRenderer(poverty_renderer())
tracts.setOpacity(0.6)
la_tracts.setRenderer(poverty_renderer())
la_tracts.setOpacity(0.6)
style_fill(parish, "255,255,255,0", "#222222", 0.9)
style_fill(la_parishes, "255,255,255,0", "#555555", 0.4)
label(la_parishes, "NAME", 8, "#444444")
style_fill(places, "255,255,255,0", "#5b6b8c", 0.7)
label(places, "NAME", 10, "#2c3e50")
style_fill(awater, "#cfe3f2", "#9fc3de", 0.1)
style_line(lwater, "#9fc3de", 0.25)
# Roads: heavier for highways (TIGER MTFCC S1100/S1200), lighter for local streets; small labels when zoomed in
road_cats = []
for codes, col, w, lbl in ((("S1100",), "#4a4a4a", 0.8, "US / state highway"),
                           (("S1200",), "#5c5c5c", 0.55, "Secondary road"),
                           (("S1400", "S1500", "S1630", "S1640", "S1710", "S1720", "S1730", "S1740", "S1750", "S1780", "S1820", "S1830"), "#8a8a8a", 0.3, "Local road")):
    sym = QgsLineSymbol.createSimple({"color": col, "width": str(w)})
    for c in codes:
        road_cats.append(QgsRendererCategory(c, sym.clone(), lbl))
road_cats.append(QgsRendererCategory("", QgsLineSymbol.createSimple({"color": "#8a8a8a", "width": "0.3"}), "Other"))
roads.setRenderer(QgsCategorizedSymbolRenderer("MTFCC", road_cats))
rl = QgsPalLayerSettings()
rl.fieldName = "FULLNAME"
rl.enabled = True
rl.placement = Qgis.LabelPlacement.Line
rl.lineSettings().setMergeLines(True)
rl.priority = 3
rl.scaleVisibility = True
rl.maximumScale = 1          # most zoomed in
rl.minimumScale = 75000      # hide labels when zoomed out past 1:75,000
rtf = QgsTextFormat()
rtf.setFont(QFont("Arial"))
rtf.setSize(6.5)
rtf.setColor(QColor("#3c3c3c"))
rb = rtf.buffer()
rb.setEnabled(True)
rb.setSize(0.7)
rb.setColor(QColor("white"))
rtf.setBuffer(rb)
rl.setFormat(rtf)
roads.setLabelsEnabled(True)
roads.setLabeling(QgsVectorLayerSimpleLabeling(rl))
style_fill(walk, "#9fd8a8", "#4c9e5c", 0.3, 0.5)
style_fill(gap, "255,255,255,0", "#d98e04", 0.9)
style_fill(rail_buf if rail is not None else walk, "#dde7f0", "#dde7f0", 0.0, 0.5)

# Assets: collapse OSM tags into a handful of readable classes
ASSET_CLASS = {
    "park": ("Park or playground", "#27ae60", "diamond", 3.5),
    "playground": ("Park or playground", "#27ae60", "diamond", 3.5),
    "pitch": ("Ball field, court or pool", "#3b6fb6", "square", 2.6),
    "sports_centre": ("Ball field, court or pool", "#3b6fb6", "square", 2.6),
    "swimming_pool": ("Ball field, court or pool", "#3b6fb6", "square", 2.6),
    "track": ("Ball field, court or pool", "#3b6fb6", "square", 2.6),
    "school": ("School", "#e08a1e", "triangle", 3.0),
    "library": ("Library or community center", "#8e5ea2", "diamond", 3.0),
    "community_centre": ("Library or community center", "#8e5ea2", "diamond", 3.0),
    "slipway": ("Boat ramp", "#1f3f73", "pentagon", 3.0),
    "museum": ("Museum or historic site", "#b5651d", "star", 3.2),
    "farm": ("Museum or historic site", "#b5651d", "star", 3.2),
    "attraction": ("Museum or historic site", "#b5651d", "star", 3.2),
    "camp_site": ("Camp or picnic site", "#27ae60", "diamond", 3.5),
    "picnic_site": ("Camp or picnic site", "#27ae60", "diamond", 3.5),
    "nature_reserve": ("Wildlife management area", "#27ae60", "diamond", 4.0),
    "protected_area": ("Wildlife management area", "#27ae60", "diamond", 4.0),
    "water": ("Named lake or bayou", "#6fa8d6", "circle", 2.0),
}
assets.dataProvider().addAttributes([QgsField("asset_class", QVariant.String)])
assets.updateFields()
assets.startEditing()
ci = assets.fields().indexOf("asset_class")
for f in assets.getFeatures():
    assets.changeAttributeValue(f.id(), ci, ASSET_CLASS.get(f["tag"], ("Other", "", "", 0))[0])
assets.commitChanges()
cats, seen = [], set()
for tag, (cls, col, shape, size) in ASSET_CLASS.items():
    if cls in seen:
        continue
    seen.add(cls)
    sym = QgsMarkerSymbol.createSimple({"color": col, "outline_color": "#ffffff", "outline_width": "0.4",
                                        "name": shape, "size": str(size)})
    cats.append(QgsRendererCategory(cls, sym, cls))
cats.append(QgsRendererCategory("Other", QgsMarkerSymbol.createSimple({"color": "#b0b0b0", "outline_color": "#ffffff", "size": "2.0"}), "Other"))
assets.setRenderer(QgsCategorizedSymbolRenderer("asset_class", cats))
label(assets, "name", 7, "#333333")

# Trails and corridors: same look as Take-a-Hike's add_place_layer.py
trail_names = None
if "trails_named" in trail_layers:
    named = trail_layers["trails_named"]
    style_line(named, "#c0392b", 1.2)
    ls = QgsPalLayerSettings()
    ls.fieldName = "name"
    ls.enabled = True
    ls.placement = Qgis.LabelPlacement.Line
    ls.lineSettings().setMergeLines(True)
    ls.priority = 10
    tf = QgsTextFormat()
    tf.setFont(QFont("Arial", 9))
    tf.setSize(9)
    tf.setColor(QColor("#7b241c"))
    b = tf.buffer()
    b.setEnabled(True)
    b.setSize(1)
    b.setColor(QColor("white"))
    tf.setBuffer(b)
    ls.setFormat(tf)
    named.setLabelsEnabled(True)
    named.setLabeling(QgsVectorLayerSimpleLabeling(ls))
    # midpoint of each named way, bold label that stays visible at any scale
    mem = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=kind:string&field=length_km:double&field=osm_url:string",
                         "trail_names", "memory")
    pts = []
    for w in named.getFeatures():
        g = w.geometry()
        f = QgsFeature(mem.fields())
        f.setGeometry(g.interpolate(g.length() / 2))
        f.setAttributes([w["name"], w["kind"], w["length_km_clipped"], w["osm_url"]])
        pts.append(f)
    mem.dataProvider().addFeatures(pts)
    mem.updateExtents()
    trail_names = save(mem, "trail_names")
    trail_names.renderer().setSymbol(QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": "#c0392b", "outline_color": "#ffffff", "outline_width": "0.4", "size": "2.6"}))
    lab = QgsPalLayerSettings()
    lab.fieldName = "name"
    lab.enabled = True
    lab.placement = Qgis.LabelPlacement.OrderedPositionsAroundPoint
    lab.priority = 10
    tf2 = QgsTextFormat()
    tf2.setFont(QFont("Arial", 9, QFont.Bold))
    tf2.setSize(9)
    tf2.setColor(QColor("#7b241c"))
    b2 = tf2.buffer()
    b2.setEnabled(True)
    b2.setSize(1.2)
    b2.setColor(QColor("white"))
    tf2.setBuffer(b2)
    lab.setFormat(tf2)
    trail_names.setLabelsEnabled(True)
    trail_names.setLabeling(QgsVectorLayerSimpleLabeling(lab))
if "trails_paths" in trail_layers:
    style_line(trail_layers["trails_paths"], "#e67e22", 0.9)
if "trails_tracks" in trail_layers:
    style_line(trail_layers["trails_tracks"], "#7f8c8d", 0.35)
extra = []
if rail is not None:
    style_line(rail, "#2b2b2b", 1.2, "dash")
    style_line(levee, "#7f5f2a", 1.0)
    extra = [rail, levee, rail_buf]

# Legend / layer-panel names
NAMES = [
    (assets, "Parks, fields, schools and other sites"),
    (trail_names, "Trail names"),
    (places, "Lake Providence town limits"),
    (parish, "East Carroll Parish boundary"),
    (tracts, "Poverty rate by census tract (ACS 2023)"),
    (la_tracts, "Louisiana tracts: poverty rate (ACS 2023)"),
    (la_parishes, "Louisiana parish boundaries"),
    (walk, "Within a half mile of a park or field"),
    (gap, "Block group with no park within a half mile"),
    (awater, "Lakes and rivers"),
    (lwater, "Streams and bayous"),
    (roads, "Roads"),
    (bgs, "Census block groups (ACS 2023)"),
    (schools_d, "School district"),
]
if trail_layers:
    NAMES += [(trail_layers.get("trails_named"), "Named trails and tracks"),
              (trail_layers.get("trails_paths"), "Paths and sidewalks"),
              (trail_layers.get("trails_tracks"), "Farm and levee tracks (unnamed)")]
if rail is not None:
    NAMES += [(rail, "Rail corridor (out of service)"), (levee, "Mississippi River levee"),
              (rail_buf, "Within one mile of the rail corridor")]
for lyr, nm in NAMES:
    if lyr is not None:
        lyr.setName(nm)
root = proj.layerTreeRoot()
for l in (assets,) + ((trail_names,) if trail_names is not None else ()) + (places,) + tuple(trail_layers.values()) + tuple(extra) + (roads, lwater, awater, walk, gap, tracts, schools_d, bgs, parish):
    proj.addMapLayer(l, False)
    root.addLayer(l)          # appended in order, so the first added draws on top
for hidden in (bgs, schools_d):
    if hidden is None:
        continue
    root.findLayer(hidden.id()).setItemVisibilityChecked(False)
la_group = root.addGroup("Louisiana statewide (toggle)")
for l in (la_parishes, la_tracts):
    proj.addMapLayer(l, False)
    la_group.addLayer(l)
la_group.setItemVisibilityChecked(False)
osm_l = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0", "OpenStreetMap", "wms")
proj.addMapLayer(osm_l, False)
root.addLayer(osm_l)          # last = bottom of the stack
# default view: parish extent, so QGIS opens zoomed to the data instead of 1:1
view = proj.viewSettings()
ext0 = parish.extent()
ext0.scale(1.05)
view.setDefaultViewExtent(QgsReferencedRectangle(ext0, parish.crs()))
view.setPresetFullExtent(QgsReferencedRectangle(ext0, parish.crs()))
# ---- Print layout with legend (Project > Layouts > "East Carroll Parks Map") ----
from qgis.core import (QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLegend, QgsLayoutItemLabel,
                       QgsLayoutItemScaleBar, QgsLayoutItemPicture, QgsLayoutPoint, QgsLayoutSize,
                       QgsUnitTypes, QgsLayoutExporter, QgsLayerTree)
layout = QgsPrintLayout(proj)
layout.initializeDefaults()
layout.setName("East Carroll Parks Map")
page = layout.pageCollection().page(0)
page.setPageSize("Letter", QgsLayoutItemPage.Orientation.Portrait)

title = QgsLayoutItemLabel(layout)
title.setText("East Carroll Parish Parks & Recreation: Assets, Trails, and Need")
title.setFont(QFont("Arial", 16, QFont.Bold))
title.attemptMove(QgsLayoutPoint(10, 8, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(196, 10, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

lmap = QgsLayoutItemMap(layout)
lmap.attemptMove(QgsLayoutPoint(10, 20, QgsUnitTypes.LayoutMillimeters))
lmap.attemptResize(QgsLayoutSize(135, 240, QgsUnitTypes.LayoutMillimeters))
lmap.setCrs(parish.crs())
lmap.setLayers([assets] + ([trail_names] if trail_names is not None else []) + [places] + list(trail_layers.values()) + extra + [roads, awater, walk, gap, tracts, parish])
lmap.setExtent(ext0)
lmap.setFrameEnabled(True)
layout.addLayoutItem(lmap)

legend = QgsLayoutItemLegend(layout)
legend.setTitle("Legend")
legend.setLinkedMap(lmap)
legend.setAutoUpdateModel(False)
lt = QgsLayerTree()
for l in [assets] + ([trail_names] if trail_names is not None else []) + list(trail_layers.values()) + extra + [walk, gap, tracts, awater, places, parish]:
    lt.addLayer(l)
legend.model().setRootGroup(lt)
legend.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 11, QFont.Bold))
legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Arial", 8, QFont.Bold))
legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 7))
legend.setSymbolHeight(3)
legend.setSymbolWidth(5)
legend.attemptMove(QgsLayoutPoint(150, 20, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(56, 200, QgsUnitTypes.LayoutMillimeters))
legend.setFrameEnabled(True)
layout.addLayoutItem(legend)

sb = QgsLayoutItemScaleBar(layout)
sb.setLinkedMap(lmap)
sb.applyDefaultSettings()
sb.setUnits(QgsUnitTypes.DistanceMiles)
sb.setUnitLabel("mi")
sb.setUnitsPerSegment(2)
sb.setNumberOfSegments(3)
sb.setNumberOfSegmentsLeft(0)
sb.attemptMove(QgsLayoutPoint(12, 250, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

north = QgsLayoutItemPicture(layout)
north.setPicturePath(r"C:\OSGeo4W\apps\qgis-ltr\svg\arrows\NorthArrow_02.svg")
north.attemptMove(QgsLayoutPoint(132, 24, QgsUnitTypes.LayoutMillimeters))
north.attemptResize(QgsLayoutSize(10, 14, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(north)

credit = QgsLayoutItemLabel(layout)
credit.setText("Sources: Census TIGER 2024, ACS 2023 5-yr (tract poverty), OpenStreetMap (assets, trails, rail, levees). "
               "Built with QGIS. github.com/wbp318/East-Carroll-Parks-and-Rec")
credit.setFont(QFont("Arial", 7))
credit.attemptMove(QgsLayoutPoint(10, 263, QgsUnitTypes.LayoutMillimeters))
credit.attemptResize(QgsLayoutSize(196, 8, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(credit)

proj.layoutManager().addLayout(layout)
exp = QgsLayoutExporter(layout)
exp.exportToPdf(os.path.join(ROOT, "east_carroll_parks_map.pdf"), QgsLayoutExporter.PdfExportSettings())
png_settings = QgsLayoutExporter.ImageExportSettings()
png_settings.dpi = 150
exp.exportToImage(os.path.join(ROOT, "east_carroll_parks_map.png"), png_settings)

proj.write(os.path.join(ROOT, "east_carroll_parks.qgz"))

ms = QgsMapSettings()
ms.setLayers([assets] + ([trail_names] if trail_names is not None else []) + [places] + list(trail_layers.values()) + extra + [roads, awater, walk, gap, tracts, parish])
ms.setBackgroundColor(QColor(255, 255, 255))
ms.setOutputSize(QSize(1600, 2000))
ms.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
ext = parish.extent()
ext.scale(1.08)
ms.setExtent(ext)
job = QgsMapRendererParallelJob(ms)
job.start()
job.waitForFinished()
job.renderedImage().save(os.path.join(ROOT, "east_carroll_overview.png"))

print("LA parishes:", la_parishes.featureCount(), "| LA tracts:", la_tracts.featureCount())
print("parish:", parish.featureCount(), "| tracts:", tracts.featureCount(), "| block groups:", bgs.featureCount())
print("municipalities:", [f["NAME"] for f in places.getFeatures()])
print("rec assets:", assets.featureCount(), "| parks/fields:", parks.featureCount())
print("block groups outside half-mile park walkshed:", gap.featureCount(), "of", bgs.featureCount(),
      "| pop without walkable park access:", sum((f["population"] or 0) for f in gap.getFeatures()))
print("parish:", acs_summary.get("0500000US22035"))
for name, l in trail_layers.items():
    km = sum((f["length_km_clipped"] or 0) for f in l.getFeatures())
    print(f"{name}: {l.featureCount()} segments, {km:.1f} km inside parish")
if "trails_named" in trail_layers:
    print(sorted({f["name"] for f in trail_layers["trails_named"].getFeatures()}))
if rail is not None:
    print("rail corridors:", rail.featureCount(), "segments,", round(sum(f["length_km"] for f in rail.getFeatures()), 1), "km;",
          Counter((f["name"], f["railway"]) for f in rail.getFeatures()))
    print("levees:", levee.featureCount(), "segments,", round(sum(f["length_km"] for f in levee.getFeatures()), 1), "km")
    served = run("native:extractbylocation", INPUT=bgs, PREDICATE=[0], INTERSECT=rail_buf)
    print("block groups within 1 mi of rail corridor:", served.featureCount(), "pop", sum((f["population"] or 0) for f in served.getFeatures()))
for f in tracts.getFeatures():
    print(" tract", f["GEOID"], "pop", f["population"], "poverty%", f["poverty_pct"], "MHI", f["med_hh_income"])
print(Counter(f["tag"] for f in assets.getFeatures()).most_common(25))
print([(f["name"], f["tag"]) for f in assets.getFeatures() if f["name"]][:60])
app.exitQgis()
