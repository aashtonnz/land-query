"""Read-only queries over the compiled Kāpiti Coast results, with provenance on every value (T-36).

The results directory holds what `kapiti.yml` publishes on the `kapiti-results` branch: `units.parquet`,
`provenance.json`, `inverse_queries.json` and `RUN.txt`. Every response carries, for each column returned, its kind
(published, derived or modelled), meaning, sources, fit-for-parcel flag and licence status, and for each source its
dataset, URL, licence and the sha256 and fetch time of the data each row's block was compiled from.

Audience (D-12): "public" serves only columns whose every source has a licence stated on the dataset; the others are
withheld, and cannot be filtered on, until the councils confirm their portal-wide statements in writing (T-35).
"internal" serves everything, for the owner.
"""
import json, math, os, re, threading
import duckdb
import catalogue as cat

MAX_ROWS = 500
MAX_ROWS_ALL_COLUMNS = 100   # without a `columns` list, fewer rows: a full row is about 2.4 KB of JSON (T-52)
MAX_CONDITIONS = 20
MAX_IN_VALUES = 1000         # across all `in` conditions
MAX_OFFSET = 100_000
MAX_BBOX_M = 20_000          # a box at most 20 km across (T-59: promised, now enforced)
WIDE_COLUMNS = 20            # asking for more columns than this counts as asking for all of them
QUERY_SECONDS = 10
OPS = {"=": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
SAFE_CLASS = re.compile(r"^[\w\s\-.,'():/āēīōūĀĒĪŌŪ]+$")


class QueryError(ValueError):
    pass


class LandQuery:
    def __init__(self, results_dir, audience="public"):
        if audience not in ("public", "internal"): raise ValueError("audience must be 'public' or 'internal'")
        self.audience, self.dir = audience, results_dir
        self._lock = threading.Lock()
        self.db = duckdb.connect(config=dict(memory_limit="1GB", threads=2))  # one request cannot take the host down (T-52)
        path = os.path.join(results_dir, "units.parquet").replace("'", "''")  # a view cannot take a parameter
        self.db.execute(f"CREATE VIEW units AS SELECT * FROM read_parquet('{path}')")
        self.all_columns = [r[0] for r in self.db.execute("DESCRIBE units").fetchall()]
        self.meta = {c: cat.column_meta(c) for c in self.all_columns}
        missing = [c for c, m in self.meta.items() if m is None]
        if missing: raise RuntimeError(f"columns missing from SOURCES.md or the catalogue: {missing}")
        self.columns = [c for c in self.all_columns
                        if audience == "internal" or (self.meta[c]["licence_cleared"] and c not in cat.PUBLIC_EXCLUDE)]
        self.withheld = [c for c in self.all_columns if c not in self.columns]
        p = os.path.join(results_dir, "provenance.json")
        self.prov = json.load(open(p)) if os.path.exists(p) else {}
        r = os.path.join(results_dir, "RUN.txt")
        self.run = open(r).read().strip() if os.path.exists(r) else None

    # ---- descriptions ----
    def about(self):
        n = self._run("SELECT count(*) FROM units", [])[0][0]  # under the lock like every query (T-62)
        return dict(
            dataset="Kāpiti Coast District parcels, compiled from public LINZ, KCDC and GWRC sources",
            run=self.run, parcels=n, audience=self.audience, columns_served=len(self.columns), columns_withheld=len(self.withheld),
            coordinates="NZTM2000 (EPSG:2193), metres; heights NZVD2016",
            licence_note=("Values come from CC BY 4.0 sources; attribute LINZ, Kāpiti Coast District Council and Greater "
                          "Wellington Regional Council as listed per source. In public mode, columns relying on a "
                          "portal-wide licence statement are withheld until confirmed in writing."),
            caution="Derived and modelled values are estimates from public data; check against the sources before relying on them.",
            boundary=("Whole parcels are published. A parcel crossing the district boundary is included if its "
                      "representative point (a point always inside it) or at least 1,000 m2 of it lies in the district, "
                      "so a few parcels reach far outside it (one forest section is 615 km2, about 40 km2 of it in the "
                      "district). Their area covers the whole parcel; terrain covers the part with LiDAR "
                      "(lidar_coverage_pct); building and open-ground values come from KCDC's 2021 building outlines, which "
                      "miss some houses (unmapped_structure_m2 warns of most), and are empty unless the outlines and the "
                      "fetch window cover the parcel (buildings_coverage_pct, coverage_pct); council layers cover what "
                      "the council maps. "
                      "district_share_pct gives the share inside; it is withheld in public mode until the council licence "
                      "is confirmed (T-35). About 70 railway parcels are not included: the council's parcel list omits them."),
            empty_values=("An empty value is never a measured 0 (a count of recommended building levels is empty "
                          "where there are none). What else it means depends on the column: an empty hazard "
                          "column means the parcel is outside that hazard where the council mapped it, and not mapped "
                          "elsewhere. KCDC's flood layers cover only its flood models, which leave out Kapiti Island, the "
                          "hills and much of the rural north. An empty zones or gw_eq_slope_failure value means not "
                          "mapped; gw_liquefaction maps only soils with significant potential. In public mode some flood "
                          "layers are withheld (see describe_columns), so empty served flood columns do not mean the "
                          "parcel is outside every flood layer."),
            provenance_available=bool(self.prov))

    def describe_columns(self, contains=None):
        out = {}
        for c in self.all_columns:
            if c in self.withheld:  # describing a withheld column can reveal its contents (T-52)
                if contains and contains.lower() not in c.lower(): continue
                out[c] = dict(served=False, withheld=cat.PUBLIC_EXCLUDE.get(c, "licence not yet confirmed in writing (T-35)"))
                continue
            if contains and contains.lower() not in c.lower() and contains.lower() not in self.meta[c]["meaning"].lower(): continue
            out[c] = dict(self.meta[c], served=True)
        return out

    # ---- queries ----
    def parcel(self, unit_id=None, appellation=None, columns=None):
        if unit_id is None and not appellation: raise QueryError("give unit_id or appellation")
        where = [dict(column="unit_id", op="=", value=int(unit_id))] if unit_id is not None else \
                [dict(column="appellation", op="=", value=str(appellation))]
        return self.search(where=where, columns=columns, limit=20)

    def search(self, bbox=None, where=None, columns=None, limit=100, offset=0):
        cols = self._columns(columns)
        clauses, params = [], []
        if bbox is not None:
            if "bbox_xmin" not in self.all_columns: raise QueryError("these results predate parcel locations (T-36): area queries need the next rebuild")
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4: raise QueryError("bbox is [xmin, ymin, xmax, ymax] in NZTM2000 metres")
            try: x0, y0, x1, y1 = (float(v) for v in bbox)
            except (TypeError, ValueError): raise QueryError("bbox values must be numbers") from None
            if not all(map(math.isfinite, (x0, y0, x1, y1))) or x1 < x0 or y1 < y0: raise QueryError("bbox must be finite, with xmin <= xmax and ymin <= ymax")
            if x1 - x0 > MAX_BBOX_M or y1 - y0 > MAX_BBOX_M: raise QueryError(f"bbox at most {MAX_BBOX_M // 1000} km across")
            clauses.append("bbox_xmax >= ? AND bbox_xmin <= ? AND bbox_ymax >= ? AND bbox_ymin <= ?"); params += [x0, x1, y0, y1]
        where = where or []
        if not isinstance(where, list) or len(where) > MAX_CONDITIONS: raise QueryError(f"where is a list of at most {MAX_CONDITIONS} conditions")
        if sum(len(c.get("value")) for c in where if isinstance(c, dict) and c.get("op") == "in" and isinstance(c.get("value"), list)) > MAX_IN_VALUES:
            raise QueryError(f"at most {MAX_IN_VALUES} values across all 'in' conditions")
        for cond in where:
            c, p = self._condition(cond); clauses.append(c); params += p
        sql_where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        try: limit, offset = int(limit), int(offset)
        except (TypeError, ValueError): raise QueryError("limit and offset must be whole numbers") from None
        cap = MAX_ROWS if columns and len(cols) <= WIDE_COLUMNS else MAX_ROWS_ALL_COLUMNS
        limit = max(1, min(limit, cap))
        if not 0 <= offset <= MAX_OFFSET: raise QueryError(f"offset must be between 0 and {MAX_OFFSET}")
        total = self._run(f"SELECT count(*) FROM units{sql_where}", params)[0][0]
        fixed = ["unit_id", "appellation", "block_id", "geometry_source"] if "geometry_source" in self.all_columns else ["unit_id", "appellation", "block_id"]
        sel = ", ".join(f'"{c}"' for c in dict.fromkeys(fixed + cols))
        res = self._run(f"SELECT {sel} FROM units{sql_where} ORDER BY unit_id LIMIT {limit} OFFSET {offset}", params, names=True)
        names, data = res
        rows = []
        for r in data:
            d = dict(zip(names, r))
            rows.append(dict(unit_id=d["unit_id"], appellation=d["appellation"], block_id=d["block_id"],
                             geometry_source=d.get("geometry_source"), values={c: self._value(c, d[c]) for c in cols}))
        return self._envelope(rows, cols, total=total, offset=offset)

    def _run(self, sql, params, names=False):
        """Run a query with a time limit; database errors become a plain message (the details stay in the server)."""
        with self._lock:  # one query at a time: a request's timer must never interrupt another request's query (T-59)
            return self._run_locked(sql, params, names)

    def _run_locked(self, sql, params, names):
        timer = threading.Timer(QUERY_SECONDS, self.db.interrupt); timer.start()
        try:
            res = self.db.execute(sql, params)
            out = res.fetchall()
            return ([d[0] for d in res.description], out) if names else out
        except duckdb.Error as e:
            if "INTERRUPT" in type(e).__name__.upper() or "interrupt" in str(e).lower():
                raise QueryError(f"query took longer than {QUERY_SECONDS} s: narrow it") from None
            raise QueryError("the query could not be run: check each condition's column, op and value type") from None
        finally:
            timer.cancel()

    def inverse_query(self, qid):
        iq = json.load(open(os.path.join(self.dir, "inverse_queries.json")))
        q = next((x for x in iq["queries"] if x["id"] == qid), None)
        if q is None: raise QueryError(f"unknown query {qid!r}; available: {[x['id'] for x in iq['queries']]}")
        used = {k for k in q["rows"][0] if k not in ("unit_id", "appellation", "block_id", "sources")} if q["rows"] else set()
        # judged by every source the query draws on, not only the columns it returns: a query can filter on a
        # withheld column, or rename one, without returning it (T-52)
        blocked = sorted(k for k in q.get("provenance", {}) if not cat.SOURCES.get(k, {}).get("licence_cleared"))
        blocked += sorted(c for c in used if c in cat.PUBLIC_EXCLUDE)
        # a withheld column named anywhere in the SQL (a filter or the order) can be read back from the rows (T-70)
        blocked += sorted(c for c in cat.PUBLIC_EXCLUDE if re.search(rf"\b{c}\b", q.get("sql") or ""))
        if self.audience == "public" and (blocked or not q.get("provenance")):
            return dict(id=q["id"], name=q["name"], withheld=True,
                        reason="draws on sources whose licence is not yet confirmed in writing (T-35)" if blocked else "no source list recorded")
        return dict(id=q["id"], name=q["name"], question=q["question"], sql=q["sql"], count=q["count"],
                    columns={c: self.meta[c] for c in sorted(used) if c in self.meta},
                    sources=q["provenance"], rows=q["rows"], run=self.run)

    # ---- helpers ----
    def _columns(self, columns):
        if not columns: return list(self.columns)
        bad = [c for c in columns if c not in self.all_columns]
        if bad: raise QueryError(f"unknown columns: {bad}")
        held = [c for c in columns if c in self.withheld]
        if held: raise QueryError(f"withheld in public mode: {[(c, cat.PUBLIC_EXCLUDE.get(c, 'licence not yet confirmed (T-35)')) for c in held]}")
        return list(columns)

    def _condition(self, cond):
        if not isinstance(cond, dict): raise QueryError("each condition is an object: {column, op, value}")
        c, op, v = cond.get("column"), cond.get("op", "="), cond.get("value")
        if isinstance(v, (dict, list)) and op not in ("in", "has_class"): raise QueryError(f"op {op!r} takes a single value")
        if c not in self.all_columns: raise QueryError(f"unknown column {c!r}")
        if c in self.withheld: raise QueryError(f"{c} is withheld in public mode, so it cannot be filtered on ({cat.PUBLIC_EXCLUDE.get(c, 'T-35')})")
        q = f'"{c}"'
        if op in OPS: return f"{q} {OPS[op]} ?", [v]
        if op == "in":
            if not isinstance(v, list) or not v or len(v) > 1000: raise QueryError("'in' takes a list of 1 to 1000 values")
            return f"{q} IN ({', '.join('?' * len(v))})", list(v)
        if op == "is_null": return f"{q} IS NULL", []
        if op == "not_null": return f"{q} IS NOT NULL", []
        if op == "contains": return f"CAST({q} AS VARCHAR) ILIKE ?", ["%" + str(v).replace("%", "").replace("_", "") + "%"]
        if op == "has_class":
            # an overlay column: class name, optionally with a minimum share of the parcel ({"class": ..., "min_pct": ...})
            cls, mn = (v.get("class"), v.get("min_pct", 0)) if isinstance(v, dict) else (v, 0)
            try: mn = float(mn)
            except (TypeError, ValueError): raise QueryError("min_pct must be a number") from None
            if not isinstance(cls, str) or not SAFE_CLASS.match(cls) or '"' in cls: raise QueryError("class name has unexpected characters")
            return f"coalesce(json_extract({q}, ?)::DOUBLE, -1) >= ?", ['$."' + cls + '"', max(float(mn), 0.000001)]
        raise QueryError(f"unknown op {op!r}; use one of {sorted(OPS) + ['in', 'is_null', 'not_null', 'contains', 'has_class']}")

    WHOLE = {"ww_pipe_year", "ww_pipe_condition_grade", "ww_pipe_dia_mm", "ws_pipe_dia_mm", "title_count", "easements_n",
             "land_covenants_n", "lidar_cells", "rbl_in_parcel_n"}

    def _value(self, c, v):
        if c in self.WHOLE and isinstance(v, float) and v.is_integer(): return int(v)  # stored as decimals where a column has gaps
        if isinstance(v, str) and v[:1] in "[{":
            try: return json.loads(v)
            except ValueError: return v
        return v

    def _envelope(self, rows, cols, total, offset):
        keys = {k for c in cols for k in self.meta[c]["sources"]}
        if any(r.get("geometry_source") == "KCDC mirror" for r in rows): keys.add("kcdc_parcels")  # computed on the mirror polygon
        keys = sorted(keys)
        blocks = sorted({r["block_id"] for r in rows})
        sources = {}
        for k in keys:
            s = cat.SOURCES.get(k, {})
            p = self.prov.get("district_flow" if k == "sea_mask" else k, {})
            sources[k] = dict(dataset=s.get("dataset"), url=p.get("url"), licence=s.get("licence"),
                              licence_status=s.get("licence_status"), fit=s.get("fit"),
                              by_block={b: p.get("by_block", {}).get(b) for b in blocks} if p else None)
        return dict(run=self.run, audience=self.audience, total=total, offset=offset, count=len(rows), rows=rows,
                    columns={c: self.meta[c] for c in cols}, sources=sources,
                    withheld=self.withheld if self.audience == "public" else [])
