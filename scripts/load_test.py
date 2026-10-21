"""
Simple load test for the Brightr backend.

Usage:
    python scripts/load_test.py --url https://brightr-api-jtpi.onrender.com \
        --image data/test/test_1.jpg --users 10

Each simulated user: create session -> upload image -> analyze.
Note: every run makes real Gemini calls and counts against the per-IP rate limit
(RATE_LIMIT_ANALYZE_PER_HOUR); raise it temporarily on the server when testing.
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


def one_user(base: str, image: Path, key: str, idx: int) -> dict:
    headers = {"X-Internal-Key": key} if key else {}
    t0 = time.perf_counter()
    try:
        s = requests.post(f"{base}/api/sessions", json={}, headers=headers, timeout=60)
        s.raise_for_status()
        sid = s.json()["id"]
        with image.open("rb") as f:
            up = requests.post(
                f"{base}/api/sessions/{sid}/images",
                files={"images": (image.name, f, "image/jpeg")},
                headers=headers,
                timeout=120,
            )
        up.raise_for_status()
        an = requests.post(
            f"{base}/api/sessions/{sid}/analyze", headers=headers, timeout=300
        )
        return {
            "user": idx,
            "status": an.status_code,
            "seconds": time.perf_counter() - t0,
            "error": "" if an.ok else an.text[:150],
        }
    except Exception as e:
        return {
            "user": idx,
            "status": 0,
            "seconds": time.perf_counter() - t0,
            "error": str(e)[:150],
        }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--users", type=int, default=10)
    p.add_argument("--key", default="", help="INTERNAL_API_KEY if set")
    a = p.parse_args()

    base = a.url.rstrip("/")
    image = Path(a.image)
    print(f"Running {a.users} concurrent users against {base} ...")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=a.users) as ex:
        results = list(
            ex.map(lambda i: one_user(base, image, a.key, i), range(a.users))
        )
    total = time.perf_counter() - t0

    ok = [r for r in results if r["status"] == 200]
    times = sorted(r["seconds"] for r in ok)
    print(f"\nTotal wall time: {total:.1f}s")
    print(f"Success: {len(ok)}/{len(results)}")
    if times:
        print(
            f"Latency  median={statistics.median(times):.1f}s  "
            f"max={times[-1]:.1f}s"
        )
    codes: dict = {}
    for r in results:
        codes[r["status"]] = codes.get(r["status"], 0) + 1
    print(f"Status codes: {codes}")
    for r in results:
        if r["status"] != 200:
            print(f"  user {r['user']}: {r['status']} {r['error']}")


if __name__ == "__main__":
    main()
