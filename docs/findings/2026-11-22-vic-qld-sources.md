# Victoria and Queensland: open sources for a parcel index

Desk research, 22 Nov 2026. Same template as the NSW note
([`2026-11-16-nsw-sources.md`](2026-11-16-nsw-sources.md)).

**Unverified:** this session could not open the official pages. `discover.data.vic.gov.au` and `land.vic.gov.au`
did not resolve (outside the session's network), and curl could not reach `data.qld.gov.au`, `data.gov.au`,
QSpatial or ELVIS either. Every finding below comes from search-result extracts of the pages cited. Licences, sizes and
coverage must be checked on the pages themselves before any build. Nothing was signed up for and no one was contacted.

## Victoria: what maps onto the New Zealand index

| NZ column | Victoria source | Licence (as found) | Bulk access | Catch |
| --- | --- | --- | --- | --- |
| Parcels (lot/plan ids, area) | DTP, Vicmap Property: Parcel Polygon (about 3.3 million parcels; weekly; statewide) [1][2][3] | CC BY 4.0 on Data.Vic; CC BY 3.0 AU on the data.gov.au mirror [4][5] | SHP, GDB, MIF, TAB, DWG, DXF downloads, plus WMS/WFS and a REST API [4][6] | whole-state file size not found; guest DataShare users can order one dataset at a time [7] |
| Title count | none open: title searches are paid through LANDATA or brokers [8][9] | — | — | **not possible** |
| Easements | Vicmap Property "Easement Line" (approved and proposed easements as lines) [10][11] | as parcels (not separately verified) | GDB and services [11] | only a subset of easements is captured [10]; lines, not polygons |
| Addresses | Vicmap Address (geocoded address points; "continual" updates) [12]; or national G-NAF (see NSW note) | CC BY 4.0 on Data.Vic; CC BY 3.0 AU on mirrors [12][13] | SHP, GDB, DWG, DXF, MIF, TAB, WMS, WFS [13] | none known |
| Road frontage | Vicmap Transport Road Line (roads, bridges, tracks, ferries) [14][15] | CC BY 4.0 in product description 5.8; CC BY 3.0 AU on mirror [16][15] | Data.Vic downloads [14] | method differs from NZ: road lines, so frontage needs road parcels from Vicmap Property instead (not verified that road parcels are flagged) |
| Coast, water | Vicmap Hydro (water features and coastal navigation features; weekly) [17] | "Creative Commons" (version not stated) [17] | Data.Vic [17] | no separate coastline layer found |
| Buildings | Vicmap Buildings: partial cover (City of Melbourne), currency 2017–2022 [18]; otherwise Overture buildings (ODbL, see NSW note) | Vicmap Buildings licence not verified | not verified | no statewide state footprints; ODbL share-alike on Overture |
| Ground, slope | Vicmap Elevation 10 m DEM [19][20]; 1 m DEM covers about 60% of the land and 98% of populated areas [19] | 10 m DEM: CC BY 4.0 [20]; 1 m DEM and LiDAR points: "licensed use" [19] | 10 m: Data.Vic or ELVIS [19]; 1 m: web services by subscription for government; LiDAR via ELVIS [19] | 1 m terms for non-government users not clear; Geoscience Australia 5 m DEM as fallback (see NSW note, not re-checked) |
| **Zoning (new)** | Vicmap Planning: Planning Scheme Zone Polygon, all Victorian planning schemes [21][22] | CC BY 4.0 on Data.Vic; CC BY 3.0 AU on mirror [21][22] | Data.Vic downloads (formats not verified) | none known: statewide, like NSW |
| **Overlays (new)** | Vicmap Planning: Planning Scheme Overlay Polygon, all schemes [23] (includes flood and bushfire overlays by name, e.g. LSIO, BMO: not verified in the extract) | CC BY 3.0 AU on mirror; Data.Vic licence assumed CC BY 4.0, not verified [23] | as zones | which overlay codes exist must be read from the code list [24] |
| **Bushfire prone (new)** | Designated Bushfire Prone Area (BPA), review 25B gazetted 16 June 2026 [25] | CC BY 4.0 on Data.Vic; CC BY 3.0 AU on mirror [25][26] | SHP, GDB, MIF, TAB, DWG, DXF, WMS, WFS [26] | none known |
| Flood | Victorian Flood History (Oct 2022 event), satellite-derived extents, "operational use only" [27] | CC BY 3.0 AU on mirror; CC BY 4.0 on researchdata [27][28] | GDB, SHP, TAB, WFS [27] | not modelled; gaps; planning overlays are the better flood source |
| Coastal hazard | Victorian Coastal Inundation, sea level rise to 2100 (and storm tide 2100) [29][30] | CC BY 4.0 on Data.Vic [29] | Data.Vic | 1:75,000 scale; "not appropriate for property-level risk assessment" [29] |
| District | ABS ASGS LGA (see NSW note) | CC BY 4.0 | GeoPackage | none |

### Victoria assessment

Feasible and free. Victoria looks easier than NSW: the cadastre, addresses, zones, overlays and bushfire prone
area are all listed under CC BY 4.0 on Data.Vic, with whole-state file downloads in common formats. The only
conflict found is the older CC BY 3.0 AU label on data.gov.au mirrors. Gaps: no title count; easements are partial
lines; no statewide state building footprints; 1 m elevation and LiDAR are "licensed use", not open [19].

## Queensland: what maps onto the New Zealand index

| NZ column | Queensland source | Licence (as found) | Bulk access | Catch |
| --- | --- | --- | --- | --- |
| Parcels (lot/plan ids, area) | Department of Resources, "Cadastral data – Queensland series" (DCDB), moving to the Queensland Spatial Cadastral Fabric (QSCF); about 3 million parcels [31][32] | CC BY ("all spatial cadastral data is provided as open data under a Creative Commons CC-BY licence") [33]; CC BY 4.0 on DCDB Lite record [34] | "Cadastral data weekly – whole of State Queensland", file geodatabase, updated weekly on Sunday [35]; QSCF whole-state zip about 4 GB [36]; ArcGIS REST service [37] | DCDB to QSCF migration may change fields [38]; dataset pages list licences differently [33] |
| Title count | none open: Titles Queensland title searches are paid (about A$25.71 a current search, FY2026–27, from a search extract) [39][40] | — | — | **not possible** |
| Easements | easement parcels are a separate layer in the cadastre (base, easement, strata, volumetric) [37][41] | as parcels | in the cadastre file and REST service [37] | better than Victoria: easement polygons |
| Addresses | "Property address Queensland" (text package and by area of interest) [42][43]; or G-NAF | CC BY 4.0 on researchdata; "not specified" on data.gov.au [44][42] | GDB, KML, SHP, TAB, and a text package [43] | licence to confirm |
| Road frontage | cadastre road parcels (not verified); "Queensland roads and tracks" baseline centrelines from cadastre road casements [45] | not verified [45] | QSpatial [45] | licence to confirm |
| Coast, water | "Coastline – Queensland"; watercourse lines by drainage division [46] | topographic data is "supplied under a licence agreement" [47]; some contour data is CC BY [47] | QSpatial: SHP, GDB, KML, TAB, WMS [46] | licence of coastline and watercourses must be checked |
| Buildings | "Buildings – Queensland series" (points under 625 m², areas over 625 m²) [48]; QRA "Queensland Building Footprints" (Microsoft open footprints plus LiDAR) [49]; or Overture | CC BY 4.0 on data.qld.gov.au; "not specified" on mirror [48]; QRA service licence not verified [49] | data.qld.gov.au downloads; QRA MapServer [49] | small buildings are points only; Microsoft-derived footprints carry ODbL |
| Ground, slope | LiDAR DEMs via ELVIS; 5 m LiDAR DEM free [50] | free download once data is over 3 years old; newer LiDAR must be bought [50][51] | ELVIS tile orders [50] | newer LiDAR costs money (price not stated); exact ELVIS licence not verified |
| **Zoning (new)** | **no statewide layer found.** Zones are per council (e.g. Moreton Bay, Townsville, Bundaberg) [52][53]; a public data request asks for one statewide set [54] | per council (not checked) | per council; number of councils with open zone data not verified | would need many council sources, like NZ |
| State overlays | SPP Interactive Mapping System layers [55] | "non-exclusive non-transferable licence to access and use" [55] | not verified as bulk | terms look closed; check before use |
| **Bushfire prone (new)** | "Bushfire prone area – Queensland series", regional packs [56] | CC BY 4.0 on researchdata and methodology record; "not specified" on mirror [57][58] | regional download packs; a mirror says "email directly for a copy" [56] | licence to confirm; may need an email request |
| Flood | Queensland Floodplain Assessment Overlay (interim, whole state, 2013) [59][60]; council flood overlays | "open data" on data.qld.gov.au; an old 2010 record says internal use only [60][61] | data.qld.gov.au [60] | coarse, interim; licence to confirm |
| Coastal hazard | Erosion prone area; storm tide high and medium hazard [62][63][64] | "not specified" on mirrors; CC BY 4.0 on researchdata for SoE2017 [62][65] | data.gov.au mirrors; CoastalManagement MapServer [64] | "indicative only" [64]; licence to confirm |
| District | ABS ASGS LGA (see NSW note) | CC BY 4.0 | GeoPackage | none |

### Queensland assessment

Parcels are feasible and free: a weekly whole-state file under CC BY, with easements as their own polygon layer. The
main gap is zoning: no statewide zoning layer was found, so zoning would mean one source per council. Many other
layers show "not specified" on data.gov.au mirrors and need their licence checked on data.qld.gov.au. Newer LiDAR
(under 3 years old) and the SPP mapping are not open. Title searches cost money.

## Sign-ups, payments and agreements

| Item | State | What is needed | Cost (as found) |
| --- | --- | --- | --- |
| DataShare scheduled orders | VIC | account for scheduling; guests order one dataset at a time [7] | free (not verified) |
| 1 m DEM, LiDAR points | VIC | subscription (government) or a commercial licence holder [19] | not stated |
| Title searches | VIC | LANDATA or broker [8][9] | fee schedule 2026–27 exists; figures not read [8] |
| LiDAR under 3 years old | QLD | purchase form [50][51] | not stated |
| Digital topographic data | QLD | licence agreement, fees by licence type [47] | not stated |
| Bushfire prone area | QLD | a mirror says email for a copy [56] | free (not verified) |
| Title searches | QLD | OTIS (Titles Queensland) [39][40] | about A$25.71 per current search (extract, not verified) |

## Next steps

1. A session with `discover.data.vic.gov.au`, `land.vic.gov.au`, `data.qld.gov.au`, `qldspatial.information.qld.gov.au`
   and `spatial-gis.information.qld.gov.au` allowed checks each licence and file size above on the source pages.
2. Victoria first: parcels, addresses, zones, overlays and bushfire prone area are all on one portal.
3. Queensland: parcels and easements, then addresses and buildings; decide whether per-council zoning is worth it.
4. Agents do not contact outside parties. Any email request (QLD bushfire data, VIC 1 m DEM) is for the owner.

## Sources

1. https://land.vic.gov.au/__data/assets/pdf_file/0027/604935/factsheet-a-more-spatially-accurate-vicmap.pdf
2. https://land.vic.gov.au/maps-and-spatial/spatial-data/vicmap-catalogue/vicmap-property
3. https://discover.data.vic.gov.au/en_AU/dataset/vicmap-property-property-polygon-with-property-and-address-detail
4. https://discover.data.vic.gov.au/dataset/10a6ee59-86a2-4490-9bb3-f2af5deea9dc
5. https://www.data.gov.au/data/dataset/vicmap-property-parcel-polygon
6. https://discover.data.vic.gov.au/dataset/vicmap-property-rest-api
7. https://datashare.maps.vic.gov.au/frontend/assets/docs/DataShare-2.0-User-Manual.pdf
8. https://www.land.vic.gov.au/__data/assets/word_doc/0019/773200/landata-service-charges-2026-2027.docx
9. https://www.land.vic.gov.au/land-registration/for-individuals/property-and-land-titles-information
10. https://metashare.maps.vic.gov.au/geonetwork/srv/api/records/fd229de1-c812-5799-b3c9-58f166667d20
11. https://discover.data.vic.gov.au/en_AU/dataset/vicmap-property-easement-line/resource/3b1c5209-7e90-409d-bdc1-8a12cd89b08f
12. https://discover.data.vic.gov.au/en_AU/dataset/vicmap-address
13. https://data.gov.au/data/dataset/vicmap-address1
14. https://discover.data.vic.gov.au/en_AU/dataset/vicmap-transport-road-line
15. https://data.gov.au/data/dataset/vicmap-transport-road-line
16. https://www.land.vic.gov.au/__data/assets/word_doc/0031/565627/Vicmap-Transport-Product-Description-5.8.docx
17. https://www.land.vic.gov.au/maps-and-spatial/spatial-data/vicmap-catalogue/vicmap-hydro
18. https://land.vic.gov.au/maps-and-spatial/spatial-data/vicmap-catalogue/vicmap-buildings
19. https://www.land.vic.gov.au/maps-and-spatial/spatial-data/vicmap-catalogue/vicmap-elevation
20. https://www.land.vic.gov.au/__data/assets/word_doc/0024/501099/Product-Data-Specification-DEM-10m-.docx
21. https://discover.data.vic.gov.au/en_AU/dataset/vicmap-planning-planning-scheme-zone-polygon
22. https://data.gov.au/data/dataset/ff71324b-3140-4cb2-a8ab-b7942f1ec872
23. https://data.gov.au/data/dataset/7cc08398-09b9-4adc-93d9-9ade27ee6868
24. https://data.gov.au/data/dataset/f772194a-83c4-477e-99f4-51782a964321
25. https://discover.data.vic.gov.au/dataset/designated-bushfire-prone-area-bpa
26. https://data.gov.au/data/dataset/designated-bushfire-prone-area-bpa
27. https://data.gov.au/data/dataset/5a27fb6b-28f6-4057-82df-398c7de224b9
28. https://researchdata.edu.au/victorian-flood-history-event-public/2768661
29. https://discover.data.vic.gov.au/dataset/victorian-coastal-inundation
30. https://discover.data.vic.gov.au/en_AU/dataset/victorian-coastal-inundation-sea-level-rise-storm-tide-2100
31. https://www.data.qld.gov.au/dataset/cadastral-data-queensland-series
32. https://resources.qld.gov.au/data-mapping/initiatives/cadastral-address-modernisation-project
33. https://www.business.qld.gov.au/running-business/support-assistance/mapping-data-imagery/data/digital-cadastral
34. https://catalogue.eatlas.org.au/geonetwork/srv/api/records/a86f062e-f47c-49f1-ace5-3e03a2272088
35. https://www.data.qld.gov.au/dataset/cadastral-data-queensland-series/resource/72ce2a1d-9f21-46f3-a116-0b4c727d5611
36. https://www.business.qld.gov.au/running-business/support-assistance/mapping-data-imagery/data/digital-cadastral/products
37. https://spatial-gis.information.qld.gov.au/arcgis/rest/services/PlanningCadastre/LandParcelPropertyFramework_TimeAware/FeatureServer/layers
38. https://business.qld.gov.au/running-business/support-services/mapping-data-imagery/data/digital-cadastral/access
39. https://titlesqld.com.au/title-searches/
40. https://www.titlesqld.com.au/wp-content/uploads/2026/05/Titles-Registry-Fees_FY-2026-to-2027.pdf
41. https://qportal.information.qld.gov.au/arcgis/rest/services/Spatial_Cadastre_Accuracy/MapServer/1/metadata
42. https://data.gov.au/data/dataset/65b51e59-296c-4908-9874-5d99f2f28264
43. https://www.data.qld.gov.au/dataset/property-address-queensland-by-area-of-interest
44. https://researchdata.edu.au/property-address-queensland-area-interest/1328171
45. https://data.gov.au/data/dataset/queensland-roads-and-tracks
46. https://spatial-qld-support.atlassian.net/wiki/spaces/SDS/pages/581140492/QSpatial+-+Topographic+Data
47. https://www.business.qld.gov.au/running-business/support-assistance/mapping-data-imagery/data/topographic
48. https://www.data.qld.gov.au/dataset/buildings-queensland-series
49. https://gisservices.qra.qld.gov.au/arcgis/rest/services/Foundation_Data/Queensland_Building_Footprints/MapServer/0
50. https://spatial-qld-support.atlassian.net/wiki/spaces/QSUITE/pages/260538373/Elevation+and+LiDAR
51. https://www.business.qld.gov.au/running-business/support-assistance/mapping-data-imagery/imagery/airborne-lidar-data
52. https://planning.qld.gov.au/planning-framework/plan-making/local-planning/zoning-information
53. https://data.gov.au/data/dataset/mbrc-planning-scheme-zones
54. https://www.data.qld.gov.au/datarequest/e71814c8-ea2c-4b0d-9880-98d16c3adea5
55. https://www.planning.qld.gov.au/planning-framework/mapping/disclaimer
56. https://data.gov.au/data/dataset/60b7bb03-873d-4837-9480-3c6595867f0e
57. https://researchdata.edu.au/bushfire-prone-area-queensland-series/658378
58. https://data.gov.au/data/dataset/30f0f8a3-3cff-494e-ab7c-1f2deb47504d
59. https://www.qld.gov.au/emergency/dealing-disasters/disaster-types/flood/for-councils-and-flood-practitioners/flood-data-and-resources/queensland-floodplain-assessment-overlay
60. https://www.data.qld.gov.au/dataset/67dc96e5-4dd6-46b0-a1ce-75baa7789a6c
61. https://wetlandinfo.des.qld.gov.au/wetlands/facts-maps/get-mapping-help/metadata/floodplain-assessment-overlay
62. https://data.gov.au/data/dataset/erosion-prone-area-series
63. https://data.gov.au/data/dataset/storm-tide-high-hazard-queensland
64. https://gisservices.information.qld.gov.au/arcgis/rest/services/PlanningCadastre/CoastalManagement/MapServer
65. https://researchdata.edu.au/soe2017-erosion-prone-area/1355888
