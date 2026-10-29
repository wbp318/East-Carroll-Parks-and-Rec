"""Build docs/ONE_PAGER.pdf: a single letter page for the Police Jury meeting.

    python scripts/build_one_pager.py
"""
import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "ONE_PAGER.pdf")
MAP = os.path.join(ROOT, "gis", "east_carroll_overview.png")

NAVY = colors.HexColor("#1f3f73")
TAN = colors.HexColor("#c0905a")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#f4efe6")

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, spaceAfter=2)
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, leading=11, textColor=GREY, spaceAfter=6)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=NAVY, spaceBefore=4, spaceAfter=2)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=7.8, leading=9.6, alignment=TA_LEFT)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=8, bulletIndent=0, spaceAfter=1)
SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=6.5, leading=8, textColor=GREY)
STAT_N = ParagraphStyle("statn", fontName="Helvetica-Bold", fontSize=14, leading=15, textColor=NAVY)
STAT_L = ParagraphStyle("statl", fontName="Helvetica", fontSize=6.5, leading=8, textColor=GREY)


def bullets(items):
    return [Paragraph(f"<bullet>&bull;</bullet>{t}", BUL) for t in items]


def stat(n, l):
    return [Paragraph(n, STAT_N), Paragraph(l, STAT_L)]


doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.55 * inch, rightMargin=0.55 * inch,
                        topMargin=0.45 * inch, bottomMargin=0.4 * inch,
                        title="Parks, Recreation & Trails Division: East Carroll Parish Police Jury",
                        author="East Carroll Parks and Rec working group")
story = []
story.append(Paragraph("A Parks, Recreation &amp; Trails Division for the East Carroll Parish Police Jury", H1))
story.append(Paragraph("Proposal for the Police Jury, December 2026. Get people outside and moving, and bring home "
                       "federal and state money the parish is not receiving today.", SUB))

# stats row
stats = Table([[stat("7,195", "residents (ACS 2023)"), stat("35.7%", "poverty rate; every tract is low-to-moderate income"),
                stat("$0", "recreation fund in the parish budget today"), stat("0.9 km", "of built trail in the whole parish"),
                stat("55 km", "dormant rail corridor + 48 km levee road")]],
              colWidths=[1.35 * inch] * 5)
stats.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, TAN),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
story.append(stats)
story.append(Spacer(1, 6))

# two columns: left text, right map
left = []
left.append(Paragraph("The ask (one resolution)", H2))
left += bullets([
    "Create a Parks, Recreation &amp; Trails Division of the Police Jury and name a liaison juror.",
    "Authorize the President to sign grant applications; designate the Secretary-Treasurer as financial contact.",
    "No new taxes, no new entity, no new hires in year one. Road crews provide local match in kind.",
])
left.append(Paragraph("Why East Carroll wins these grants", H2))
left += bullets([
    "USDA persistent-poverty county and DRA distressed parish: the highest funding tier in nearly every program.",
    "The parish already owns the raw material: Lake Providence frontage, ball fields, two boat ramps, the Mississippi levee "
    "road, a dormant rail line through every block group, and Bayou Macon WMA on its border.",
    "The Jury already has SAM.gov, a Single Audit history, and road equipment. Nothing waits on paperwork.",
])
left.append(Paragraph("First projects", H2))
left += bullets([
    "<b>Lakeshore Loop</b>: 2 to 3 mile walking and biking path linking downtown, the Cotton Museum, ball fields, "
    "boat ramps, and the schools. Inside town limits; no railroad or Corps permission needed.",
    "<b>Levee bike route</b>: sign the levee crown road as a gravel bike route with a trailhead; a safe alternative to "
    "US 65 for the Mississippi River Trail (US Bicycle Route 45).",
    "<b>Rail-with-trail</b>: license from the railroad for 3 to 4 miles through Lake Providence; railbank if the line is ever abandoned.",
    "<b>Road safety</b>: a parish Local Road Safety Plan (LTAP writes it free) unlocks 100% federal money up to $500k per project.",
])

img_w = 2.55 * inch
img = Image(MAP, width=img_w, height=img_w * 1.12)
right = [img, Paragraph("Poverty by tract (tan), existing parks and schools, dormant rail line (dashed), levee (brown), "
                        "half-mile park walksheds (green). Full map and data: github.com/wbp318/East-Carroll-Parks-and-Rec", SMALL)]

cols = Table([[left, right]], colWidths=[4.55 * inch, 2.75 * inch])
cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (0, 0), 10)]))
story.append(cols)
story.append(Spacer(1, 4))

# funding table
story.append(Paragraph("Money on the table (local share shown; full list of 30 programs in the repo)", H2))
rows = [["Program", "Pays for", "Local share", "Typical award", "Next date"],
        ["LCDBG Public Facilities (LA OCD)", "Rec center, community facilities, streets", "0 to 10%", "$500k to $1.5M", "FY28 cycle, Aug 2027"],
        ["Transportation Alternatives (LA DOTD)", "Shared-use paths, sidewalks, Safe Routes", "20%", "$200k to $1.5M", "Early 2027 call"],
        ["Land & Water Conservation Fund (State Parks)", "Fields, playgrounds, trailhead park", "50%", "$100k to $500k", "April 1, 2027"],
        ["Recreational Trails Program (State Parks)", "Trails, trailheads, levee route signage", "20%", "$50k to $200k", "July 1, 2027"],
        ["USDA Community Facilities", "Rec center, equipment, vehicles", "25 to 75% grant", "$50k to $2M", "Rolling"],
        ["Local Road Safety Program (DOTD/LTAP)", "Signing, striping, shoulders, ped-bike safety", "0%", "up to $500k each", "Quarterly"],
        ["Louisiana Outdoors Forever (LDWF)", "Match for the programs above", "match source", "$100k to $1M", "Pre-app ~July 2027"],
        ["DRA SEDAP (via North Delta LDD)", "Public and transportation infrastructure", "low (distressed)", "$150k to $1M", "~June 2027"],
        ["Capital Outlay (Legislature)", "Any public facility or road", "state bonds", "$250k to $2M", "Request Nov 1"],
        ["USGS 3DEP lidar", "Parish-wide elevation data for design", "~50% partner", "varies", "Nov 13 / Dec 4, 2026"]]
rows = [[Paragraph(c, BODY) for c in r] for r in rows]
ft = Table(rows, colWidths=[2.05 * inch, 2.25 * inch, 0.95 * inch, 1.0 * inch, 1.05 * inch], repeatRows=1)
ft.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
for c in range(5):
    rows[0][c].style = ParagraphStyle("th", parent=BODY, textColor=colors.white, fontName="Helvetica-Bold")
story.append(ft)
story.append(Spacer(1, 5))

story.append(Paragraph("Twelve months", H2))
tl = [["Nov 2026", "Resolution on agenda. Capital Outlay request. USGS lidar partner estimate (Nov 13)."],
      ["Dec 2026", "Division created. USGS lidar submission (Dec 4). First public meeting."],
      ["Jan to Mar 2027", "Parish Road Program adopts trail segments. NPS RTCA application. TAP and AARP applications."],
      ["Apr to Jul 2027", "LWCF (Apr 1). Master plan adopted. RTP (Jul 1). DRA SEDAP. Outdoors Forever pre-app."],
      ["2028", "Lakeshore Loop phase 1 under construction. Levee route open. LCDBG FY28 application."]]
tl = [[Paragraph(f"<b>{a}</b>", BODY), Paragraph(b, BODY)] for a, b in tl]
tt = Table(tl, colWidths=[1.0 * inch, 6.3 * inch])
tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
story.append(tt)
story.append(Spacer(1, 4))
story.append(Paragraph("Sources: Census ACS 2023 5-year; Louisiana Legislative Auditor FY 2022 report (no recreation fund); "
                       "program pages for LA OCD, DOTD, State Parks, LDWF, USDA RD, DRA, USGS. Dates from the latest published "
                       "cycle; confirm with each agency. Prepared October 29, 2026.", SMALL))

doc.build(story)
print("wrote", OUT)
