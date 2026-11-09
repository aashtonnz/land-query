# National index pilot: Greater Wellington (T-100)

9 November 2026. Tier 1 of the national MVP (D-21), built for one region to measure run time, cost and size before
the whole country (T-102).

## What was built

`pipeline/national_index.py` builds one row per parcel from LINZ data only, in 40 km tiles on the NZTM grid, so the
same code runs for a region or the country. Results: the `national-pilot` branch (`results/index.parquet`,
`provenance.json`, `run.json`). Columns are listed in [`SOURCES.md`](../../SOURCES.md) ("Columns: national index").

**Data comes from LINZ's own public ArcGIS services, not the LINZ Data Service.** LINZ publishes NZ Primary Parcels,
Property Titles, Building Outlines, Addresses and the Mean High Water Springs coastline as public feature services
(services.arcgis.com/xdsHIIxuCWByZiCB), with no key, updated within days of the LINZ Data Service (parcels last edited
in early November 2026). So the index can be built anywhere, including in this session for free (D-22).

## Results

| Measure | Value |
| --- | --- |
| Parcels | 217,326 (without road, water and seabed parcels), in 11 tiles |
| Run time | 47 minutes the first time (33 of them downloading, one page at a time); 17 minutes from saved downloads. With parallel downloads (now the default) a first run should take about 25 minutes |
| Elevation step | about 70 seconds per tile, whatever the parcel count: reading the 10 m ground model over the network, and flow |
| Index size | 34 MB (Parquet, with each parcel's shape simplified to 0.5 m) |
| Downloads | 186 MB of saved downloads; 1.2 million records |
| Cost | Nothing: run in this session, not on GitHub |

**Estimate for the whole country (T-102).** About 2.5 million parcels (2.8 million primary parcels less 335,000 road
and water parcels) in about 170 tiles with land. About 6 to 7 hours on one machine: elevation about 3.3 hours, vector
work and downloads the rest. On GitHub Actions that is about 400 runner minutes, about US$3 a run, split over several
jobs so each stays under an hour. The index would be about 400 MB: a GitHub release file (up to 2 GB each), not a
branch.

## Checks against the Kāpiti results

The Kāpiti district was compiled separately from LINZ's Data Service and 1 m LiDAR, so its 27,284 parcels are an
independent check.

| Column | Agreement |
| --- | --- |
| Parcel area | 27,227 parcels in both; all within 1 m² (median difference 0) |
| Title count | identical for all 27,227 |
| Title types | identical for 99% |
| Mean ground height (10 m here, 1 m in Kāpiti) | within 0.5 m for 96.7%; median difference 0.05 m |
| Building area (LINZ outlines here, KCDC's in Kāpiti; both from 2021 photos) | within 10 m² for 58%; LINZ's 20 m² or more smaller on 22% of parcels, larger on 1%. Median ratio 0.96 |

57 Kāpiti parcels are not in the index: their representative point lies outside Stats NZ's district polygons, which
the pilot uses for the region, while Kāpiti uses a two-of-three boundary rule (D-18).

LINZ's building outlines being smaller than KCDC's on a fifth of parcels is a real difference between the two sets of
outlines, not a computing error (both are areas inside the parcel, from the same 2021 photography). It needs a look
in the review (T-103): which outlines match the LiDAR better.

## Problems found and fixed

1. **LINZ's ArcGIS copies hold some records twice.** 1,368 parcels in Wellington City appear twice with the same
   values and shapes differing by under 0.1 m², and 433 buildings in the region appear twice with the same shape (one
   copy's use "Unknown", the other's empty). The first pilot run counted 1,300 parcels twice. The index now keeps one
   record per LINZ id and records how many it dropped (`repeated_records` in the provenance). A doubled building would
   otherwise have doubled the building area on its parcel.
2. **Downloads are now checked record by record.** While tracking the repeats down, it was clear the old check (count
   the records, compare with the server's total) cannot see a page that repeats another page. Downloads now ask for
   the list of record numbers first, fetch them in chunks, and fail unless each chunk holds exactly the records asked
   for, once each. A test with a fake server that repeats a page fails the old method and passes the new one. This
   download code is shared, so the council builds use it too; it gave the same counts on KCDC and PCC layers.
3. **Parallel downloads.** Downloading was 94% of the largest tile's time. Chunks are now fetched eight at a time:
   Wellington City's 113,000 parcel records took 51 seconds instead of about 5 minutes.

## Not in the pilot

- **Easements** (LINZ NZ Non-Primary Parcels): not among LINZ's public ArcGIS services; needs the LINZ key, so a
  GitHub run.
- **Rivers**: LINZ's public river layers are named lines only; left for later.
- **Coastline layer number and licence**: the Mean High Water Springs coastline's LINZ Data Service layer number was
  not confirmed, and its licence is assumed to be LINZ's usual CC BY 4.0. To confirm before anything is sold (T-104).
- **Region boundary**: Greater Wellington is taken as Stats NZ's eight district polygons via GWRC; the small part of
  Tararua District in the region is left out. The national build needs a national boundary source for district names
  (it falls back to the address's district).
