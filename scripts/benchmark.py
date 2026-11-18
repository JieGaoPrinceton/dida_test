"""Benchmark search performance with synthetic data."""

import argparse
import asyncio
import random
import statistics
import sys
import time

sys.path.insert(0, ".")

from src.config import settings
from src.services.es_service import bulk_index_emails, es_client, ensure_indices

SUBJECTS_ZH = [
    "关于订单退款的问题", "无法登录账户", "产品功能咨询", "物流配送延迟",
    "密码重置请求", "API接口报错", "系统故障通知", "价格方案咨询",
    "服务投诉反馈", "账户安全问题", "订单状态查询", "退货流程说明",
]
SUBJECTS_EN = [
    "Order refund inquiry", "Cannot login to account", "Product feature question",
    "Shipping delay issue", "Password reset request", "API integration error",
    "System outage report", "Pricing plan inquiry", "Service complaint",
    "Account security concern", "Order status check", "Return process info",
]
BODIES_ZH = [
    "您好，我想咨询一下关于退款的流程。我在上周购买了一件商品，但是收到后发现有质量问题。",
    "我的账户无法登录，输入密码后提示错误。我已经尝试了多次，但都没有成功。",
    "请问你们的产品支持哪些功能？我正在考虑购买，想了解更多细节。",
    "我的快递已经显示发货一周了，但是至今还没有收到。请帮忙查询一下物流信息。",
    "我忘记了登录密码，请帮我重置。我的注册邮箱是example@test.com。",
    "调用API接口时返回500错误，请求参数如下：...",
    "系统从今天上午10点开始出现访问缓慢的情况，部分页面无法加载。",
]
BODIES_EN = [
    "Hi, I would like to inquire about the refund process. I purchased an item last week but found quality issues.",
    "My account cannot be logged in. After entering the password, it shows an error. I have tried multiple times.",
    "What features does your product support? I am considering purchasing and want to know more details.",
    "My delivery has shown shipped for a week but I still haven't received it. Please check the logistics.",
    "I forgot my login password, please help me reset it. My registered email is example@test.com.",
]
CATEGORIES = ["账户问题", "订单问题", "产品咨询", "技术支持", "投诉建议"]
QUERIES = [
    "退款流程", "无法登录", "产品功能", "物流查询", "密码重置",
    "API报错", "系统故障", "价格", "投诉", "账户安全",
    "refund process", "cannot login", "product features", "shipping status",
    "how to reset password", "API error 500",
]


def generate_emails(n: int) -> list[dict]:
    emails = []
    for i in range(n):
        is_zh = random.random() < 0.6
        subject = random.choice(SUBJECTS_ZH if is_zh else SUBJECTS_EN)
        body = random.choice(BODIES_ZH if is_zh else BODIES_EN)
        emails.append({
            "email_id": i + 1,
            "subject": subject,
            "body_text": body,
            "sender": f"user{i}@example.com",
            "category": random.choice(CATEGORIES),
            "tags": random.sample(["urgent", "vip", "follow-up", "resolved"], k=random.randint(0, 2)),
            "sent_at": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T10:00:00Z",
            "language": "zh" if is_zh else "en",
            "quality_score": round(random.uniform(0.5, 1.0), 2),
        })
    return emails


async def run_benchmark(num_emails: int, num_queries: int):
    print(f"=== Email KB Search Benchmark ===\n")

    await ensure_indices()

    # Index emails
    print(f"Generating {num_emails} sample emails...")
    emails = generate_emails(num_emails)

    print(f"Indexing {num_emails} emails to Elasticsearch...")
    batch_size = settings.ingest_batch_size
    t0 = time.perf_counter()
    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        await bulk_index_emails(batch)
    index_time = time.perf_counter() - t0
    print(f"  Indexed in {index_time:.2f}s ({num_emails / index_time:.0f} docs/sec)\n")

    # Wait for refresh
    await es_client.indices.refresh(index=settings.es_email_index)

    # Run queries
    print(f"Running {num_queries} search queries...")
    from src.services.es_service import search_emails_bm25

    latencies = []
    for _ in range(num_queries):
        query = random.choice(QUERIES)
        category = random.choice([None, None, random.choice(CATEGORIES)])

        t0 = time.perf_counter()
        results = await search_emails_bm25(query, category=category, top_n=10)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

    # Stats
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\n=== Results ({num_queries} queries) ===")
    print(f"  Mean:  {statistics.mean(latencies):.1f} ms")
    print(f"  P50:   {p50:.1f} ms")
    print(f"  P95:   {p95:.1f} ms")
    print(f"  P99:   {p99:.1f} ms")
    print(f"  Min:   {min(latencies):.1f} ms")
    print(f"  Max:   {max(latencies):.1f} ms")

    target_p99 = 500
    status = "PASS" if p99 < target_p99 else "FAIL"
    print(f"\n  P99 target (<{target_p99}ms): {status}")

    await es_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark search performance")
    parser.add_argument("--emails", type=int, default=1000, help="Number of emails to generate")
    parser.add_argument("--queries", type=int, default=100, help="Number of queries to run")
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.emails, args.queries))
