"""标签服务"""
from sqlalchemy.orm import Session
from app.models.tag import Tag
from app.data.seed_tags import SEED_TAGS


def seed_tags(db: Session) -> int:
    """导入种子标签，返回新增数量"""
    count = 0
    # 先建父级标签，再建子级
    parent_map = {}  # name -> tag_id

    # 先处理所有父级（parent_name 为 None 的）
    for name, category, parent_name, alias, sort_order in SEED_TAGS:
        if parent_name is None:
            tag = db.query(Tag).filter(Tag.name == name, Tag.category == category).first()
            if not tag:
                tag = Tag(
                    name=name,
                    category=category,
                    parent_id=None,
                    alias=alias or [],
                    sort_order=sort_order,
                    status="active",
                )
                db.add(tag)
                count += 1
            parent_map[name] = tag

    # 再处理子级
    for name, category, parent_name, alias, sort_order in SEED_TAGS:
        if parent_name is not None:
            parent = parent_map.get(parent_name)
            if not parent:
                continue
            tag = db.query(Tag).filter(Tag.name == name, Tag.category == category).first()
            if not tag:
                tag = Tag(
                    name=name,
                    category=category,
                    parent_id=parent.id,
                    alias=alias or [],
                    sort_order=sort_order,
                    status="active",
                )
                db.add(tag)
                count += 1

    db.commit()
    return count
