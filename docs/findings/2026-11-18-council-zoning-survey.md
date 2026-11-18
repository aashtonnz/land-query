# Council zoning layers with an open licence on the dataset (T-35, T-38)

18 Nov 2026. `pipeline/council_survey.py` searched ArcGIS Online's public catalogue for New Zealand layers on zoning,
flooding, coastal hazards, land hazards and heritage: 2,003 layers. On 519 of them the dataset itself carries an open
licence (CC BY or similar, commercial use allowed), which this project accepts without writing to the council
(SOURCES.md, "Licence basis"); 124 are non-commercial or no-derivatives, 36 state an open licence beside a clause that
restricts it, and 1,324 state none or something else. The survey runs weekly in `sources.yml` and writes
`council_layers.json` (every layer, its address and licence text).

## District plan zoning, by parcels covered

One base zoning layer per council, with parcel counts from the national build of 16 Nov (2,468,249 parcels).

| District | Parcels | Licence on the dataset | Layer |
| --- | --- | --- | --- |
| Auckland | 563,052 | open licence with a restricting clause | Unitary Plan Base Zone |
| Christchurch City | 174,661 | dataset licence | DP Zone (OpenData) |
| Wellington City | 68,887 | dataset licence | WCC District Plan Zones |
| Far North District | 52,964 | dataset licence | DECISIONS - Proposed District Plan - Zones (FNDC) |
| New Plymouth District | 43,363 | dataset licence | NPDC Strategy : District Plan Part Operative - Zone |
| Hastings District | 39,451 | dataset licence | Hastings DC Operative District Plan Zones |
| Palmerston North City | 38,087 | dataset licence, subject to council terms (to read) | PNCC District Plan Zones |
| Marlborough District | 36,209 | dataset licence | MEP - Marlborough Environment Plan Zoning |
| Waimakariri District | 35,075 | dataset licence | District Plan Zones - Search |
| Gisborne District | 31,689 | dataset licence | District Planning Zones |
| Western Bay of Plenty District | 30,636 | dataset licence | Western Bay of Plenty District Plan Zones |
| Waipa District | 29,995 | dataset licence | Waipa District Plan - Commercial Zone |
| Taupo District | 26,783 | dataset licence | Zones |
| Manawatu District | 23,982 | dataset licence | MDC District Plan Zones |
| Tararua District | 21,628 | dataset licence | TDC Planning Layer - Zones |
| Whakatane District | 20,082 | dataset licence | District Plan Zones |
| Upper Hutt City | 18,721 | dataset licence | District Plan Zones |
| South Waikato District | 13,708 | dataset licence | Plan Zones |

Of these, **12 are used** (`pipeline/zoning.py`): Christchurch, Far North, New Plymouth, Hastings, Marlborough, Gisborne,
Western Bay of Plenty, Waipā (its combined "Waipa District Plan - Zones" layer, not the commercial zone listed above),
Taupō, Manawatū, Tararua and South Waikato: **525,069 parcels, about 21% of New Zealand**; with Kāpiti Coast and Porirua,
already compiled, about 23%. Left out although openly licensed: Wellington City (the open layer is the 2018 plan; the
current 2024 zones carry no open licence), Whakatāne (its open layer is from 2016), Waimakariri (its open layer's
appeals version covers 23.5% of the district's parcels) and Upper Hutt (not reached yet).

Not yet usable:
- **Auckland** (563,052 parcels, 23%): the dataset states CC BY 4.0 but also that "you are not permitted to copy or
  republish any substantial amount of the information ... without the prior written consent of Auckland Council". A
  zone name per parcel is arguably not a substantial copy, but that is for Auckland to confirm in writing (T-35).
- **Palmerston North**: CC BY 4.0, "subject to PNCC Terms and Conditions", which are still to be read.
- Hamilton, Tauranga, Dunedin, Hutt City, Nelson, Napier, Rotorua, Whangārei and most other councils publish no zoning
  layer with a licence on ArcGIS Online that the search found; they may publish elsewhere (their own portals), which
  the survey does not cover yet.

## Hazards

Open-licence flood, coastal and land hazard layers come mainly from Environment Canterbury (regional), Christchurch,
Hawke's Bay Regional, Gisborne, Nelson (Tonkin and Taylor models), Taranaki Regional, Waimakariri, Taupō and Far North.
Waikato Regional Council's hazards portal is CC BY-ND (no derivatives) and Northland Regional Council's is non-commercial:
neither is usable without permission. Hazard layers differ far more between councils than zoning does (return periods,
climate scenarios, model or mapped), so each needs its own reading before use.

## Next

A national zoning column from the 12 layers used (T-38): each parcel's zone with the largest share, its share, and the
layer and licence it came from, compiled in the national build. The zone names differ by council, so the council's own
name is published, with a few broad classes (residential, rural, business, open space, other) for comparison across
councils.

## Review (18 Nov)

A fresh-eyes review of the zoning work found: the bulk download would have crashed on the zoning entry (fixed before
any build); parcels near a boundary took a neighbouring council's zone (1,478 parcels; now only the parcel's own
council's zones count); misclassified names ("Transport" as open space, villages as other, lifestyle zones split; the
classes reordered and widened); the map neither credited the councils nor told infrastructure from "no value" in dark
mode (both fixed); slivers set zones (a zone must now cover half the parcel); duplicate polygons were counted twice
(each zone's pieces are merged); Waipā's reserves were left out (now included); Hastings' open space codes and
Western Bay of Plenty's underscores were unreadable (named and tidied); Marlborough's plan label lacked its status;
South Waikato's service adds that its information may not be used for legal disputes (recorded with its licence).
All 12 licences were confirmed as CC BY 4.0 on the council's dataset, every download matched the service's count, and
238 of 240 parcels spot-checked against the live services agreed (the other two: a parcel across a boundary at 50.5%,
and a 0.1% sliver).
