# The query service over HTTP (T-26), on the newest published national index. Build from the repository root:
#   docker build -f service/host/Dockerfile -t land-query .
#   docker run -p 8000:8000 -e LANDQ_ALLOWED_HOSTS=your.host.name land-query
# At start it fetches the newest national-* release (public, no key), prepares it for the service and serves MCP at
# /mcp (stateless, JSON), with /health for the host's checks. About 1 GB of memory is enough (DuckDB is capped at 1 GB).
FROM python:3.12-slim
RUN pip install --no-cache-dir "mcp==2.3.0" duckdb pandas pyarrow shapely requests uvicorn
WORKDIR /app
COPY SOURCES.md /app/SOURCES.md
COPY pipeline/councils /app/pipeline/councils
COPY pipeline/provenance.py /app/pipeline/provenance.py
COPY service /app/service
ENV LANDQ_TRANSPORT=http LANDQ_AUDIENCE=public LANDQ_RESULTS=/data/results PORT=8000 LANDQ_RATE=60
EXPOSE 8000
CMD ["python3", "/app/service/host/start.py"]
