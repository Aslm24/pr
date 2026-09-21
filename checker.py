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


async def check_proxy(
    proxy: str,
    protocol: str,
    semaphore: asyncio.Semaphore,
    geo_session: aiohttp.ClientSession,
) -> dict | None:
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
            country = await _get_country(geo_session, proxy.split(":")[0])
            return {"proxy": proxy, "protocol": protocol, "latency": latency_ms, "country": country}

        except Exception:
            return None


async def check_all(proxies_by_protocol: dict[str, set[str]]) -> list[dict]:
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CHECKS)
    working: list[dict] = []

    async with aiohttp.ClientSession() as geo_session:
        tasks = [
            check_proxy(proxy, protocol, semaphore, geo_session)
            for protocol, proxies in proxies_by_protocol.items()
            for proxy in proxies
        ]
        total = len(tasks)

        if total == 0:
            return []

        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                working.append(result)

    working.sort(key=lambda x: x["latency"])
    logger.info(f"البروكسيات الشغالة: {len(working)} من أصل {total}")
    return working
