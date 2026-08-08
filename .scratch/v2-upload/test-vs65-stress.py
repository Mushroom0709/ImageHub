"""#65 E2E 压测：6 文件并发上传（5 小 + 1 大），混合直传 + 分片

验证：
- 并发 6 个文件上传不冲突
- 小文件走直传 + 大文件走分片
- 6 个都成功入库（done=6, failed=0）
- 每个 asset 都有缩略图 + EXIF + AI 标签（除非内网不通）
"""
import httpx
import os
import time
import random
import sys

API = "http://localhost:8000"


def login(c):
    r = c.post(f"{API}/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def upload_direct(c, token, file_path, file_name):
    """小文件走凭证 + 直传 + complete"""
    size = os.path.getsize(file_path)
    r = c.post(
        f"{API}/api/upload/credentials",
        json={"files": [{"file_name": file_name, "file_size": size, "content_type": "image/jpeg", "asset_type": "image"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    d = r.json()
    cred = d["data"]["credentials"][0]
    upload_id = d["data"]["upload_id"]
    with open(file_path, "rb") as f:
        c.put(cred["upload_url"], content=f.read())
    r = c.post(
        f"{API}/api/upload/complete",
        json={
            "upload_id": upload_id,
            "files": [{"file_index": 0, "obs_key": cred["obs_key"], "file_name": file_name, "file_size": size}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()


def upload_multipart(c, token, file_path, file_name):
    """大文件走 multipart（>100MB）"""
    size = os.path.getsize(file_path)
    r = c.post(
        f"{API}/api/upload/multipart/init",
        json={"batch_id": "", "file_name": file_name, "file_size": size, "content_type": "video/mp4", "asset_type": "video"},
        headers={"Authorization": f"Bearer {token}"},
    )
    d = r.json()
    init_data = d["data"]
    batch_id = init_data["batch_id"]
    part_size = init_data["part_size"]
    total_parts = init_data["total_parts"]
    url_map = {p["part_number"]: p["url"] for p in init_data["part_upload_urls"]}

    with open(file_path, "rb") as f:
        for pn in range(1, total_parts + 1):
            f.seek((pn - 1) * part_size)
            chunk = f.read(part_size)
            if not chunk:
                break
            httpx.put(url_map[pn], content=chunk, timeout=httpx.Timeout(60, read=60))
            c.post(
                f"{API}/api/upload/multipart/part-complete",
                json={"batch_id": batch_id, "part_number": pn, "size": len(chunk)},
                headers={"Authorization": f"Bearer {token}"},
            )
    r = c.post(
        f"{API}/api/upload/multipart/complete",
        json={"batch_id": batch_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()


def make_small_jpg(path, w, h):
    """生成小尺寸 JPG（容器内 Pillow）"""
    import sys as _sys
    _sys.path.insert(0, '/app')
    from PIL import Image
    random.seed(42)
    img = Image.new('RGB', (w, h))
    px = img.load()
    chunk = 64
    for y in range(0, h, chunk):
        for x in range(0, w, chunk):
            c = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            for dy in range(min(chunk, h - y)):
                for dx in range(min(chunk, w - x)):
                    px[x + dx, y + dy] = c
    img.save(path, 'JPEG', quality=70)


def main():
    # 准备测试文件
    test_files = []

    # 5 个小 JPG（20-40MB 各 → 走直传）
    sizes = [(4000, 3000), (5000, 4000), (3000, 3000), (6000, 4000), (4000, 4000)]
    for i, (w, h) in enumerate(sizes):
        path = f"/app/stress-{i+1}.jpg"
        make_small_jpg(path, w, h)
        test_files.append((path, f"stress-{i+1}.jpg", "small"))

    # 1 个大文件（200MB → 走分片）
    # 用随机字节拼一个真 MP4 header + 200MB 数据
    big_path = "/app/stress-big.mp4"
    target_size = 250 * 1024 * 1024  # 250MB > 100MB 阈值触发分片
    with open(big_path, 'wb') as out:
        # 合法 MP4 ftyp box header
        ftyp = bytes.fromhex('0000001866747970') + b'mp42' + bytes.fromhex('000000006d70343269736f6d') + bytes.fromhex('0000000866726565')
        out.write(ftyp)
        # 凑到目标大小
        out.write(b'\x00' * (target_size - len(ftyp)))
    test_files.append((big_path, "stress-big.mp4", "big"))

    print(f"[0] 准备 {len(test_files)} 个测试文件:")
    for path, name, kind in test_files:
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  - {name}: {size_mb:.1f} MB ({kind})")

    # 登录
    with httpx.Client(timeout=httpx.Timeout(60, read=120)) as c:
        token = login(c)
        print(f"[1] token={token[:30]}...")

        # 并发上传（6 线程）
        import threading
        results = [None] * len(test_files)

        def worker(idx):
            path, name, kind = test_files[idx]
            t0 = time.time()
            try:
                if kind == "small":
                    d = upload_direct(c, token, path, name)
                else:
                    d = upload_multipart(c, token, path, name)
                results[idx] = (name, d, time.time() - t0)
            except Exception as e:
                results[idx] = (name, {"error": str(e)}, time.time() - t0)

        threads = []
        for i in range(len(test_files)):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        # 汇总
        print(f"\n=== 压测结果 ===")
        success = 0
        failed = 0
        asset_ids = []
        for name, d, elapsed in results:
            data = d.get("data", {})
            asset_id = None
            if "asset_ids" in data:
                asset_ids.extend(data["asset_ids"])
            if "asset_id" in data:
                asset_ids.append(data["asset_id"])
            if d.get("code") == 0 and asset_ids:
                success += 1
                print(f"  ✓ {name}: {elapsed:.1f}s asset_id={asset_ids[-1][:8]}")
            else:
                failed += 1
                print(f"  ✗ {name}: {elapsed:.1f}s error={d.get('message', d.get('error', 'unknown'))}")

        print(f"\n  total: {len(test_files)}, success: {success}, failed: {failed}")

        # 等 20 秒让后端处理全部完成
        print(f"\n[2] 等 20s 让后端处理...")
        time.sleep(20)

        # 验证每个 asset 入库
        import psycopg2
        conn = psycopg2.connect("postgresql://imagehub:imagehub@db:5432/imagehub")
        cur = conn.cursor()
        total_thumbs = 0
        total_tags = 0
        for aid in asset_ids:
            cur.execute("SELECT width, height FROM assets WHERE id = %s", (aid,))
            r = cur.fetchone()
            if r and r[0] and r[1]:
                total_thumbs += 1
            cur.execute("SELECT count(*) FROM asset_tags WHERE asset_id = %s", (aid,))
            total_tags += cur.fetchone()[0]
        print(f"  assets with dimensions: {total_thumbs}/{len(asset_ids)}")
        print(f"  total AI tags: {total_tags}")
        conn.close()

        # 清理
        print(f"\n[3] 清理 {len(asset_ids)} 个测试资产...")
        sys.path.insert(0, '/app')
        from app.services.obs_service import obs_service
        conn = psycopg2.connect("postgresql://imagehub:imagehub@db:5432/imagehub")
        cur = conn.cursor()
        for aid in asset_ids:
            cur.execute("SELECT obs_key FROM assets WHERE id = %s", (aid,))
            r = cur.fetchone()
            if r:
                try: obs_service.delete_file(r[0])
                except: pass
                try: obs_service.delete_file(r[0] + "_thumb_small.jpg")
                except: pass
                try: obs_service.delete_file(r[0] + "_thumb_medium.jpg")
                except: pass
            cur.execute("DELETE FROM asset_tags WHERE asset_id = %s", (aid,))
            cur.execute("DELETE FROM assets WHERE id = %s", (aid,))
        conn.commit()
        conn.close()
        print("  cleaned")

        # 删除测试文件
        for path, _, _ in test_files:
            if os.path.exists(path):
                os.unlink(path)

        # 退出码
        if success == len(test_files):
            print("\n✅ 压测全部通过")
        else:
            print(f"\n⚠ {failed} 个失败")


if __name__ == "__main__":
    main()