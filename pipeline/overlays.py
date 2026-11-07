"""Class shares of polygon overlays on a parcel (zones, plan overlays, hazard layers)."""
from shapely.ops import unary_union


def class_label(layer, props):
    """The class a polygon feature belongs to, from the layer's own class field (T-39).

    zones: ePlan_Zone, the operative District Plan zone (PDP_ZONE holds older names for some features).
    Layers without a class field get a fixed name for the overlay itself, never the column name."""
    f = lambda k: (props.get(k) or "").strip() if isinstance(props.get(k), str) else props.get(k)
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
    return [dict(id=p.get(id_field), significance=p.get("SIGNIFICANCE") or None) for g, p in features if parcel.covers(g)]


def nearest_item(items, candidates, g, tie_m=0.05):
    """(distance, properties) of the nearest item to g, or (None, None).

    Items within tie_m of the nearest distance count as equally near (a parcel lying on two pipe segments that meet),
    and the lowest asset id among them is chosen, so the result never depends on the order the source sent them."""
    ds = [(items[i][0].distance(g), items[i][1]) for i in candidates]
    if not ds: return None, None
    dmin = min(d for d, _ in ds)
    return min(((d, p) for d, p in ds if d <= dmin + tie_m), key=lambda t: str(t[1].get("asset_id") or ""))
