"""Class shares of polygon overlays on a parcel (zones, plan overlays, hazard layers)."""
from shapely.ops import unary_union


def class_label(layer, props, council=None):
    """The class a polygon feature belongs to, from the layer's own class field (T-39).

    zones: ePlan_Zone, the operative District Plan zone (PDP_ZONE holds older names for some features).
    Layers without a class field get a fixed name for the overlay itself, never the column name."""
    f = lambda k: (props.get(k) or "").strip() if isinstance(props.get(k), str) else props.get(k)
    from councils import COUNCIL
    council = council or COUNCIL
    if layer in council.CLASS_FIELDS:   # a council's own class fields, then a fixed name (T-87)
        fields, default, *how = council.CLASS_FIELDS[layer]
        if how == ["join"]: return "; ".join(str(f(k)) for k in fields if f(k)) or default   # every field, e.g. a control and its limit
        if how:   # format strings, the first whose fields are all set
            for fmt in how[0]:
                names = [n for _, n, _, _ in __import__("string").Formatter().parse(fmt) if n]
                if all(f(n) for n in names): return fmt.format(**{n: f(n) for n in names})
            return default
        return next((f(k) for k in fields if f(k)), None) or default
    if layer == "zones": return f("ePlan_Zone") or f("NPS_Zone") or "Zone not recorded"
    if layer == "ovl_fault_avoidance":
        return ": ".join(x for x in (f("FAULT_NAME"), f("DESCRIPTIO")) if x) or "Fault avoidance area"
    if layer == "ovl_flood_hazard" or layer.startswith("flood_"): return f("ZONE") or "Flood hazard"
    if layer == "tsunami_zones": return f("Evac_Zone") or "Tsunami evacuation zone"
    if layer == "gw_liquefaction": return f("Liquefaction") or "Liquefaction class not recorded"
    if layer == "gw_eq_slope_failure": return f("SEVERITY") or "Severity not recorded"
    if layer == "ovl_noise_corridor": return f("Id") or f("Name") or "Noise Corridor (no name in source)"
    if layer == "ovl_ecological_sites": return f("Name") or "Ecological site (no name in source)"
    if layer == "earthworks": return f("Label_Text") or "Earthworks"
    return dict(ovl_coastal_env="Coastal Environment", wind_stainless="Stainless Zone",
                wind_very_high="Very High Wind Zone").get(layer) or layer


def class_shares(layer, parcel, features):
    """Percent of the parcel covered by each class: overlapping features of a class are unioned, not summed."""
    parts = {}
    for pg, pp in features:
        a = pg.intersection(parcel)
        if a.area > 0.5: parts.setdefault(class_label(layer, pp), []).append(a)
    return {k: round(100 * unary_union(v).area / parcel.area, 1) for k, v in parts.items()}


def points_on(parcel, features, id_field):
    """Point features inside or on the boundary of the parcel, as [{id, significance}] (T-44: not within 1 m)."""
    # a multipoint item (Porirua's heritage items) is on every parcel that holds one of its points (fifteenth review)
    return [dict(id=p.get(id_field), significance=p.get("SIGNIFICANCE") or None) for g, p in features
            if any(parcel.covers(q) for q in getattr(g, "geoms", [g]))]


def nearest_item(items, candidates, g, prefer=None, maxd=None, tie_m=0.05):
    """(distance, properties, tied ids) of the nearest item to g within maxd, or (None, None, []).

    Items within tie_m of the nearest distance count as equally near (two manholes inside one parcel, or a parcel lying
    on two pipe segments that meet). Among them, prefer(properties) picks the one with the smallest key (callers state
    the rule, for example the deepest invert); the lowest asset id settles any remaining tie, so the result never
    depends on the order the source sent them. All tied ids are returned so the choice can be reported (T-49)."""
    ds = [(items[i][0].distance(g), items[i][1]) for i in candidates]
    if maxd is not None: ds = [t for t in ds if t[0] <= maxd]
    if not ds: return None, None, []
    dmin = min(d for d, _ in ds)
    tied = [(d, p) for d, p in ds if d <= dmin + tie_m]
    key = lambda t: ((prefer(t[1]) if prefer else 0), str(t[1].get("asset_id") or ""))
    d, p = min(tied, key=key)
    return d, p, sorted(str(q.get("asset_id")) for _, q in tied)


def deepest_invert(p):
    return p.get("invert_level_nzvd2016") if p.get("invert_level_nzvd2016") is not None else float("inf")


def worst_grade(p):
    g = p.get("condition_grade")
    return -g if g in (1, 2, 3, 4, 5) else 0   # grade 0 has no published definition: treated as not graded


def split_clipped(diffs, linz_geoms, edge, tol_m=1.0):
    """Split parcel area differences (compiled minus LINZ, m²) into parcels clipped at the district boundary (smaller
    than LINZ by over 1 m², where the LINZ parcel itself crosses the boundary line) and all others, which are reported:
    a mirror polygon cut short anywhere else is an error in the mirror (T-49)."""
    at_edge = lambda i: edge is not None and not edge.is_empty and i in linz_geoms and linz_geoms[i].buffer(tol_m).intersects(edge)
    clipped = {i: d for i, d in diffs.items() if d < -1 and at_edge(i)}
    return clipped, {i: d for i, d in diffs.items() if i not in clipped}


def largest_diameter(p):
    d = p.get("nominal_diameter")
    return -d if isinstance(d, (int, float)) else 0


def as_int(v):
    """A whole number stored as a float (1964.0) as an integer; anything else unchanged."""
    return int(v) if isinstance(v, float) and v.is_integer() else v


def district_polygon(lines, sea_x=1735000.0):
    """The district's area from KCDC's boundary line, which is open along the coast: its two loose ends are joined by a
    loop out to sea (west of Kapiti Island), and the closed ring becomes a polygon (T-60). Returns an empty polygon if
    the line does not have exactly two loose ends."""
    from collections import Counter
    from shapely.geometry import LineString, Polygon
    from shapely.ops import linemerge, polygonize, unary_union
    merged = linemerge(unary_union(lines))
    parts = list(merged.geoms) if merged.geom_type == "MultiLineString" else [merged]
    ends = Counter()
    for l in parts:
        ends[l.coords[0]] += 1; ends[l.coords[-1]] += 1
    loose = [pt for pt, n in ends.items() if n == 1]
    if len(loose) != 2: return Polygon()
    (x0, y0), (x1, y1) = loose
    sea = LineString([(x0, y0), (sea_x, y0), (sea_x, y1), (x1, y1)])
    polys = list(polygonize(unary_union(parts + [sea])))
    return unary_union(polys) if polys else Polygon()


# A parcel belongs to the district if its representative point lies inside, or if at least 1,000 m² of it does
# (T-65, T-70). Whole parcels are published (owner, T-69); `district_share_pct` says how much lies inside. An area
# floor alone: a share floor dropped 1.5-2 ha of district land on large parcels (sixth review).
MIN_INSIDE_M2 = 1000.0
SEA_SLIVER_M = 30.0


def district_outline(lines, wards, stats, sea_x=1735000.0):
    """The district from three boundaries: KCDC's boundary line closed at sea, KCDC's whole-district ward polygon, and
    Stats NZ's district polygon. Land counts where at least two of the three agree (T-70). The ward and Stats NZ both
    follow meshblocks and agree to within a metre almost everywhere, so in practice this is their boundary, with the
    line deciding only where they differ (seventh review). The sea and islands come from the line's sea loop, where neither polygon reaches: thin strips there (up to
    2 * SEA_SLIVER_M wide) are where the line disagrees with both polygons on land, and are left out. Empty if any of
    the three is missing."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    d = district_polygon(lines, sea_x)
    if d.is_empty or not wards or not stats: return Polygon()
    w, g = unary_union(list(wards)), unary_union(list(stats))
    land = unary_union([d.intersection(w), d.intersection(g), w.intersection(g)])
    sea = d.difference(w).difference(g).buffer(-SEA_SLIVER_M).buffer(SEA_SLIVER_M)
    return unary_union([land, sea])


def district_share(g, outline):
    """Percent of g inside outline if g belongs to the district, else None."""
    if g.is_empty or not g.area: return None
    inside = g.intersection(outline).area
    if outline.contains(g.representative_point()) or inside >= MIN_INSIDE_M2:
        return round(100 * inside / g.area, 1)
    return None


def split_by_district(features, outline):
    """(members with district_share_pct set, [{id, appellation}] of the others)."""
    from shapely.geometry import shape
    inside, outside = [], []
    for f in features:
        s = district_share(shape(f["geometry"]), outline)
        if s is None: outside.append(dict(id=f["properties"].get("id"), appellation=f["properties"].get("appellation")))
        else: f["properties"]["district_share_pct"] = s; inside.append(f)
    return inside, outside


def linz_not_in_mirror(by_id, mirror_ids, block, outline):
    """LINZ parcels assigned to this block (representative point inside it) and belonging to the district, whose id
    no mirror feature in the block query has (T-59, T-62)."""
    from shapely.geometry import shape
    out = []
    for i, f in by_id.items():
        if i in mirror_ids: continue
        g = shape(f["geometry"]); p = g.representative_point()
        if (block.contains(p) or block.touches(p)) and district_share(g, outline) is not None:
            out.append(dict(id=i, appellation=f["properties"].get("appellation"), intent=f["properties"].get("parcel_intent")))
    return out


def parcels_error(key_set, kept, from_linz, err):
    """The parcels source's error: LINZ's own, or LINZ returning none of the block's parcels although the key is set."""
    if err: return err
    if key_set and kept and not from_linz: return "LINZ returned none of the block's parcels"
    return None


# Columns that need the 2021 building outlines over the whole parcel: building area itself, and everything measured
# on "open ground" (the parcel minus buildings). Where the outlines don't reach, a house would count as open ground
# and its roof as no building, so these are empty, not 0 (seventh review, T-73; D-12). The viewpoint columns (horizon,
# sky view, wind) are kept: the viewpoint must also be clear of anything standing in the 2024-25 DSM, roofs included.
BUILDING_COLUMNS = ("building_2021_m2", "open_ground_m2", "open_ground_slope_lt5_m2", "canopy_gt3m_open_pct",
                    "open_ground_clear_pct", "winter_sun_hours_open_mean", "winter_sun_open_ge3h_pct",
                    "roof_pitch_p50_deg", "roof_flat_m2", "roof_north_m2", "roof_solar_rel_pct",
                    "level_open_cut_m3", "level_open_fill_m3", "platform_15m_earthworks_min_m3")
BUILDING_MIN_COVER = 0.99


def building_cover(capture, outline):
    """Where KCDC's 2021 building outlines were captured: the 2017 urban aerial photos' footprint (NZTM), within the
    district (the layer holds no outlines outside it). None if either is unknown: then no parcel counts as covered
    (T-73, T-76; the layer's bounding box, used at first, took in Reikorangi and Waiorua Bay, which have houses)."""
    if capture is None or capture.is_empty or outline is None or outline.is_empty: return None
    return capture.intersection(outline)


def capture_area_nztm(geojson):
    """A LINZ capture-area GeoJSON (a Feature or FeatureCollection in WGS84) as one NZTM geometry."""
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from pyproj import Transformer
    feats = geojson["features"] if geojson.get("type") == "FeatureCollection" else [geojson]
    t = Transformer.from_crs(4326, 2193, always_xy=True).transform
    return transform(t, unary_union([shape(f["geometry"]) for f in feats]))


UNMAPPED_MIN_M2 = 40  # from this, unmapped_structure_m2 warns that a building may stand where KCDC has no outline (D-19)


def withhold_uncovered_buildings(row, g, cover):
    """Sets buildings_coverage_pct and empties the building columns unless the outlines cover the parcel and the
    block's fetch window covers it (`coverage_pct`, T-79). The building columns describe KCDC's 2021 outlines, which
    miss some houses; `unmapped_structure_m2` warns of those, without emptying anything (D-19, T-81)."""
    share = g.intersection(cover).area / g.area if cover is not None and g.area else 0.0
    row["buildings_coverage_pct"] = round(100 * share, 1)
    return finish_row(row)


LIDAR_FLOW_COLUMNS = ("upslope_area_max_m2", "upslope_area_truncated", "flow_path_m", "unmapped_structure_m2")


def finish_row(row, council=None):
    """Rules that need only a parcel's own published values, applied by the compiler to every row and by finish.py to
    published results, so a change to them republishes in minutes without a rebuild (T-82). Each is idempotent.

    - Building and open-ground columns empty unless the outlines and the fetch window cover 99% of the parcel (T-73,
      T-79); the published, rounded figure decides (T-77).
    - Flow and structure columns empty under 99% LiDAR coverage: a part's values are not the parcel's (T-81).
    - KCDC's condition grade 0 means "not graded": empty (T-79). A count of 0 recommended building levels: empty (T-76).
    """
    def below(k):
        v = row.get(k)
        return v is None or v != v or v < 100 * BUILDING_MIN_COVER   # missing or NaN counts as not covered
    if below("buildings_coverage_pct") or below("coverage_pct"):
        from councils import COUNCIL
        council = council or COUNCIL
        for k in BUILDING_COLUMNS:
            row[k] = None
            r = council.RENAME_COLUMNS.get(k)
            if r and r in row: row[r] = None   # published results carry the council's name for it (T-87)
    if below("lidar_coverage_pct"):
        for k in LIDAR_FLOW_COLUMNS:
            if k in row: row[k] = None
    if row.get("ww_pipe_condition_grade") == 0: row["ww_pipe_condition_grade"] = None
    if row.get("rbl_in_parcel_n") == 0: row["rbl_in_parcel_n"] = None
    return row


def district_outline_polygons(a, b, c):
    """A district from three boundary polygons (lists of geometries): land where at least two agree (T-87; Porirua,
    which has no boundary line closed at sea). Empty if any is missing."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    if not (a and b and c): return Polygon()
    a, b, c = unary_union(a), unary_union(b), unary_union(c)
    return unary_union([a.intersection(b), a.intersection(c), b.intersection(c)])


# Parcel intents not in LINZ's primary parcel layer (roads and water have layers of their own); KCDC's copy omits them,
# PCC's includes them, so they are left out for every council (T-88)
NOT_PRIMARY_INTENTS = frozenset({"Road", "Hydro"})


def council_columns(columns, council):
    """The council's published columns, in order: those it has no source for left out (D-12), others renamed (T-87)."""
    import re
    return [council.RENAME_COLUMNS.get(c, c) for c in columns
            if not any(re.fullmatch(p, c) for p in council.ABSENT_COLUMNS)]


def buildings_cover_for(council, capture, outline):
    """Where the council's building outlines were captured: its capture area within the outline, or, for a council
    whose footprints span it (BUILDINGS_CAPTURE None), the outline itself (T-76, T-87)."""
    return building_cover(outline, outline) if council.BUILDINGS_CAPTURE is None else building_cover(capture, outline)


def repaired(g):
    """A valid geometry for an invalid source shape, keeping its true extent (fourteenth review): buffer(0), used
    before, fills in the holes and gaps of some multi-ring polygons (PCC's gas pipeline corridor read as 7.05 km² for
    0.667 km²). make_valid keeps them; for a polygon layer only its polygon parts are kept."""
    from shapely.validation import make_valid
    from shapely.geometry import MultiPolygon, GeometryCollection
    if g.is_valid: return g
    v = make_valid(g)
    if g.geom_type in ("Polygon", "MultiPolygon") and isinstance(v, GeometryCollection) and not isinstance(v, MultiPolygon):
        parts = [p for p in v.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        v = parts[0] if len(parts) == 1 else MultiPolygon([q for p in parts for q in getattr(p, "geoms", [p])])
    return v
