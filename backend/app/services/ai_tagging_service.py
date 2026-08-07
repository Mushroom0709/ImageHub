"""AI 打标服务"""
import json
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tag import Tag, AssetTag

# 9 大分类定义（prompt 用）
CATEGORIES = [
    "scene 场景（城市街拍/自然风光/人文建筑/室内场景/特殊场景）",
    "style 风格（性感/可爱/俏皮/甜美/酷飒/清冷/优雅/名媛/复古/文艺/街头/学院/民族风/国潮/洛丽塔）",
    "clothing 服装（上装/下装/鞋履/袜饰/配饰/特殊服饰，如短裙/长裙/超短裙/高跟鞋/白丝/黑丝）",
    "makeup 妆容（裸妆/淡妆/浓妆/烟熏妆/纯欲妆/甜酷妆/氛围感妆/白开水妆/古风妆/民族妆/泰式妆/日系妆/韩系妆）",
    "pose_type 姿势类型（站姿/坐姿/蹲姿/躺姿/侧身/背影/回头杀/跳姿/走路，手部动作如插兜/托腮/撩头发/叉腰）",
    "composition 构图（全身照/半身照/特写/俯拍/仰拍/居中构图/三分法构图/框架构图/引导线构图）",
    "mood 色调氛围（日系清新/胶片感/复古港风/暗调情绪/逆光/温柔治愈/高级灰调/暖色调/冷色调）",
    "body_focus 身材修饰点（显腿长/显脸小/显瘦/锁骨/直角肩/马甲线/腰臀比/大长腿/背影杀）",
]

PROMPT_TEMPLATE = """你是专业的人像摄影标签师。请分析这张照片，从以下 8 个维度给出标签：

{categories}

要求：
1. 每个维度给出 1-3 个最合适的标签，总共不超过 15 个
2. 只输出 JSON，不要其他文字
3. 如果图片没有明确的信息（如看不清脸），该维度可以省略

输出格式：
{{"tags": [{{"name": "标签名", "category": "scene|style|clothing|makeup|pose_type|composition|mood|body_focus", "confidence": 0.0-1.0}}]}}

参考图片描述（如果有）：
{description}
"""


class AiTaggingService:
    """调用 Qwen 多模态模型给图片打标"""

    def __init__(self):
        self.api_base = settings.AI_API_BASE
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL

    def tag_image(self, image_url: str, description: str = "") -> list[dict]:
        """
        给单张图片打标
        image_url: 图片 URL（OBS 预签名 URL）
        返回: [{"name": ..., "category": ..., "confidence": ...}]
        """
        prompt = PROMPT_TEMPLATE.format(
            categories="\n".join(f"{i+1}. {c}" for i, c in enumerate(CATEGORIES)),
            description=description or "无",
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "max_tokens": 800,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                return result.get("tags", [])
        except Exception as e:
            print(f"[AI打标] 失败: {e}")
            return []

    def apply_tags(self, db: Session, asset_id, tags: list[dict]) -> int:
        """
        把 AI 打标结果写入数据库
        规则：
        - 已有标签（匹配名称或别名）→ 复用
        - 新标签 → 创建（pending 状态）
        - confidence < 0.7 → 素材标记待审核（通过 tag status 体现）
        """
        count = 0
        for tag_data in tags:
            name = tag_data.get("name", "").strip()
            category = tag_data.get("category", "other")
            confidence = float(tag_data.get("confidence", 0.5))

            if not name:
                continue

            # 找已有标签（按名称，不分大小写）
            tag = db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                # 创建新标签（pending 状态，需要审核）
                tag = Tag(
                    name=name,
                    category=category,
                    status="pending",
                )
                db.add(tag)
                db.flush()

            # 关联（幂等）
            existing = db.query(AssetTag).filter(
                AssetTag.asset_id == asset_id,
                AssetTag.tag_id == tag.id,
            ).first()
            if not existing:
                db.add(AssetTag(
                    asset_id=asset_id,
                    tag_id=tag.id,
                    confidence=confidence,
                    source="ai",
                ))
                count += 1

        db.commit()
        return count


ai_tagging_service = AiTaggingService()
