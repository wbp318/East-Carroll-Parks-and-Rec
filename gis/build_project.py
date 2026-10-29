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
from qgis.PyQt.QtGui import QColor

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


def style_fill(l, color, outline="#333333", width=0.3, opacity=1.0):
    s = QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width)})
    s.setOpacity(opacity)
    l.renderer().setSymbol(s)


def style_line(l, color, width):
    l.renderer().setSymbol(QgsLineSymbol.createSimple({"color": color, "width": str(width)}))


style_fill(parish, "255,255,255,0", "#000000", 0.8)
POVERTY_BREAKS = [(0, 10, "#fee5d9"), (10, 20, "#fcae91"), (20, 30, "#fb6a4a"), (30, 40, "#de2d26"), (40, 100, "#a50f15")]


def poverty_renderer():
    ranges = []
    for lo, hi, col in POVERTY_BREAKS:
        sym = QgsFillSymbol.createSimple({"color": col, "outline_color": "#777777", "outline_width": "0.15"})
        label = f"{lo}% to {hi}%" if hi < 100 else f"{lo}% and up"
        ranges.append(QgsRendererRange(lo, hi, sym, label))
    r = QgsGraduatedSymbolRenderer("poverty_pct", ranges)
    r.setClassAttribute("poverty_pct")
    return r


tracts.setRenderer(poverty_renderer())
tracts.setOpacity(0.7)
la_tracts.setRenderer(poverty_renderer())
la_tracts.setOpacity(0.7)
style_fill(la_parishes, "255,255,255,0", "#333333", 0.5)
ls = QgsPalLayerSettings()
ls.fieldName = "NAME"
ls.enabled = True
tf = QgsTextFormat()
tf.setSize(8)
ls.setFormat(tf)
la_parishes.setLabelsEnabled(True)
la_parishes.setLabeling(QgsVectorLayerSimpleLabeling(ls))
style_fill(gap, "255,200,0,0", "#ff9900", 1.0)
style_fill(walk, "#3cb371", "#2e8b57", 0.4, 0.45)
style_fill(awater, "#a6cee3", "#6baed6", 0.1)
style_line(lwater, "#6baed6", 0.3)
style_line(roads, "#999999", 0.25)
style_fill(places, "255,255,255,0", "#6a3d9a", 0.6)
colors = {"park": "#33a02c", "playground": "#b2df8a", "pitch": "#1f78b4", "sports_centre": "#1f78b4",
          "school": "#ff7f00", "community_centre": "#e31a1c", "library": "#e31a1c", "slipway": "#000080",
          "camp_site": "#6a3d9a", "picnic_site": "#6a3d9a", "attraction": "#fb9a99", "museum": "#fb9a99",
          "protected_area": "#006d2c"}
cats = [QgsRendererCategory(tag, QgsMarkerSymbol.createSimple({"color": c, "outline_color": "#000000", "size": "2.6"}), tag)
        for tag, c in colors.items()]
cats.append(QgsRendererCategory("", QgsMarkerSymbol.createSimple({"color": "#aaaaaa", "size": "1.8"}), "other"))
assets.setRenderer(QgsCategorizedSymbolRenderer("tag", cats))
for lyr, field, size in ((places, "NAME", 9), (assets, "name", 7)):
    ls = QgsPalLayerSettings()
    ls.fieldName = field
    ls.enabled = True
    tf = QgsTextFormat()
    tf.setSize(size)
    ls.setFormat(tf)
    lyr.setLabelsEnabled(True)
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(ls))

trail_style = {"trails_named": ("#d7191c", 0.9), "trails_paths": ("#fdae61", 0.5), "trails_tracks": ("#888888", 0.3)}
for name, (col, w) in trail_style.items():
    if name in trail_layers:
        style_line(trail_layers[name], col, w)
if "trails_named" in trail_layers:
    ls = QgsPalLayerSettings()
    ls.fieldName = "name"
    ls.enabled = True
    ls.placement = Qgis.LabelPlacement.Line
    tf = QgsTextFormat()
    tf.setSize(7)
    ls.setFormat(tf)
    trail_layers["trails_named"].setLabelsEnabled(True)
    trail_layers["trails_named"].setLabeling(QgsVectorLayerSimpleLabeling(ls))

extra = []
if rail is not None:
    rail.renderer().setSymbol(QgsLineSymbol.createSimple({"color": "#000000", "width": "1.1", "line_style": "dash"}))
    levee.renderer().setSymbol(QgsLineSymbol.createSimple({"color": "#8c510a", "width": "0.9"}))
    style_fill(rail_buf, "#1f78b4", "#1f78b4", 0.2, 0.15)
    extra = [rail, levee, rail_buf]
root = proj.layerTreeRoot()
for l in (assets, places) + tuple(trail_layers.values()) + tuple(extra) + (roads, lwater, awater, walk, gap, tracts, schools_d, bgs, parish):
    proj.addMapLayer(l, False)
    root.addLayer(l)          # appended in order, so the first added draws on top
for hidden in (bgs, schools_d):
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
proj.write(os.path.join(ROOT, "east_carroll_parks.qgz"))

ms = QgsMapSettings()
ms.setLayers([assets, places] + list(trail_layers.values()) + extra + [roads, awater, walk, gap, tracts, parish])
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
