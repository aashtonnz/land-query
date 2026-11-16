"""Send a map build's data to Cloudflare R2 (D-26): upload_r2.py DATA_DIR BUILD.

BUILD names the data by its content (build_map.data_id). Puts every file under DATA_DIR at builds/BUILD/<its path> in
the bucket, many at once (about 107,000 small files: the AWS command line sent about 25 a second, too slow for the
job), never changed once written so browsers may keep them a year, and meta.json last, so a folder with meta.json is
complete. A build whose folder is already complete (its data unchanged) sends only meta.json again, to mark it newest:
one write instead of 107,000. Then keeps the newest KEEP complete builds, by when their meta.json was written, and
deletes the rest, incomplete ones included, 1,000 objects a request. Reads the bucket, endpoint and keys from the
environment: R2_BUCKET, R2_ACCOUNT_ID, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
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


MARK = "meta.json"   # written last: a folder holding it is complete


def complete(client, bucket, build):
    try: client.head_object(Bucket=bucket, Key=f"builds/{build}/{MARK}"); return True
    except Exception as e:
        if getattr(e, "response", {}).get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"): return False
        raise


def upload(client, bucket, root, build, threads=THREADS):
    """Upload every file, meta.json last; returns how many were sent. Any failure stops the job (the page would point
    at missing data). If the build is already complete in the bucket, only meta.json is sent."""
    def put(item):
        path, rel = item
        with open(path, "rb") as f:
            client.put_object(Bucket=bucket, Key=f"builds/{build}/{rel}", Body=f.read(), CacheControl=CACHE,
                              ContentType=TYPES.get(os.path.splitext(rel)[1], "application/octet-stream"))
    items = list(files(root))
    last = [i for i in items if i[1] == MARK]
    if not last: raise SystemExit(f"no {MARK} in {root}")
    if not complete(client, bucket, build):
        with ThreadPoolExecutor(threads) as ex:
            for _ in ex.map(put, [i for i in items if i[1] != MARK]): pass
        put(last[0]); return len(items)
    put(last[0]); return 1


def folders(client, bucket):
    out, token = [], None
    while True:
        r = client.list_objects_v2(Bucket=bucket, Prefix="builds/", Delimiter="/", **({"ContinuationToken": token} if token else {}))
        out += [p["Prefix"].split("/")[1] for p in r.get("CommonPrefixes", [])]
        if not r.get("IsTruncated"): return out
        token = r["NextContinuationToken"]


def builds(client, bucket):
    """The complete build folders, oldest first by when their meta.json was written, and the incomplete ones."""
    done, partial = [], []
    for b in folders(client, bucket):
        try: done.append((client.head_object(Bucket=bucket, Key=f"builds/{b}/{MARK}")["LastModified"], b))
        except Exception as e:
            if getattr(e, "response", {}).get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"): partial.append(b)
            else: raise
    return [b for _, b in sorted(done)], partial


def prune(client, bucket, keep=KEEP, current=None):
    """Delete every complete build but the newest `keep`, and every incomplete one (a cancelled upload) but `current`;
    returns the builds deleted."""
    done, partial = builds(client, bucket)
    old = (done[:-keep] if keep else done) + [b for b in partial if b != current]
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
    print(f"{n} files to builds/{build}/ in {time.time() - t0:.0f} s" + (" (data unchanged: already there)" if n == 1 else ""), flush=True)
    print("deleted older or incomplete builds:", prune(client, bucket, current=build) or "none")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
