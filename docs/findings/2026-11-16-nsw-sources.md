# New South Wales: open sources for a parcel index (T-27)

Desk research, 16 Nov 2026. **Unverified:** this session could not open the official pages (data.nsw.gov.au,
data.gov.au, planningportal.nsw.gov.au, spatial.nsw.gov.au and the elevation portals are outside its network), so the
findings come from search-result extracts of those pages. Licences, sizes and coverage must be checked on the pages
themselves before any build.

## What maps onto the New Zealand index

| NZ column | NSW source | Licence (as found) | Bulk access | Catch |
| --- | --- | --- | --- | --- |
| Parcels (lot/plan ids, area) | DCS Spatial Services, "Lot", NSW Land Parcel and Property Theme (GDA2020); current within about 10 working days of lodgement | Spatial Services: CC BY 4.0 site-wide; catalogue records disagree (CC BY 3.0 AU, "not specified", one CC BY-ND link) | ArcGIS FeatureServer (`portal.spatial.nsw.gov.au/.../NSW_Land_Parcel_Property_Theme_multiCRS`); no confirmed free statewide file ("contact the Customer HUB") | the licence and a bulk file need confirming in writing |
| Title count | none open: the register is NSW LRS, a private concession; title searches are paid and broker terms forbid compiling a database | — | — | **not possible**; at most the cadastre's "ITS title status" field |
| Addresses | G-NAF (Geoscape, data.gov.au), quarterly | Open G-NAF EULA: CC BY 4.0 plus a ban on compiling addresses for mail without a second source | national download, PSV | the mail clause must be passed on to users |
| Buildings | Overture Maps buildings (OSM, Microsoft, Google, Esri), monthly GeoParquet | ODbL | bulk, monthly | share-alike for the footprints themselves; counts per parcel are a produced work |
| Road frontage | cadastre "Road" and "Road Corridor" polygons | as parcels | as parcels | same method as NZ |
| Coast, water | NSW Water Theme: Coastline, Hydro Area, Hydro Line | "not specified" now; CC BY 3.0 AU in 2018 sheets | File Geodatabase or services | licence to confirm |
| District | ABS ASGS LGA 2025 (or the NSW Administrative Boundaries Theme) | CC BY 4.0 | GeoPackage | none |
| Easements | cadastre "Easement" layer (polygons, carriageways included) | as parcels | FeatureServer layer 9 (100 records a query) | better than NZ: a layer of its own |
| Ground, slope, flow | NSW 1 m/2 m LiDAR via ELVIS (tile orders); NSW 5 m Elevation Data Service; Geoscience Australia 5 m LiDAR DEM (CC BY 4.0, zipped by UTM zone, populated and coastal areas) | CC BY 4.0 mostly | GA 5 m: bulk zips; 1 m: order by order, no cloud mirror found | 1 m coverage of the state unknown; a 5 m base, 1 m where it exists |
| **Zoning (new)** | DPHI "EPI – Land Zoning", statewide, weekly | CC BY 4.0 in metadata (CC BY 3.0 AU on the mirror) | REST or WMS online; full file by email request (data.broker@environment.nsw.gov.au) | statewide zoning, which NZ lacks |
| **Bush fire prone land (new)** | statewide, per council certification | CC BY variants | ZIP and REST | licence to confirm |
| Flood | "EPI – Flood"; councils own flood maps since 2021 | — | REST | patchy, optional |

## Assessment

Feasible and free, if Spatial Services confirms CC BY 4.0 for the cadastre and water layers. Everything in the NZ index
has an NSW source except the title count. Statewide zoning and bush fire prone land would be new columns that New
Zealand cannot offer.

Risks, in order: the cadastre's licence (CC BY-ND links and "not specified" records); no bulk cadastre file (paging a
service of millions of lots monthly is fragile); ODbL share-alike on buildings; the G-NAF mail clause; 1 m terrain
coverage and delivery.

## Next steps (T-27)

1. The owner, or someone they choose, asks Spatial Services (Customer Hub) to confirm the licence of the Lot, Road
   Corridor, Easement and Water layers and for a bulk file, and asks DPHI's data broker for the zoning file. Agents
   do not contact outside parties.
2. A session with the NSW hosts allowed checks every licence and size above on the source pages.
3. Then build in this order: parcels and districts; addresses; road frontage and easements; coast and water;
   buildings; zoning and bush fire; terrain (5 m first, 1 m where it exists).
