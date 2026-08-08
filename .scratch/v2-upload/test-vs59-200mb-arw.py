"""#59 VS 端到端：200MB 伪 ARW 走分片上传链路

策略：用 200MB 真 JPEG 改 .arw 后缀（强制走 RAW 路径），dcraw 失败但链路通
"""
import httpx
import os
import time
import sys

API = "http://localhost:8000"
ARW = "/app/test-200mb.arw"


def login(c):
    r = c.post(f"{API}/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def upload_via_multipart(token):
    file_size = os.path.getsize(ARW)
    file_name = "test-200mb-vs59.arw"

    sys.path.insert(0, '/app')
    from app.services.obs_service import obs_service as _obs
    import psycopg2

    with httpx.Client(timeout=httpx.Timeout(60, read=120, write=120)) as c:
        # 1. multipart init
        r = c.post(
            f"{API}/api/upload/multipart/init",
            json={
                "file_name": file_name,
                "file_size": file_size,
                "content_type": "image/x-sony-arw",
                "asset_type": "image",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        d = r.json()
        assert d["code"] == 0, f"init failed: {d}"
        init_data = d["data"]
        batch_id = init_data["batch_id"]
        part_size = init_data["part_size"]
        total_parts = init_data["total_parts"]
        part_urls = init_data["part_upload_urls"]
        obs_key = init_data["obs_key"]
        print(f"[1] init: total_parts={total_parts}, part_size={part_size}, batch_id={batch_id[:8]}")

        url_map = {p["part_number"]: p["url"] for p in part_urls}
        print(f"   url[1]={list(url_map.values())[0][:70]}...")

        # 2. PUT 25 parts
        t0 = time.time()
        with open(ARW, "rb") as f:
            for pn in range(1, total_parts + 1):
                f.seek((pn - 1) * part_size)
                chunk = f.read(part_size)
                if not chunk:
                    break
                resp = httpx.put(url_map[pn], content=chunk, timeout=httpx.Timeout(60, read=60))
                if resp.status_code != 200:
                    print(f"   part {pn} PUT failed: {resp.status_code}")
                    break
                # 通知后端
                c.post(
                    f"{API}/api/upload/multipart/part-complete",
                    json={"batch_id": batch_id, "part_number": pn, "size": len(chunk)},
                    headers={"Authorization": f"Bearer {token}"},
                )
        elapsed = time.time() - t0
        print(f"[2] uploaded {total_parts} parts in {elapsed:.1f}s, {file_size/1024/1024/elapsed:.1f} MB/s")

        # 3. 立刻查 OBS 状态
        conn = psycopg2.connect("postgresql://imagehub:imagehub@db:5432/imagehub")
        cur = conn.cursor()
        cur.execute("SELECT obs_upload_id FROM multipart_uploads WHERE batch_id=%s", (batch_id,))
        uid = cur.fetchone()[0]
        conn.close()
        for i in range(3):
            n = len(_obs.list_uploaded_parts(obs_key, uid))
            print(f"   [list +{i+1}s] OBS parts: {n}")
            time.sleep(1)

        # 4. complete
        r = c.post(
            f"{API}/api/upload/multipart/complete",
            json={"batch_id": batch_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"[3] complete: {r.status_code} {r.text[:300]}")
        d = r.json()
        asset_id = d.get("data", {}).get("asset_id") if d.get("data") else None
        return asset_id, batch_id, d


def subscribe_sse(token, asset_id):
    print(f"[4] subscribing SSE for {asset_id[:8]}...")
    events = []
    with httpx.Client(timeout=httpx.Timeout(60, read=120)) as c:
        with c.stream("GET", f"{API}/api/upload/events/{asset_id}", timeout=60) as resp:
            raw = b""
            for chunk in resp.iter_bytes():
                raw += chunk
                if b"event: done\r\n" in raw or b"event: failed\r\n" in raw:
                    break
    raw_str = raw.decode("utf-8", errors="replace")
    current_event = None
    for line in raw_str.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            events.append((current_event, line.split(":", 1)[1].strip()[:100]))
    for ev_type, data in events:
        print(f"   - {ev_type}: {data}")
    return events


if __name__ == "__main__":
    if not os.path.exists(ARW):
        print(f"ERROR: {ARW} not found")
        sys.exit(1)

    with httpx.Client(timeout=httpx.Timeout(60, read=120)) as c:
        token = login(c)
        asset_id, batch_id, complete_resp = upload_via_multipart(token)
        if not asset_id:
            print("complete failed, no asset_id")
            sys.exit(1)
        events = subscribe_sse(token, asset_id)
        has_done = any(ev == "done" for ev, _ in events)
        print(f"\n=== 链路完成: {has_done} ===")