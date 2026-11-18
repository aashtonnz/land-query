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

The 16 with a plain open licence cover 667,834 parcels, **27% of New Zealand**; with Kāpiti Coast and Porirua, already
compiled, about 29%.

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

A national zoning column from the 16 open layers (T-38): each parcel's zone with the largest share, its share, and the
layer and licence it came from, compiled in the national build. The zone names differ by council, so the council's own
name is published, with a few broad classes (residential, rural, business, open space, other) for comparison across
councils.
