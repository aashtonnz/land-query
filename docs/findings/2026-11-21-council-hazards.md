# Council flood and coastal hazard areas (T-128), 21 November 2026

## What was added
`pipeline/hazards.py` downloads the flood and coastal hazard areas that councils publish under an open licence (CC BY 4.0). Each parcel gets, for each kind:
- `flood_area_pct` / `coastal_area_pct`: the share of the parcel inside its own council's area. It is 0 where the council maps the area and the parcel is outside it, and empty where the council publishes no such map openly. That is most of the country for now.
- `flood_area` / `coastal_area`: what the area is, in the council's own terms. Where the council includes climate change or sea-level rise, the label says so.

The shares show where a council has drawn its line. They are not a measure of risk, and they can't be compared between councils: return periods, scenarios and methods all differ.

## Sources (clean download, 21 November)

| Council | Kind | Areas | Source layer |
| --- | --- | ---: | --- |
| Christchurch City | flood | 2,078 | District Plan Flood Management Area (removed areas left out) |
| Taupō District | flood | 27,159 | District Plan Flood Hazard Area, 1% AEP |
| Gisborne District | flood | 347 | Tairāwhiti Plan flood hazard areas F1–F9 |
| Waipā District | flood | 13 | District Plan Special Feature Area, Flood |
| Far North District | flood | 26 | Proposed Plan decisions version, river flood 1% AEP including climate change |
| Gisborne District | coastal | 51 | Tairāwhiti Plan Coastal Hazard Overlay CH1–CH4 |
| Far North District | coastal | 237 | Proposed Plan decisions version, coastal flood zones 1–3 |
| Nelson City | coastal | 9 | Present-day 1% AEP coastal flooding, areas connected to the sea |

All eight sources downloaded with no failures.

Not used, and why:
- Christchurch's coastal layers hold future scenarios only.
- Hawke's Bay's coastal erosion is given by probability and year.
- Fault and liquefaction studies are a different kind of data and will need columns of their own.
- Auckland and Wellington City are waiting on the councils to confirm their licences (T-35).

## Parcels covered (339,922 parcels in the six districts, index of November)

| Council | Kind | Parcels | Any part inside | Half or more inside |
| --- | --- | ---: | ---: | ---: |
| Christchurch City | flood | 174,661 | 32.3% | 24.5% |
| Far North District | flood | 52,964 | 23.3% | 8.6% |
| Gisborne District | flood | 31,689 | 25.8% | 18.4% |
| Taupō District | flood | 26,783 | 4.4% | 1.6% |
| Waipā District | flood | 29,995 | 2.7% | 1.3% |
| Far North District | coastal | 52,964 | 14.5% | 4.8% |
| Gisborne District | coastal | 31,689 | 1.4% | 0.6% |
| Nelson City | coastal | 23,830 | 3.3% | 1.4% |

Two figures changed during the checks:
- **Nelson coastal, from 82.1% to 3.3%.** The first layer used held the model's cells, meaning the whole area studied, rather than the flooded area.
- **Far North flood, from 39.9% to 23.3% (any part) and from 14.8% to 8.6% (half or more).** The notified layer needed a shape repair, and the repair grew one zone by 5%. That gave parcels outside the zone 100%. The decisions version needs no repair.

Christchurch's share is high because its Flood Management Area deliberately takes in the low-lying eastern suburbs, allowing for sea-level rise.

## Fresh-eyes review (21 November) and what changed
- Far North's flood areas now come from the decisions version. A repair is kept only if its area is within 2% of the area the council states for that shape. Otherwise the source fails rather than publishing a wrong area.
- Far North's coastal erosion zones are lines, not areas, so they had been dropped without notice. They are now left out on purpose and the label says so. A source whose layer is not an area layer, or that yields no areas, now fails instead.
- Labels state any climate-change and sea-level allowances. The map and page describe the shares as where a council drew its line, not as risk.
- Taupō's requested derivative statement is in its licence note. Nelson's date is corrected.
- Tests cover: a line layer failing, the repair check, 0 outside versus empty where there is no map, and a parcel counting only its own council's areas.

## Next
These columns go into the next national build, which needs GitHub Actions to be unlocked (T-127).
