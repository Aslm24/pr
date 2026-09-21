import asyncio
import logging
import re

import aiohttp

import config

logger = logging.getLogger(__name__)

IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")


async def _fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.text(errors="ignore")
            logger.warning(f"استجابة غير صالحة ({resp.status}) من المصدر: {url}")
    except Exception as e:
        logger.warning(f"فشل جلب المصدر {url}: {e}")
    return ""


def _extract_proxies(text: str) -> set[str]:
    return {f"{m.group(1)}:{m.group(2)}" for m in IP_PORT_RE.finditer(text)}


async def _fetch_source_map(session: aiohttp.ClientSession, source_map: dict[str, list[str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {proto: set() for proto in source_map}
    tasks, mapping = [], []

    for proto, urls in source_map.items():
        for url in urls:
            tasks.append(_fetch_text(session, url))
            mapping.append(proto)

    texts = await asyncio.gather(*tasks)
    for proto, text in zip(mapping, texts):
        result[proto] |= _extract_proxies(text)

    return result


async def _fetch_proxyscrape(session: aiohttp.ClientSession) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    tasks, protos = [], []

    for proto in config.PROXYSCRAPE_PROTOCOLS:
        url = config.PROXYSCRAPE_API.format(proto=proto)
        tasks.append(_fetch_text(session, url))
        protos.append(proto)

    texts = await asyncio.gather(*tasks)
    for proto, text in zip(protos, texts):
        result.setdefault(proto, set())
        result[proto] |= _extract_proxies(text)

    return result


async def scrape_all(extra_sources: dict[str, set[str]] | None = None) -> dict[str, set[str]]:
    source_map: dict[str, list[str]] = {proto: list(urls) for proto, urls in config.PROXY_SOURCES.items()}
    if extra_sources:
        for proto, urls in extra_sources.items():
            merged = set(source_map.get(proto, [])) | set(urls)
            source_map[proto] = list(merged)

    async with aiohttp.ClientSession() as session:
        github_result, proxyscrape_result = await asyncio.gather(
            _fetch_source_map(session, source_map),
            _fetch_proxyscrape(session),
        )

    combined: dict[str, set[str]] = {}
    for source in (github_result, proxyscrape_result):
        for proto, proxies in source.items():
            combined.setdefault(proto, set())
            combined[proto] |= proxies

    total = sum(len(v) for v in combined.values())
    logger.info(f"تم جلب {total} بروكسي بعد إزالة التكرار عبر {len(combined)} تصنيف")
    return combined
