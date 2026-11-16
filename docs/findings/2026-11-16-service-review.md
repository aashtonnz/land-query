# Fresh-eyes review of the query service before outside use (T-126)

16 Nov 2026. A reviewer with no part in building it tested `service/` on the national index (2,467,530 parcels, the
15 Nov build), on Kāpiti's results and in HTTP mode. It edited nothing.

| # | Area | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| 1 | Load | Every query runs under one lock and the rate limit counted requests, not time: six heavy searches from one address held the database 30 s, and an `about` waited 8 s | Serious | Fixed: a request that cannot get the database within 10 s is told the service is busy; one request at a time per address over HTTP |
| 2 | Hosting | Preparing the national index read it whole: 5.3 GB of memory, against "about 1 GB" in the container note; serving peaked at 1.1 GB | Serious | Fixed: prepared a batch at a time (1.4 GB peak, 14 s); the container note and the hosting proposal say 2 GB |
| 3 | Load | The 10 s limit applied to each of a search's two statements, so one call could hold the database 20 s | Moderate | Fixed: one deadline for the count and the rows |
| 4 | HTTP | Behind a proxy the limit read the caller's own first X-Forwarded-For entry, so anyone could change it; over 100,000 addresses cleared everyone's limit | Moderate | Fixed: the right-most entry, the proxy's; the longest unseen addresses are dropped first |
| 5 | Provenance | The instructions promised a sha256 per source, which national tiles do not have; lakes and rivers had no provenance (recorded as a bare count) | Moderate | Fixed: national wording names address, feature count and fetch time; the count is carried as `lakes_rivers` |
| 6 | Provenance | The 15 Nov build claimed Stats NZ boundaries it did not use (built before them); the build never recorded the boundaries or the easement layer even when used | Moderate | Fixed: the service names sources and attribution from what the build recorded; builds now record `districts` and `nonprimary` per tile and say how districts were decided |
| 7 | Catalogue | `territorial_authority` labelled published though inferred; `titles_not_found` published though derived; `unit_id` derived though LINZ's id | Moderate | Fixed in SOURCES.md |
| 8 | Values | All 991 Chatham Islands parcels read 0 buildings where LINZ has no outlines (unknown, not 0) | Moderate | Fixed: building columns empty in a tile with no outline at all; test |
| 9 | Errors | A malformed `op` gave a raw exception | Minor | Fixed: checked; unexpected errors give a plain message |
| 10 | Input | null, NaN, booleans as a box and a string as `columns` were accepted silently | Minor | Fixed: refused with a message |
| 11 | Wording | The `query` tool and `has_class` offered for national data; "one parcel" for an appellation that names many; the 100-row cap not stated | Minor | Fixed: national servers have no `query` tool; descriptions say how matching and caps work |
| 12 | Catalogue | One meaning shared by several columns; the land outline named as lakes and rivers | Minor | Fixed: rows split in SOURCES.md |
| 13 | Size | Fixed fields repeated in each row's values; meanings repeated in every response | Minor | Open (T-126): a short form for the meanings |
| 14 | Output | DuckDB's progress bar could write to stdout, the MCP channel | Minor | Fixed: turned off |
| 15 | Licence | The 8 m elevation model (Geographx) not named in the attribution | Suspected | Fixed: named where elevation is recorded |
| 16 | Hosting | The container trusts the newest release without a checksum | Minor | Open (T-126): publish a checksum with the release |

Checked and found correct: no SQL injection (columns checked, values parameters, limits cast); the limits on
conditions, `in` values, offset, rows and box size; query interruption; the host check (421), body limit (413) and
`/health`; no title references, types or owner data anywhere, and withheld columns not leaked through filters,
meanings, errors or order; area searches exact (168 of 168 in a 1 km box, paged without repeats); lookups by id and
appellation; integers and empty values consistent with the build; every national column described.

Note: before the HTTP mode was in scope, the reviewer started the server twice bound to all interfaces of its sandbox
(about 6 minutes). The server now listens on this machine only unless `LANDQ_HOST` says otherwise; the container sets it.
