"""#54 SSE 端到端测试：上传→订阅→收到所有阶段事件

策略:
1. 同步: credentials + OBS PUT + complete(异步返回)
2. 异步: 启动 SSE 订阅 (timeout 30s)
3. 期望收到事件序列: connected → uploaded → thumbnail → exif → ai_tagging → done
"""
import httpx
import os
import threading
import time
import sys

API = "http://localhost:8000"
JPG = "/app/test-50mb.jpg"


def login(client):
    r = client.post(f"{API}/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def upload_and_subscribe(token):
    """并行: SSE 在后台线程订阅，主线程先 complete 触发 publisher"""
    file_size = os.path.getsize(JPG)

    with httpx.Client(timeout=httpx.Timeout(30, read=120)) as c:
        # 1. credentials
        r = c.post(
            f"{API}/api/upload/credentials",
            json={"files": [{"file_name": "sse-test.jpg", "file_size": file_size, "content_type": "image/jpeg", "asset_type": "image"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        d = r.json()
        cred = d["data"]["credentials"][0]
        upload_id = d["data"]["upload_id"]

        # 2. PUT
        with open(JPG, "rb") as f:
            c.put(cred["upload_url"], content=f.read())

        # 用一个非 SSE 客户端触发 complete
        c2 = httpx.Client(timeout=httpx.Timeout(30, read=120))
        r = c2.post(
            f"{API}/api/upload/complete",
            json={
                "upload_id": upload_id,
                "files": [{"file_index": 0, "obs_key": cred["obs_key"], "file_name": "sse-test.jpg", "file_size": file_size}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        d = r.json()
        asset_id = d["data"]["asset_ids"][0]
        async_flag = d["data"].get("async_processing")
        print(f"[complete] asset_id={asset_id[:8]}..., async_processing={async_flag}")

        # 3. 订阅 SSE（事件已 publish，需要从缓存拿）
        print("[subscribe] opening SSE stream (should get cached events)...")
        events = []
        # 60s 超时，等 background task 全部跑完
        with c.stream("GET", f"{API}/api/upload/events/{asset_id}", timeout=60) as resp:
            print(f"[subscribe] HTTP {resp.status_code}, headers={dict(resp.headers)}")
            raw = []
            for chunk in resp.iter_bytes():
                raw.append(chunk)
                print(f"  [raw chunk {len(chunk)}b]: {chunk[:200]!r}")
            print(f"[subscribe] total raw bytes: {sum(len(r) for r in raw)}")
            # 重新解析
            data = b"".join(raw).decode("utf-8", errors="replace")
            print(f"[subscribe] full data:\n{data}")
            print(f"[subscribe] closed, total {len(events)} events")

        c2.close()
        return asset_id, events


if __name__ == "__main__":
    with httpx.Client(timeout=httpx.Timeout(30, read=120)) as c:
        token = login(c)
        asset_id, events = upload_and_subscribe(token)
        print(f"\n=== 收到 {len(events)} 个事件 ===")
        for e in events:
            print(f"  {e[:140]}")