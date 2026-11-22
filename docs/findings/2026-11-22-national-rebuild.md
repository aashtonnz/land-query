# National rebuild with zoning and hazards, 21–22 November 2026

**Run:** [National index run 16](https://github.com/aashtonnz/land-query/actions/runs/44954071348), started by an agent on 21 Nov. It took 1 h 41 min, with 40 shares, and GitHub billed 0 minutes. It has not been published. Its index stays available as an artifact until 21 Dec 2026.

## Result
- **Parcels:** 2,469,407. That is 1,158 more than the 16 Nov build (nz5), +0.05%, which is a few days of LINZ changes.
- **Duplicates and unknowns:** 0 duplicate ids; 3,487 parcels with water unknown; 100 with district unknown.
- **New columns:** zone, zone_share_pct, zone_class, zone_plan, flood_area_pct, flood_area, coastal_area_pct and coastal_area. None were lost; there are 54 columns in all.
- **No titles or owners:** the index holds title counts only, and the provenance names no titles.

## Comparison with the 16 Nov build (`national_compare.py`)
- **Parcels:** ok.
- **Columns:** ok.
- **Unknowns and values:** ok, on 2,468,008 parcels that appear in both builds.
- **Districts:** failed, as expected. Parcels outside any district now have one spelling ("Area outside Territorial Authority"), down from two. Under the shore rule, 281 of the 458 shoreline parcels now take the district beside them, leaving 177. Both were intended changes from review 27, so the failure isn't a data problem. Monthly builds from now on compare with this one.

## New columns on real data
**Zoning:** 542,174 parcels zoned in the 13 districts with open zoning maps, between 98.8% (South Waikato) and 100% (Hastings, Marlborough, Upper Hutt) of each district's parcels.

Parcels by zone class:

| Zone class | Parcels |
| --- | ---: |
| Residential | 333,901 |
| Rural | 153,804 |
| Business | 17,045 |
| Open space | 12,826 |
| Industrial | 11,870 |
| Special purpose | 7,930 |
| Other | 2,662 |
| Infrastructure | 2,136 |

**Hazards:** these match the check on 21 Nov ([findings](2026-11-21-council-hazards.md)) to within the few days of new parcels.

| Council | Kind | Any part inside | Half or more inside |
| --- | --- | ---: | ---: |
| Christchurch City | flood | 32.3% | 24.5% |
| Far North District | flood | 23.3% | 8.6% |
| Gisborne District | flood | 25.8% | 18.4% |
| Taupō District | flood | 4.4% | 1.6% |
| Waipā District | flood | 2.7% | 1.3% |
| Far North District | coastal | 14.5% | 4.8% |
| Gisborne District | coastal | 1.4% | 0.6% |
| Nelson City | coastal | 3.3% | 1.4% |

## Ready for the owner
This can be the first published index (D-27). To publish it, run the "National index" workflow with `publish_run` = `44954071348`. After that, the map is rebuilt from it once R2 is turned back on (T-129).
