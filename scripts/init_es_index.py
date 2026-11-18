"""Initialize Elasticsearch indices with proper mappings."""

import argparse
import asyncio
import sys

from elasticsearch import AsyncElasticsearch

sys.path.insert(0, ".")

from src.config import settings
from src.services.es_service import EMAIL_INDEX_SETTINGS, KNOWLEDGE_INDEX_SETTINGS


async def main(force: bool = False):
    es = AsyncElasticsearch(hosts=settings.es_hosts)

    indices = {
        settings.es_email_index: EMAIL_INDEX_SETTINGS,
        settings.es_knowledge_index: KNOWLEDGE_INDEX_SETTINGS,
    }

    try:
        for index_name, index_settings in indices.items():
            exists = await es.indices.exists(index=index_name)

            if exists and force:
                print(f"Deleting existing index: {index_name}")
                await es.indices.delete(index=index_name)
                exists = False

            if exists:
                print(f"Index already exists: {index_name} (use --force to recreate)")
            else:
                print(f"Creating index: {index_name}")
                await es.indices.create(index=index_name, body=index_settings)
                print(f"  Created with {index_settings['settings']['number_of_shards']} shards")

        info = await es.info()
        print(f"\nES cluster: {info['cluster_name']} (version {info['version']['number']})")

        for index_name in indices:
            stats = await es.indices.stats(index=index_name)
            doc_count = stats["indices"][index_name]["primaries"]["docs"]["count"]
            print(f"  {index_name}: {doc_count} documents")

    finally:
        await es.close()

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize ES indices")
    parser.add_argument("--force", action="store_true", help="Delete and recreate existing indices")
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
