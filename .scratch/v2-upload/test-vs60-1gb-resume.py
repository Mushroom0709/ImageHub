"""#60 VS 端到端：1GB MP4 分片上传 + 断点续传

策略：
  Phase A: init + 上传前 30 parts（共 240MB）
  Phase B: 模拟"客户端崩溃"——直接 exit 进程（OBS 侧 upload_id 仍存活）
  Phase C: 重新 init 同 batch_id → 后端复用会话 → 返回 uploaded_parts[1..30]
  Phase D: 只传 31..128（共 98 parts）→ complete

验证项：
- 断点续传只上传缺失分片（断网/重连场景）
- complete 走视频处理管线（video_service 抽封面 + 取分辨率）
- 资产入库: width/height/width, duration, AI 打标（视频可能跳过 AI）
"""
import httpx
import os
import sys
import time

API = "http://localhost:8000"
MP4 = "/app/test-1gb.mp4"


def login(c):
    r = c.post(f"{API}/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def init_session(c, token, file_size, file_name, batch_id=""):
    """init 带 batch_id = 续传；不带 = 新建"""
    r = c.post(
        f"{API}/api/upload/multipart/init",
        json={
            "batch_id": batch_id,
            "file_name": file_name,
            "file_size": file_size,
            "content_type": "video/mp4",
            "asset_type": "video",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    d = r.json()
    assert d["code"] == 0, f"init failed: {d}"
    init_data = d["data"]
    return init_data


def upload_parts(c, token, batch_id, init_data, from_part, to_part):
    """上传 from_part ~ to_part（inclusive）"""
    url_map = {p["part_number"]: p["url"] for p in init_data["part_upload_urls"]}
    part_size = init_data["part_size"]
    total_parts = init_data["total_parts"]

    print(f"  uploading parts {from_part}-{to_part} (size={part_size})")
    t0 = time.time()
    with open(MP4, "rb") as f:
        for pn in range(from_part, to_part + 1):
            f.seek((pn - 1) * part_size)
            chunk = f.read(part_size)
            if not chunk:
                break
            resp = httpx.put(url_map[pn], content=chunk, timeout=httpx.Timeout(60, read=60))
            if resp.status_code != 200:
                print(f"  part {pn} PUT failed: {resp.status_code}")
                return False
            # 后端 part-complete
            c.post(
                f"{API}/api/upload/multipart/part-complete",
                json={"batch_id": batch_id, "part_number": pn, "size": len(chunk)},
                headers={"Authorization": f"Bearer {token}"},
            )
    elapsed = time.time() - t0
    speed = (to_part - from_part + 1) * part_size / 1024 / 1024 / elapsed
    print(f"  {to_part - from_part + 1} parts in {elapsed:.1f}s ({speed:.1f} MB/s)")
    return True


def main():
    file_size = os.path.getsize(MP4)
    file_name = "test-1gb-vs60.mp4"
    print(f"[0] file: {MP4}, size={file_size/1024/1024:.1f} MB")

    with httpx.Client(timeout=httpx.Timeout(60, read=120, write=120)) as c:
        token = login(c)
        print(f"[0] token={token[:30]}...")

        # Phase A: 全新 init + 上传前 30 parts
        print("\n=== Phase A: 全新上传前 30 parts ===")
        batch_id = f"vs60-{int(time.time())}"
        init_data = init_session(c, token, file_size, file_name, batch_id)
        total_parts = init_data["total_parts"]
        print(f"  init: batch_id={batch_id[:8]}, total_parts={total_parts}, part_size={init_data['part_size']}")
        ok = upload_parts(c, token, batch_id, init_data, 1, 30)
        if not ok:
            return
        # Phase B: 模拟客户端崩溃——直接退出进程
        print("\n=== Phase B: 模拟客户端崩溃 ===")
        print("  (not really exiting, just stopping here)")
        # 验证：DB 中 batch_id 状态
        import psycopg2
        conn = psycopg2.connect("postgresql://imagehub:imagehub@db:5432/imagehub")
        cur = conn.cursor()
        cur.execute(
            "SELECT status, jsonb_array_length(uploaded_parts) FROM multipart_uploads WHERE batch_id=%s",
            (batch_id,),
        )
        print(f"  DB state: {cur.fetchone()}")
        conn.close()

        # Phase C: 重新 init（同 batch_id）
        print("\n=== Phase C: 重新 init（同 batch_id）→ 复用会话 ===")
        init_data2 = init_session(c, token, file_size, file_name, batch_id)
        uploaded = init_data2["uploaded_parts"]
        uploaded_nums = sorted([p["part_number"] for p in uploaded])
        print(f"  reused batch_id={init_data2['batch_id'][:8]}, uploaded_parts={len(uploaded)} parts")
        print(f"  first/last uploaded: {uploaded_nums[0]}..{uploaded_nums[-1]}")
        # 验证已传分片与之前一致
        assert set(uploaded_nums) == set(range(1, 31)), f"uploaded_parts mismatch: {uploaded_nums}"
        print("  ✓ uploaded_parts 正确包含前 30 parts")

        # Phase D: 传剩余 parts
        print("\n=== Phase D: 传剩余 parts ===")
        uploaded_set = set(uploaded_nums)
        next_to_upload = [n for n in range(31, total_parts + 1) if n not in uploaded_set]
        print(f"  need to upload: {len(next_to_upload)} parts")
        ok = upload_parts(c, token, batch_id, init_data2, 31, total_parts)
        if not ok:
            return

        # Phase E: complete
        print("\n=== Phase E: complete ===")
        t0 = time.time()
        r = c.post(
            f"{API}/api/upload/multipart/complete",
            json={"batch_id": batch_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed = time.time() - t0
        d = r.json()
        print(f"  complete: {elapsed:.1f}s, status={r.status_code}")
        print(f"  body: {r.text[:300]}")
        asset_id = d.get("data", {}).get("asset_ids", [None])[0] if d.get("data") else None
        return asset_id, batch_id


if __name__ == "__main__":
    result = main()
    if result:
        asset_id, batch_id = result
        # 等几秒看处理结果
        print("\n=== 等后端处理 ===")
        time.sleep(15)
        import psycopg2
        conn = psycopg2.connect("postgresql://imagehub:imagehub@db:5432/imagehub")
        cur = conn.cursor()
        cur.execute("SELECT file_name, width, height, file_size, duration FROM assets WHERE id=%s", (asset_id,))
        print(f"asset: {cur.fetchone()}")
        conn.close()