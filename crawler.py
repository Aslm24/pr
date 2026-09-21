import asyncio
import logging

import aiohttp

import config

logger = logging.getLogger(__name__)

GITHUB_SEARCH_API = "https://api.github.com/search/code"


def _guess_protocol(url: str) -> str:
    lowered = url.lower()
    if "socks5" in lowered:
        return "socks5"
    if "socks4" in lowered:
        return "socks4"
    if "https" in lowered:
        return "https"
    return "http"


async def _search_github(session: aiohttp.ClientSession, query: str) -> list[str]:
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    urls = []
    try:
        async with session.get(
            GITHUB_SEARCH_API,
            params={"q": query, "per_page": 10},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            for item in data.get("items", []):
                repo = item.get("repository", {}).get("full_name")
                path = item.get("path")
                if repo and path:
                    for branch in ("main", "master"):
                        urls.append(f"https://raw.githubusercontent.com/{repo}/{branch}/{path}")
    except Exception as e:
        logger.warning(f"فشل بحث GitHub عن {query}: {e}")
    return urls


async def discover_sources() -> dict[str, set[str]]:
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_search_github(session, q) for q in config.GITHUB_SEARCH_QUERIES])

    discovered: dict[str, set[str]] = {}
    for urls in results:
        for url in urls:
            protocol = _guess_protocol(url)
            discovered.setdefault(protocol, set()).add(url)

    total = sum(len(v) for v in discovered.values())
    logger.info(f"الزاحف الذكي اكتشف {total} مصدر جديد محتمل")
    return discovered
