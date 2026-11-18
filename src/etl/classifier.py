import re

CATEGORY_RULES: dict[str, dict[str, list[str]]] = {
    "billing": {
        "keywords": ["invoice", "payment", "refund", "charge", "billing", "price",
                      "账单", "付款", "退款", "收费", "费用", "发票"],
        "subcategories": {
            "refund": ["refund", "money back", "退款", "退费"],
            "payment": ["payment", "pay", "付款", "支付"],
            "invoice": ["invoice", "receipt", "发票", "收据"],
        },
    },
    "technical": {
        "keywords": ["error", "bug", "crash", "not working", "issue", "problem", "fail",
                      "错误", "故障", "崩溃", "无法", "问题", "失败", "报错"],
        "subcategories": {
            "bug": ["bug", "defect", "缺陷"],
            "performance": ["slow", "latency", "timeout", "慢", "延迟", "超时"],
            "integration": ["api", "integration", "webhook", "集成", "接口"],
        },
    },
    "account": {
        "keywords": ["login", "password", "account", "register", "signup", "access",
                      "登录", "密码", "账号", "注册", "权限", "账户"],
        "subcategories": {
            "access": ["login", "password", "reset", "登录", "密码", "重置"],
            "settings": ["settings", "profile", "preference", "设置", "配置"],
        },
    },
    "product": {
        "keywords": ["feature", "request", "suggest", "new", "update", "upgrade",
                      "功能", "需求", "建议", "新增", "更新", "升级"],
        "subcategories": {
            "feature_request": ["feature request", "suggest", "功能需求", "建议"],
            "usage": ["how to", "tutorial", "guide", "如何", "教程", "指南"],
        },
    },
    "shipping": {
        "keywords": ["shipping", "delivery", "track", "order", "package",
                      "物流", "快递", "配送", "订单", "包裹", "发货"],
        "subcategories": {
            "tracking": ["track", "where", "status", "追踪", "状态"],
            "delay": ["delay", "late", "slow", "延迟", "迟"],
        },
    },
}

PRODUCT_PATTERNS = [
    r"\b(?:v|version)\s*\d+[\.\d]*",
    r"\b[A-Z][a-zA-Z]*(?:Pro|Plus|Enterprise|Basic|Premium)\b",
]


def classify_email(subject: str, body: str) -> tuple[str | None, str | None]:
    text = f"{subject} {body}".lower()
    best_category = None
    best_score = 0

    for category, rules in CATEGORY_RULES.items():
        score = sum(1 for kw in rules["keywords"] if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_category = category

    if not best_category or best_score == 0:
        return None, None

    best_subcategory = None
    best_sub_score = 0
    for subcat, keywords in CATEGORY_RULES[best_category].get("subcategories", {}).items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_sub_score:
            best_sub_score = score
            best_subcategory = subcat

    return best_category, best_subcategory


def extract_tags(subject: str, body: str) -> list[str]:
    text = f"{subject} {body}"
    tags = set()

    for category, rules in CATEGORY_RULES.items():
        for kw in rules["keywords"]:
            if kw.lower() in text.lower():
                tags.add(category)
                break

    for pattern in PRODUCT_PATTERNS:
        matches = re.findall(pattern, text)
        tags.update(matches)

    return sorted(tags)
