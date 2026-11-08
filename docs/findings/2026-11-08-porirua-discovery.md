# Porirua discovery for the second council (T-24, 8 Nov 2026)

This is desk research only; nothing has been compiled. It looks at what Porirua City Council publishes, where, and
under what terms, to judge the cost of adding a council.

## Where the data is

| What | Where | Licence stated |
| --- | --- | --- |
| District plan layers: Proposed District Plan (PDP) and Variation 1, including zones, flood hazard (overland flow, ponding, stream corridor), coastal erosion and inundation (current and with 1 m sea-level rise), tsunami (100, 500 and 1,000 year), fault rupture, heritage, notable trees, significant natural areas, noise and more | ArcGIS Online, `services1.arcgis.com` (organisation `kIwRm3UCyRHYbM8a`), listed on the council's ArcGIS Hub `data-pcc.opendata.arcgis.com` | None on the dataset |
| Property and environment layers: building footprints, suburbs, wind and corrosion zones, reserves | The council's own server, `maps.poriruacity.govt.nz` | CC BY 4.0 on 5 datasets (reserves, wind zones, sports grounds, public toilets, corrosion zone); CC BY 3.0 on 3 older ones |
| Three waters: pipes, manholes and pump stations, with inverts, cover levels, install dates and condition grades | Wellington Water, `gis.wellingtonwater.co.nz` (`Councils/PCC_3_Waters_Underground_Services`) | **Non-commercial**, see below |
| Parcels, titles, easements | LINZ, as for Kāpiti | CC BY 4.0 |
| LiDAR and aerials | LINZ elevation and imagery buckets (for example `porirua_2023`, `porirua_2025_0.075m`) | CC BY 4.0 |

- **Portal licence.** The Hub portal lists 59 datasets; 8 state a licence and 51 state none. The portal's footer says
  its work is licensed under CC BY 4.0 and links to a separate "Terms and Conditions for use of GIS" page on the
  council's website, which could not be read from here.
- **Like Kāpiti.** Like KCDC's, this is a portal-wide statement that needs written confirmation before commercial use
  (as T-35).

## Wellington Water's licence

The licence text on Wellington Water's Porirua three-waters service says:

> "This Data is not to be used for commercial purposes including, but not limited to, reselling. You must acknowledge
> WWL as the source of the Data in any publication or other public disclosure where you use or rely on the Data."

- **Not just Porirua.** The same server publishes the three-waters networks of Wellington City, Hutt City, Upper Hutt
  and South Wairarapa, and Greater Wellington's bulk water, which is the whole Phase 2 area (T-38).
- **Under D-12.** The data may be collected only if its terms allow automated use, which the text does not address.
  And it could not be served to outside users in a paid product.
- **Effect.** Three-waters values drive Q1 (gravity-serviceable infill) and Q3 (old poor sewers), the queries that
  set this product apart for Kāpiti, where KCDC publishes its own networks under CC BY 4.0.

## What a council adapter costs (estimate)

- **Layer map.** A per-council layer list and class-field map, replacing `layers.py` and the label rules in
  `overlays.py` with per-council configuration (about half a day).
- **Columns.** Porirua's overlays differ (coastal erosion and inundation, three tsunami return periods, a second plan
  version). Columns would be per council, with `SOURCES.md` rows and the service catalogue to match.
- **District membership.** Kāpiti uses KCDC's parcel mirror; Porirua needs another source (for example LINZ parcels
  within the territorial authority boundary).
- **Three waters.** A Wellington Water schema mapping (field names differ: `Invert_Level_m`, `Condition_Grade`,
  `Operational_Status`, `Owner`), and a datum check (Wellington Water levels may be Wellington 1953, not NZVD2016).
- **LiDAR.** The `porirua_2023` survey; ground-change measures need a second epoch.
- **GitHub cost.** Porirua is about two thirds the size of Kāpiti, so a full compile would cost about US$1–1.50.
