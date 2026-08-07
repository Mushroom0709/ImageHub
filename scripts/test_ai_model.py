#!/usr/bin/env python3
"""
T00-02: AI 模型连通性验证（Qwen3.6-27B）
验证：1) 文本对话 2) 结构化JSON输出 3) 多模态(图片) 4) 打标prompt初测
"""
import sys
import json
import requests

API_BASE = "http://27.18.114.8:10203/v1"
API_KEY = "a1bbbc249fba8e2a3bbf04458224bbefbd26e4787e1bf3671edc3857f9d99c6c"
MODEL = "/model"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_chat():
    """测试 1: 基本文本对话"""
    print("\n[1/4] 基本文本对话测试...")
    try:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "你好，请用一句话介绍你自己。"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        resp = requests.post(f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"✅ 文本对话成功")
            print(f"   回复: {content[:80]}...")
            return True
        else:
            print(f"❌ 请求失败, status={resp.status_code}, body={resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def test_structured_output():
    """测试 2: 结构化 JSON 输出"""
    print("\n[2/4] 结构化 JSON 输出测试...")
    try:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是一个图片标签助手。请用 JSON 格式返回标签。输出格式: {\"tags\": [{\"name\": \"标签名\", \"category\": \"scene|style|clothing|makeup|pose_type|composition|mood|body_focus|info\", \"confidence\": 0.0-1.0}]}"},
                {"role": "user", "content": "描述一张在草原上穿白色连衣裙的女生的照片，给 5 个标签。"}
            ],
            "max_tokens": 500,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            try:
                result = json.loads(content)
                print(f"✅ 结构化 JSON 输出成功")
                print(f"   解析出 {len(result.get('tags', []))} 个标签")
                for tag in result.get("tags", [])[:3]:
                    print(f"   - {tag.get('name', '?')} ({tag.get('category', '?')}, {tag.get('confidence', '?')})")
                return True
            except json.JSONDecodeError:
                print(f"⚠️  返回非 JSON: {content[:100]}...")
                return False
        else:
            print(f"❌ 请求失败, status={resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def test_multimodal():
    """测试 3: 多模态（图片输入）"""
    print("\n[3/4] 多模态图片输入测试...")
    try:
        # 用一张 base64 的小图测试（简单的 1x1 红色像素）
        # 先测接口是否支持多模态
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图里有什么？用一句话回答。"},
                        {"type": "image_url", "image_url": {"url": "https://picsum.photos/100/100"}}
                    ]
                }
            ],
            "max_tokens": 100,
            "temperature": 0.3
        }
        resp = requests.post(f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"✅ 多模态调用成功")
            print(f"   回复: {content[:80]}...")
            return True
        else:
            print(f"⚠️  多模态请求失败, status={resp.status_code}, body={resp.text[:200]}")
            print("   可能模型不支持多模态，后续用其他方式处理图片打标")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def test_tagging_prompt():
    """测试 4: 打标 prompt 初版效果"""
    print("\n[4/4] 打标 Prompt v1 测试...")
    prompt = """你是专业的人像摄影标签师。请分析这张照片，从以下 9 个维度给出标签：

1. scene 场景（城市街拍/自然风光/人文建筑/室内场景/特殊场景）
2. style 风格（性感/可爱/俏皮/甜美/酷飒/清冷/优雅/名媛/复古/文艺/...）
3. clothing 服装（上装/下装/鞋履/袜饰/配饰/材质/颜色）
4. makeup 妆容（裸妆/淡妆/纯欲/甜酷/氛围感/...）
5. pose_type 姿势类型（站姿/坐姿/蹲姿/侧身/背影/回头/...）
6. composition 构图（全身/半身/特写/俯拍/仰拍/三分法/...）
7. mood 色调氛围（日系清新/胶片感/复古港风/暗调情绪/...）
8. body_focus 身材修饰点（显腿长/显脸小/显瘦/锁骨/直角肩/...）
9. info 信息（不需要你输出）

请严格用 JSON 输出，格式:
{"tags": [{"name": "标签名", "category": "scene|style|clothing|makeup|pose_type|composition|mood|body_focus", "confidence": 0.0-1.0}]}

只输出 JSON，不要其他文字。每个维度给出 1-3 个最合适的标签，总共不超过 15 个标签。"""

    try:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "图片描述：一个年轻女生穿着白色吊带连衣裙，站在草原上，蓝天白云背景，侧着脸看远方，风吹起头发，色调清新自然。"}
            ],
            "max_tokens": 800,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            tags = result.get("tags", [])
            print(f"✅ 打标 Prompt v1 测试成功")
            print(f"   共 {len(tags)} 个标签:")
            for tag in tags:
                print(f"   - [{tag.get('category', '?'):12s}] {tag.get('name', '?'):15s} (conf: {tag.get('confidence', 0):.2f})")
            return True
        else:
            print(f"❌ 请求失败, status={resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    print("=" * 60)
    print("AI 模型连通性验证（Qwen3.6-27B）")
    print(f"API: {API_BASE}")
    print(f"模型: {MODEL}")
    print("=" * 60)

    results = []
    results.append(("文本对话", test_chat()))
    results.append(("结构化输出", test_structured_output()))
    results.append(("多模态", test_multimodal()))
    results.append(("打标Prompt", test_tagging_prompt()))

    print("\n" + "=" * 60)
    print("测试总结:")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    print(f"\n通过: {passed}/{len(results)}")
    
    if passed >= 3:
        print("🎉 核心能力验证通过！")
        sys.exit(0)
    else:
        print("⚠️  部分测试未通过，需要关注")
        sys.exit(1)

if __name__ == "__main__":
    main()
