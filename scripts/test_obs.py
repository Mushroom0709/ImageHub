#!/usr/bin/env python3
"""
T00-01: OBS 连通性全流程验证
验证：上传/生成预签名URL/下载/列出/删除 全流程
"""
import sys
import os
import tempfile
from obs import ObsClient

# 配置
AK = "E4PODEJ2KFRXLIBACJG5"
SK = "4G3TvKp0ehqOQPcDPOavWxiCgbid7fAGVxbjUMl5"
ENDPOINT = "obs.cn-central-221.ovaijisuan.com"
BUCKET = "obs-mushroom"
TEST_PREFIX = "ImageHub/test/"

def main():
    print("=" * 60)
    print("OBS 连通性全流程验证")
    print("=" * 60)

    # 1. 初始化客户端
    print("\n[1/6] 初始化 ObsClient...")
    try:
        obs_client = ObsClient(
            access_key_id=AK,
            secret_access_key=SK,
            server=ENDPOINT
        )
        print("✅ ObsClient 初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

    test_file_name = "obs-connectivity-test.txt"
    test_content = "Hello ImageHub! This is an OBS connectivity test file.\n"
    test_key = TEST_PREFIX + test_file_name

    # 2. 上传文件
    print(f"\n[2/6] 上传测试文件到 {test_key} ...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            local_file = f.name
        
        resp = obs_client.putFile(BUCKET, test_key, local_file)
        if resp.status < 300:
            print(f"✅ 上传成功, status={resp.status}")
        else:
            print(f"❌ 上传失败, status={resp.status}, body={resp.body}")
            sys.exit(1)
        os.unlink(local_file)
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        sys.exit(1)

    # 3. 列出对象
    print(f"\n[3/6] 列出 {TEST_PREFIX} 目录...")
    try:
        resp = obs_client.listObjects(BUCKET, prefix=TEST_PREFIX, max_keys=10)
        if resp.status < 300:
            contents = resp.body.contents if hasattr(resp.body, 'contents') else []
            print(f"✅ 列出成功，共 {len(contents)} 个对象")
            for obj in contents[:5]:
                print(f"   - {obj.key} ({obj.size} bytes)")
        else:
            print(f"❌ 列出失败, status={resp.status}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 列出异常: {e}")
        sys.exit(1)

    # 4. 生成预签名 URL
    print(f"\n[4/6] 生成预签名 GET URL...")
    try:
        result = obs_client.createSignedUrl("GET", bucketName=BUCKET, objectKey=test_key, expires=3600)
        signed_url = result["signedUrl"]
        print(f"✅ 预签名 URL 生成成功")
        print(f"   URL (前100字符): {signed_url[:100]}...")
    except Exception as e:
        print(f"❌ 预签名URL异常: {e}")
        sys.exit(1)

    # 5. 下载文件验证内容
    print(f"\n[5/6] 下载文件并验证内容...")
    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            download_path = f.name
        
        resp = obs_client.getObject(BUCKET, test_key, download_path)
        if resp.status < 300:
            with open(download_path, 'r') as f:
                content = f.read()
            if content == test_content:
                print(f"✅ 下载成功，内容一致")
            else:
                print(f"❌ 内容不一致: 期望 '{test_content[:30]}...', 实际 '{content[:30]}...'")
                sys.exit(1)
        else:
            print(f"❌ 下载失败, status={resp.status}")
            sys.exit(1)
        os.unlink(download_path)
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        sys.exit(1)

    # 6. 删除文件
    print(f"\n[6/6] 删除测试文件...")
    try:
        resp = obs_client.deleteObject(BUCKET, test_key)
        if resp.status < 300:
            print(f"✅ 删除成功")
        else:
            print(f"❌ 删除失败, status={resp.status}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 删除异常: {e}")
        sys.exit(1)

    # 关闭客户端
    obs_client.close()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！OBS 连通性验证成功")
    print("=" * 60)

if __name__ == "__main__":
    main()
