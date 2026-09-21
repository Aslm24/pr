import checker
import crawler
import generator
import scraper


async def scrape_check_smart() -> tuple[dict[str, set[str]], list[dict]]:
    discovered = await crawler.discover_sources()
    proxies_by_protocol = await scraper.scrape_all(extra_sources=discovered)
    proxies_by_protocol = await generator.expand_with_generated(proxies_by_protocol)
    working = await checker.check_all(proxies_by_protocol)
    return proxies_by_protocol, working
