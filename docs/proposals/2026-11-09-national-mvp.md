# National MVP proposal (T-99)

Status: **approved 9 Nov 2026** (D-21). The owner will work out the buyer conversations (Part 6, "Owner") later.

## Why

The owner wants the first product to be nationwide. Land Query has so far been built council by council: Kāpiti Coast,
then Porirua (T-24). Most of what made Kāpiti valuable comes from each council separately: zoning, flood models and
sewer depths. New Zealand has 67 councils, each with different layers and licence terms, and Wellington Water's licence
bars commercial use of three waters (D-16). A national product therefore has to stand on data that exists everywhere,
and add council data where it can be cleared.

Doing that the Kāpiti way would also cost too much. Precomputing every parcel at 1 m resolution, as for Kāpiti, would
cost around US$150–200 per nationwide rebuild on GitHub. That is against a US$20 monthly budget (D-14).

## Part 1. The product

**A site screen for any parcel in New Zealand.** A buyer, builder or developer enters an address or legal
description. They get the first-hour facts about the land, each with its source, date and licence, and what is unknown.

**Area search on a national index.** For example, "residential-size sections over 800 m², under 25% built on, mostly
flat, in these suburbs". Developers can scout anywhere, then check zoning themselves for the shortlist. Zoning joins
the index council by council as licences are confirmed.

Who pays, to be tested by the owner with buyers (Part 6):

| Buyer | Uses | Likely form |
| --- | --- | --- |
| Small developers and builders | Finding and screening infill sites | Subscription with area search |
| Home buyers and buyer's agents | Checking a section before an offer | One-off report |
| Proptech and AI-agent builders | Parcel facts by API (D-12) | Metered API, later |

## Part 2. Data: national sources only

All of these are LINZ data under CC BY 4.0, published on the dataset itself, so no council licence confirmation (T-35)
is needed for the MVP. Layer numbers are to be confirmed when built.

| Source | Gives | Coverage |
| --- | --- | --- |
| NZ Primary Parcels (layer 50823) | Parcel shape, area, legal description, intent | National, about 2.5 million parcels (to confirm) |
| NZ Property Titles (50804) | Title type and count; never owners (D-12, D-15) | National |
| NZ Non-Primary Parcels (50782) | Easements and covenants (existence only) | National |
| NZ Addresses | Address search, the address on each parcel | National |
| NZ Building Outlines | Building cover, open ground (as D-19: outline-based, with a LiDAR warning) | National, captured from aerial imagery |
| NZ Roads, coastline and rivers (Topo50) | Road frontage, distance to coast and rivers | National |
| LiDAR 1 m DEM and DSM (national mosaics, `new-zealand/dem_1m`, `dsm_1m`) | Ground height, slope, flow paths, sun, roof, open ground, structures | 424 map sheets, surveys 2008–2026: nearly all of the country (gaps to measure) |
| National 1 m DEM read at 10 m, and the 8 m contour DEM | Catchments, sea mask, the national index's terrain | National |

Not in the MVP:
- council zoning, plan overlays and hazard maps (they join per council when licences are confirmed);
- three waters (council or Wellington Water data);
- ground change (it needs two surveys).

GNS and regional council hazard layers (liquefaction, active faults) can be added where their licences allow; GWRC's
are already in use.

## Part 3. Architecture: two tiers

**Tier 1: the national index.** Every parcel, precomputed, rebuilt monthly or when LINZ changes much.
- **Columns from vector data:** area, shape, title type and count, easements, building cover from outlines, road
  frontage, distance to coast and rivers, address.
- **Columns from elevation:** from the national DEM at 10 m: ground height (mean, min, max), slope, low-lying land
  near the coast, and catchment.
- **Cost:** cheap. The Porirua flow grid (1,440 km² at 10 m) took 48 seconds, and New Zealand is about 190 times that
  area. Parcels and outlines come from LINZ's bulk exports, not page-by-page queries.
- **What it serves:** area searches.

**Tier 2: the parcel report, on demand.** The full 1 m analysis for one parcel, computed when someone asks, then
cached.
- **Columns:** everything the Kāpiti pipeline computes from LiDAR and national data: slope detail, overland flow, open
  ground, winter sun, roof pitch and solar, earthworks for a building platform, horizon, and buildings missing from the
  outlines.
- **Speed:** a block of 27,000 parcels took about 6 minutes of runner time per 1,000 parcels. A single parcel with its
  surrounding window should take one to two minutes, for a few cents.
- **What it serves:** the report a customer reads.

The existing code carries over: per-council settings become per-region settings for the LiDAR, and the compiler,
checks, service catalogue, finishing step and review practice stay. Council layers become optional add-ons to a parcel
row, marked as such.

## Part 4. Cost (estimates to check in the pilot)

| Item | How often | Estimate |
| --- | --- | --- |
| National index build | Monthly | A few US$ per run on GitHub Actions (to measure in the pilot) |
| Parcel report | Per request | A few cents (1–2 runner minutes), then cached |
| Storage of the national index (several hundred MB) | Ongoing | Free in GitHub release files up to 2 GB each; a git branch is unsuitable |
| Serving reports to customers | Ongoing | Needs somewhere to run on request. GitHub Actions can do it for a pilot (1–2 minutes' wait); a product needs a small server, which project rule 1 does not yet allow |

## Part 5. Decisions this needs

1. **D-12 (scope).** From "starts with Kāpiti Coast and grows one council at a time" to "national on LINZ data, with
   council layers added where licences are confirmed". Everything else in D-12 stays: provenance on every value, facts
   about land never people, nothing invented, public data only.
2. **D-14 and project rule 1 (costs).**
   - The national index's monthly build (a few US$) fits the current budget.
   - Serving reports to paying customers needs a small hosted server, about US$5–20 a month depending on the host. The
     owner decides when that starts, once there is someone to serve.
3. **The council-by-council work.** Kāpiti and Porirua stay as the richest areas and as the template for adding council
   layers. T-38 (rest of Greater Wellington) is paused in favour of the national tiers.

## Part 6. Plan

| Task | What | Cost |
| --- | --- | --- |
| T-100 | Pilot the national index on one region (all of Greater Wellington, about 200,000 parcels, LINZ data only): measure run time, cost and output size | About US$1 |
| T-101 | The parcel report on demand: one parcel anywhere in New Zealand from the national LiDAR mosaics, as a page; reuses the Kāpiti compiler | Cents per report |
| T-102 | Build out the national index to the whole country, monthly | A few US$ per run |
| T-103 | Fresh-eyes review of the index and the report before anyone outside sees them | Free (runs locally) |
| Owner | Show a sample report to five to ten builders, developers and buyer's agents; ask what they would pay, per report or per month | Owner's time |
| Owner | T-35 for the councils whose zoning matters most first (Auckland, Wellington, Christchurch, Hamilton, Tauranga), in parallel | Owner's time |

## Risks

- **LiDAR gaps and ages.** Surveys range from 2008 to 2026. An old survey misses recent earthworks and buildings, and
  a few areas have none. Each report says which survey it used and when.
- **No zoning.** Without zoning, the site screen answers "is this land workable?" but not "what may I build?". This is
  the main thing buyers may say is missing. It is the reason to start T-35 for the large councils early.
- **Building outlines.** LINZ's national outlines miss some buildings, as KCDC's did. The LiDAR warning (D-19) carries
  over.
- **LINZ API limits.** The key's quotas for bulk downloads need checking; LINZ's export service suits whole-country
  layers better than page-by-page queries.
