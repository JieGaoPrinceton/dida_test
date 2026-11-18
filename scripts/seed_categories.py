"""Seed the categories table with a default taxonomy."""

import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, ".")

from src.config import settings
from src.db.database import Base
from src.db.models import Category

CATEGORY_TREE = [
    {
        "name": "账户问题",
        "description": "Account-related issues",
        "keywords": ["账户", "账号", "登录", "密码", "注册", "account", "login", "password"],
        "children": [
            {"name": "登录问题", "keywords": ["登录", "登入", "无法登录", "login", "sign in"]},
            {"name": "密码重置", "keywords": ["密码", "重置", "忘记密码", "password", "reset"]},
            {"name": "账户安全", "keywords": ["安全", "被盗", "异常", "security", "hack"]},
        ],
    },
    {
        "name": "订单问题",
        "description": "Order-related issues",
        "keywords": ["订单", "购买", "支付", "order", "purchase", "payment"],
        "children": [
            {"name": "订单查询", "keywords": ["查询", "状态", "跟踪", "query", "status", "track"]},
            {"name": "退款退货", "keywords": ["退款", "退货", "退回", "refund", "return"]},
            {"name": "物流配送", "keywords": ["物流", "配送", "快递", "运输", "shipping", "delivery"]},
        ],
    },
    {
        "name": "产品咨询",
        "description": "Product inquiries",
        "keywords": ["产品", "功能", "价格", "product", "feature", "price"],
        "children": [
            {"name": "功能使用", "keywords": ["功能", "使用", "操作", "怎么用", "how to", "feature"]},
            {"name": "价格咨询", "keywords": ["价格", "费用", "收费", "套餐", "price", "cost", "plan"]},
            {"name": "产品对比", "keywords": ["对比", "区别", "差异", "比较", "compare", "difference"]},
        ],
    },
    {
        "name": "技术支持",
        "description": "Technical support",
        "keywords": ["技术", "bug", "故障", "错误", "API", "technical", "error"],
        "children": [
            {"name": "Bug报告", "keywords": ["bug", "缺陷", "问题", "报错", "error", "crash"]},
            {"name": "系统故障", "keywords": ["故障", "宕机", "不可用", "outage", "down", "unavailable"]},
            {"name": "API集成", "keywords": ["API", "接口", "集成", "对接", "integration", "endpoint"]},
        ],
    },
    {
        "name": "投诉建议",
        "description": "Complaints and suggestions",
        "keywords": ["投诉", "建议", "不满", "改进", "complaint", "suggestion", "feedback"],
        "children": [
            {"name": "服务投诉", "keywords": ["投诉", "不满", "差评", "complaint", "poor service"]},
            {"name": "改进建议", "keywords": ["建议", "改进", "希望", "suggestion", "improvement"]},
        ],
    },
]


def seed(db: Session):
    existing = db.query(Category).count()
    if existing > 0:
        print(f"Categories table already has {existing} rows. Skipping seed.")
        return

    for top_cat in CATEGORY_TREE:
        parent = Category(
            name=top_cat["name"],
            description=top_cat.get("description"),
            keywords=top_cat.get("keywords"),
            level=0,
        )
        db.add(parent)
        db.flush()

        for child in top_cat.get("children", []):
            sub = Category(
                name=child["name"],
                parent_id=parent.id,
                keywords=child.get("keywords"),
                level=1,
            )
            db.add(sub)

    db.commit()
    total = db.query(Category).count()
    print(f"Seeded {total} categories.")


def main():
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed(db)

    engine.dispose()
    print("Done.")


if __name__ == "__main__":
    main()
