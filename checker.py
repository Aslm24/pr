import asyncio
import logging
import time

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType

import config

logger = logging.getLogger(__name__)


async def _get_country(session: aiohttp.ClientSession, ip: str) -> str:
    try:
        async with session.get(
            config.GEOIP_API.format(ip=ip), timeout=aiohttp.ClientTimeout(total=4)
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                if data.get("status") == "success":
                    return data.get("countryCode", "??")
    except Exception:
        pass
    return "??"


async def check_proxy(proxy: str, protocol: str, semaphore: asyncio.Semaphore) -> dict | None:
    """
    Liveness check only — no geo lookup here. Releasing the semaphore slot
    the moment this resolves (bounded by CHECK_TIMEOUT) is what lets a
    large candidate pool actually benefit from MAX_CONCURRENT_CHECKS;
    geo-IP lookup used to add up to 4 more seconds per SUCCESSFUL check
    before the slot freed, and worse, ip-api.com's free tier caps at
    ~45 requests/minute — a limit that no amount of internal concurrency
    tuning can get around. See check_all() for where geo lookup now happens.
    """
    async with semaphore:
        start = time.monotonic()
        try:
            if protocol in ("http", "https"):
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        config.CHECK_URL,
                        proxy=f"http://{proxy}",
                        timeout=aiohttp.ClientTimeout(total=config.CHECK_TIMEOUT),
                    ) as resp:
                        if resp.status != 200:
                            return None
            else:
                ip, port = proxy.split(":")
                proxy_type = ProxyType.SOCKS4 if protocol == "socks4" else ProxyType.SOCKS5
                connector = ProxyConnector(proxy_type=proxy_type, host=ip, port=int(port))
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        config.CHECK_URL,
                        timeout=aiohttp.ClientTimeout(total=config.CHECK_TIMEOUT),
                    ) as resp:
                        if resp.status != 200:
                            return None

            latency_ms = round((time.monotonic() - start) * 1000)
            return {"proxy": proxy, "protocol": protocol, "latency": latency_ms, "country": "??"}

        except Exception:
            return None


async def check_all(proxies_by_protocol: dict[str, set[str]]) -> list[dict]:
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)

    tasks = [
        check_proxy(proxy, protocol, semaphore)
        for protocol, proxies in proxies_by_protocol.items()
        for proxy in proxies
    ]
    total = len(tasks)

    if total == 0:
        return []

    working: list[dict] = []
    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result:
            working.append(result)

    working.sort(key=lambda x: x["latency"])
    logger.info(f"البروكسيات الشغالة: {len(working)} من أصل {total}")

    # Geo lookup happens AFTER liveness checking, only on the (much
    # smaller) working set, with its own concurrency cap kept under
    # ip-api.com's free-tier ~45 req/min limit — so it can't bottleneck
    # the expensive liveness-check phase anymore, and can't blow through
    # the external service's own rate limit either.
    geo_semaphore = asyncio.Semaphore(40)

    async def _attach_country(entry: dict, geo_session: aiohttp.ClientSession) -> None:
        async with geo_semaphore:
            entry["country"] = await _get_country(geo_session, entry["proxy"].split(":")[0])

    async with aiohttp.ClientSession() as geo_session:
        await asyncio.gather(*[_attach_country(w, geo_session) for w in working])

    return working
