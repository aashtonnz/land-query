"""Send a map build's data to Cloudflare R2 (D-26): upload_r2.py DATA_DIR BUILD.

Puts every file under DATA_DIR at builds/BUILD/<its path> in the bucket, many at once (about 107,000 small files: the
AWS command line sent about 25 a second, too slow for the job), never changed once written so browsers may keep them
a year; then keeps the newest KEEP builds and deletes older ones, 1,000 objects a request. Reads the bucket, endpoint
and keys from the environment: R2_BUCKET, R2_ACCOUNT_ID, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor

THREADS = 128
KEEP = 3   # a page loaded just before an update still finds its data
CACHE = "public, max-age=31536000, immutable"
TYPES = {".json": "application/json", ".bin": "application/octet-stream", ".txt": "text/plain; charset=utf-8"}


def files(root):
    for d, _, names in os.walk(root):
        for n in names:
            p = os.path.join(d, n)
            yield p, os.path.relpath(p, root).replace(os.sep, "/")


def upload(client, bucket, root, build, threads=THREADS):
    """Upload every file; returns how many. Any failure stops the job (the page would point at missing data)."""
    def put(item):
        path, rel = item
        with open(path, "rb") as f:
            client.put_object(Bucket=bucket, Key=f"builds/{build}/{rel}", Body=f.read(), CacheControl=CACHE,
                              ContentType=TYPES.get(os.path.splitext(rel)[1], "application/octet-stream"))
    items = list(files(root))
    with ThreadPoolExecutor(threads) as ex:
        for _ in ex.map(put, items): pass
    return len(items)


def builds(client, bucket):
    """The build folders in the bucket, oldest first (their names are UTC stamps, so they sort by time)."""
    out, token = [], None
    while True:
        r = client.list_objects_v2(Bucket=bucket, Prefix="builds/", Delimiter="/", **({"ContinuationToken": token} if token else {}))
        out += [p["Prefix"].split("/")[1] for p in r.get("CommonPrefixes", [])]
        if not r.get("IsTruncated"): return sorted(out)
        token = r["NextContinuationToken"]


def prune(client, bucket, keep=KEEP):
    """Delete every build but the newest `keep`; returns the builds deleted."""
    old = builds(client, bucket)[:-keep] if keep else builds(client, bucket)
    for b in old:
        token = None
        while True:
            r = client.list_objects_v2(Bucket=bucket, Prefix=f"builds/{b}/", **({"ContinuationToken": token} if token else {}))
            keys = [{"Key": o["Key"]} for o in r.get("Contents", [])]
            for i in range(0, len(keys), 1000):
                client.delete_objects(Bucket=bucket, Delete={"Objects": keys[i:i + 1000], "Quiet": True})
            if not r.get("IsTruncated"): break
            token = r["NextContinuationToken"]
    return old


def main(root, build):
    import boto3
    from botocore.config import Config
    client = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", region_name="auto",
                          config=Config(max_pool_connections=THREADS, retries=dict(max_attempts=10, mode="adaptive")))
    bucket = os.environ["R2_BUCKET"]
    t0 = time.time(); n = upload(client, bucket, root, build)
    print(f"{n} files to builds/{build}/ in {time.time() - t0:.0f} s", flush=True)
    print("deleted older builds:", prune(client, bucket) or "none")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
