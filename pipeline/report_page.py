"""A parcel report (parcel_report.py's report.json) as one static HTML page (T-101).

Usage: report_page.py REPORT_JSON OUT_HTML. Every value is shown with what it means and where it comes from; values
the report does not have are shown as not known, never as 0 (D-12)."""
import html, json, sys
from shapely.geometry import shape

E = html.escape

# (column, label, unit, decimals, meaning). Meanings follow SOURCES.md, in plain words.
GROUPS = [
    ("The land", [
        ("area_m2", "Area", "m²", 0, "Measured from LINZ's parcel shape."),
        ("survey_area_m2", "Surveyed area", "m²", 0, "The area on the survey plan."),
        ("parcel_intent", "Parcel type", "", None, "LINZ's parcel intent (DCDB is an older survey record)."),
        ("title_count", "Titles", "", 0, "Records of title on the parcel."),
        ("title_types", "Title types", "", None, "Freehold, cross lease, unit title and so on."),
        ("easements_n", "Easements", "", 0, "Easement parcels over this parcel (existence only)."),
        ("land_covenants_n", "Land covenants", "", 0, "Land covenant parcels over this parcel (existence only)."),
    ]),
    ("Ground", [
        ("ground_min_m", "Lowest ground", "m", 2, "Height above sea level (NZVD2016), from the 1 m LiDAR ground model."),
        ("ground_mean_m", "Average ground", "m", 2, "Height above sea level (NZVD2016)."),
        ("ground_max_m", "Highest ground", "m", 2, "Height above sea level (NZVD2016)."),
        ("slope_p50_deg", "Typical slope", "°", 1, "Half the parcel is flatter than this."),
        ("slope_p90_deg", "Steep parts", "°", 1, "Nine-tenths of the parcel is flatter than this."),
        ("lidar_coverage_pct", "LiDAR cover", "%", 1, "Share of the parcel the LiDAR covers. Below 100, ground values describe only the covered part."),
    ]),
    ("Buildings and open ground", [
        ("building_m2", "Under buildings", "m²", 0, "Area under LINZ's building outlines, drawn from aerial photos. 0 means no outline, not no building."),
        ("open_ground_m2", "Open ground", "m²", 0, "The rest of the parcel."),
        ("open_ground_slope_lt5_m2", "Open and flattish", "m²", 0, "Open ground sloping less than 5°."),
        ("open_ground_clear_pct", "Open ground clear", "%", 1, "Share of open ground with nothing over 0.5 m standing on it (no tree, hedge, fence, car or new building)."),
        ("canopy_gt3m_open_pct", "Tall cover", "%", 1, "Share of open ground under something more than 3 m tall, mostly trees."),
        ("unmapped_structure_m2", "Possible missing building", "m²", 0, "The largest flat-topped shape 2.5–15 m tall on open ground with no outline. Often a building newer than the photos; sometimes a dense tree."),
    ]),
    ("Sun, outlook and shelter", [
        ("winter_sun_hours_open_mean", "Midwinter sun", "h", 1, "Average hours of direct sun on the clear open ground on 21 June, from the LiDAR surface (no cloud)."),
        ("winter_sun_open_ge3h_pct", "Open ground with 3 h+", "%", 1, "Share of clear open ground with at least 3 hours of sun on 21 June."),
        ("horizon_north_deg", "Northern horizon", "°", 1, "Highest angle of buildings, trees or hills to the north, seen from the most open spot at eye height."),
        ("horizon_mean_deg", "Average horizon", "°", 1, "Mean horizon angle in 16 directions from the same spot."),
        ("sky_view_pct", "Sky view", "%", 1, "How much sky is visible from that spot (100 is open sky)."),
        ("wind_obstruction_pct", "Shelter around", "%", 1, "Share of the surrounding 200 m square with buildings or trees over 2.5 m. An input to wind, not a wind rating."),
        ("wind_rel_height_m", "Height above surroundings", "m", 1, "Ground here compared with the average ground within 500 m."),
    ]),
    ("Roof", [
        ("roof_pitch_p50_deg", "Typical roof pitch", "°", 1, "From the LiDAR surface inside the building outlines."),
        ("roof_north_m2", "North-facing roof", "m²", 0, "Roof facing north (315°–45°) at 5° or more."),
        ("roof_flat_m2", "Flat roof", "m²", 0, "Roof under 5°."),
        ("roof_solar_rel_pct", "Roof sun", "%", 1, "Direct sun on the roof over three days of the year, as a share of an unshaded flat surface here. For comparing roofs, not kWh."),
    ]),
    ("Earthworks", [
        ("level_open_cut_m3", "Cut to level", "m³", 0, "Earth to remove to bring all open ground to its middle level."),
        ("level_open_fill_m3", "Fill to level", "m³", 0, "Earth to add for the same."),
        ("platform_15m_earthworks_min_m3", "15 m pad", "m³", 0, "Least earthworks for a 15 m × 15 m level pad on open ground; empty where none fits."),
    ]),
    ("Water flowing over the land", [
        ("upslope_area_max_m2", "Land draining through", "m²", 0, "The largest area whose rain flows across this parcel, on the 1 m ground model."),
        ("upslope_area_truncated", "Could be larger", "", None, "Yes where that area reaches the edge of the model, so may be bigger (use the catchment below)."),
        ("flow_path_m", "Flow paths", "m", 0, "Length of paths across the parcel draining at least 2,000 m²."),
        ("catchment_area_max_m2", "Catchment through it", "m²", 0, "The same on the 10 m national model over 8 km around, for streams and rivers."),
        ("catchment_truncated", "Catchment could be larger", "", None, "Yes where the catchment reaches past that 8 km."),
    ]),
]
NOT_INCLUDED = ["District plan zoning and overlays", "Council flood and hazard maps", "Water, wastewater and stormwater pipes",
                "Valuations and sale prices", "Owners: never included"]


def fmt(v, unit, dec):
    if v is None: return '<span class="unknown">not known</span>'
    if isinstance(v, bool): return "Yes" if v else "No"
    if dec is None or isinstance(v, str): return E(str(v))
    s = f"{float(v):,.{dec}f}"
    return E(s) + (f'<span class="unit">{E(unit)}</span>' if unit else "")


def plan_svg(rep):
    """The parcel and nearby building outlines, north up, with a scale bar."""
    g = shape(rep["geometry"]); bs = [shape(b) for b in rep.get("buildings_nearby", [])]
    x0, y0, x1, y1 = g.buffer(max(4.0, 0.08 * max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]))).bounds
    W = 560; k = W / max(x1 - x0, y1 - y0); H = (y1 - y0) * k
    pt = lambda c: f"{(c[0] - x0) * k:.1f},{(y1 - c[1]) * k:.1f}"
    def path(geom):
        polys = getattr(geom, "geoms", [geom])
        return " ".join("M" + " L".join(pt(c) for c in ring.coords) + "Z" for p in polys
                        for ring in [p.exterior, *p.interiors])
    bar = next(b for b in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if b * k >= W / 6)
    out = [f'<svg viewBox="0 0 {W} {H + 34:.0f}" role="img" aria-label="Plan of the parcel and building outlines, north up">',
           f'<path d="{path(g)}" class="parcel"/>']
    out += [f'<path d="{path(b)}" class="bld"/>' for b in bs]
    out += [f'<g class="scale" transform="translate(8,{H + 14:.0f})"><path d="M0,6 V0 H{bar * k:.1f} V6"/>'
            f'<text x="{bar * k + 6:.1f}" y="6">{bar} m</text></g>',
            f'<g class="north" transform="translate({W - 18},{H + 4:.0f})"><path d="M0,22 L6,6 L12,22 Z"/><text x="6" y="2">N</text></g>',
            "</svg>"]
    return "".join(out)


def page(rep):
    v = rep["values"]
    title = rep.get("address") or v.get("appellation") or f"Parcel {rep['parcel_id']}"
    rows = []
    for name, cols in GROUPS:
        items = [c for c in cols if c[0] in v]
        if not items: continue
        rows.append(f'<section><h2>{E(name)}</h2><dl>')
        for col, label, unit, dec, meaning in items:
            rows.append(f'<div class="row"><dt>{E(label)}</dt><dd class="val">{fmt(v[col], unit, dec)}</dd>'
                        f'<dd class="what">{E(meaning)}</dd></div>')
        rows.append("</dl></section>")
    sv = lambda key: "".join(
        f'<li><b>{E(s["survey"] or "")}</b>, flown {E(s["flown_from"] or "?")} to {E(s["flown_to"] or "?")}'
        f' by {E(s["producer"] or "?")} for {E(s["licensor"] or "?")}; {s["share_pct"]:g}% of the parcel</li>'
        for s in rep["lidar_surveys"][key]) or "<li>No LiDAR survey covers this parcel.</li>"
    src = "".join(f'<li><code>{E(k)}</code> {E(str(s.get("url") or s.get("collection") or ""))}'
                  f'{" (" + E(str(s.get("fetched"))) + ")" if s.get("fetched") else ""}'
                  f'{"" if s.get("ok", True) else " <span class=unknown>not fetched</span>"}</li>'
                  for k, s in sorted((rep.get("sources") or {}).items()) if isinstance(s, dict))
    built = min((s.get("fetched") for s in (rep.get("sources") or {}).values() if isinstance(s, dict) and s.get("fetched")), default="")
    return f"""<title>{E(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* A surveyor's site sheet: plan beside the parcel's identity, then label / value / meaning rows by topic. */
:root {{
  --paper: #f5f6f1; --ink: #1c2420; --muted: #5b655f; --rule: #d6dbd2; --contour: #8a5a2b; --water: #2f6b8f; --bld: #c9cfc4;
  --display: "Archivo", "Arial Narrow", system-ui, sans-serif; --body: "Source Sans 3", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #121614; --ink: #e3e7e1; --muted: #9aa49d; --rule: #2b332e; --contour: #d29a5f; --water: #7fb4d6; --bld: #3a433d; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --paper: #121614; --ink: #e3e7e1; --muted: #9aa49d; --rule: #2b332e; --contour: #d29a5f; --water: #7fb4d6; --bld: #3a433d; color-scheme: dark }}
body {{ background: var(--paper); color: var(--ink); font: 16px/1.5 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 28px 48px }}
main {{ max-width: 980px; margin: 0 auto; display: grid; gap: 36px }}
header {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 28px; align-items: start }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--contour) }}
h1 {{ font: 800 clamp(28px, 5vw, 44px)/1.05 var(--display); font-stretch: 80%; margin: 10px 0 12px; text-wrap: balance }}
.id {{ font: 14px/1.6 var(--mono); color: var(--muted) }}
.id b {{ color: var(--ink); font-weight: 500 }}
.lede {{ max-width: 60ch; color: var(--muted); margin: 14px 0 0 }}
figure {{ margin: 0; border: 1px solid var(--rule); padding: 12px; background: color-mix(in srgb, var(--paper) 70%, var(--rule)) }}
svg {{ width: 100%; height: auto; display: block }}
.parcel {{ fill: color-mix(in srgb, var(--contour) 10%, transparent); stroke: var(--contour); stroke-width: 2 }}
.bld {{ fill: var(--bld); stroke: var(--muted); stroke-width: .8 }}
.scale path, .north path {{ fill: none; stroke: var(--ink); stroke-width: 1.4 }}
.north path {{ fill: var(--ink) }}
svg text {{ font: 11px var(--mono); fill: var(--ink); text-anchor: start }}
.north text {{ text-anchor: middle }}
figcaption {{ font: 12px/1.4 var(--mono); color: var(--muted); margin-top: 8px }}
section h2 {{ font: 700 15px/1 var(--display); letter-spacing: .06em; text-transform: uppercase; margin: 0 0 6px;
  padding-bottom: 8px; border-bottom: 2px solid var(--ink) }}
dl {{ margin: 0 }}
.row {{ display: grid; grid-template-columns: 13rem 9rem minmax(0, 1fr); gap: 4px 20px; padding: 10px 0; border-bottom: 1px solid var(--rule) }}
dt {{ font-weight: 600 }}
dd {{ margin: 0 }}
.val {{ font: 500 15px/1.5 var(--mono); font-variant-numeric: tabular-nums; text-align: right }}
.unit {{ color: var(--muted); margin-left: .3em }}
.what {{ color: var(--muted); font-size: 15px }}
.unknown {{ font-family: var(--body); font-style: italic; color: var(--muted) }}
.notes {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 28px }}
.notes ul {{ margin: 8px 0 0; padding-left: 1.1em }}
.notes li {{ margin: 4px 0 }}
.sub {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 14px 0 0 }}
.sources {{ font-size: 13px; color: var(--muted); overflow-wrap: anywhere }}
.sources code {{ font: 12px var(--mono); color: var(--ink) }}
@media (max-width: 720px) {{
  header, .notes {{ grid-template-columns: minmax(0, 1fr) }}
  .row {{ grid-template-columns: minmax(0, 1fr) auto }}
  .what {{ grid-column: 1 / -1 }}
}}
</style>
<main>
<header>
  <div>
    <div class="eyebrow">Site screen · LINZ data only</div>
    <h1>{E(title)}</h1>
    <div class="id"><b>{E(v.get("appellation") or "")}</b><br>Parcel {rep["parcel_id"]} · {E(v.get("title_types") or "no live title found")}<br>
      NZTM {v.get("rep_x", 0):,.0f} E · {v.get("rep_y", 0):,.0f} N</div>
    <p class="lede">What the national data says about this land: its shape, ground, buildings, sun, earthworks and water flow,
      each with what it means. Council zoning and hazard maps are not included.</p>
  </div>
  <figure>{plan_svg(rep)}<figcaption>Parcel (brown) and LINZ building outlines nearby, north up.</figcaption></figure>
</header>
{"".join(rows)}
<div class="notes">
  <section><h2>LiDAR surveys used</h2>
    <p class="sub">Ground model</p><ul>{sv("dem")}</ul>
    <p class="sub">Surface model (roofs, trees)</p><ul>{sv("dsm")}</ul></section>
  <section><h2>Not in this report</h2><ul>{"".join(f"<li>{E(x)}</li>" for x in NOT_INCLUDED)}</ul></section>
</div>
<section class="sources"><h2>Sources</h2>
  <p>All data from Toitū Te Whenua Land Information New Zealand (LINZ) under CC BY 4.0, with each LiDAR survey's producer
  and licensor named above. Fetched {E(built[:10])}. Values marked <span class="unknown">not known</span> could not be measured or fetched; they are never 0.</p>
  <ul>{src}</ul></section>
</main>
"""


if __name__ == "__main__":
    rep = json.load(open(sys.argv[1]))
    open(sys.argv[2], "w").write(page(rep))
    print("wrote", sys.argv[2])
