"""
One-shot scrape + check + publish — meant to run on a schedule via GitHub
Actions (see the workflow file below), not as a persistent process.

No SQLite, no bot polling, no per-channel management — just: run the
existing crawler+scraper+generator+checker pipeline once, post the result
to one Telegram channel via a plain HTTP call, exit. The scheduling is
GitHub's cron, not this script's job.

Required environment variables (set these as GitHub Actions secrets,
never hardcode them):
    BOT_TOKEN    - Telegram bot token
    CHANNEL_ID   - target channel, e.g. -1001234567890
    GITHUB_TOKEN - optional, raises crawler.py's GitHub Search API rate
                   limit; omit to run it unauthenticated (lower limit,
                   still works)
"""

import asyncio
import os
import sys

import aiohttp

import engine  # existing pipeline, unchanged

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

PROTO_LABELS = {"http": "HTTP", "https": "HTTPS", "socks4": "SOCKS4", "socks5": "SOCKS5"}


async def post_message(session: aiohttp.ClientSession, text: str) -> None:
    async with session.post(
        f"{TELEGRAM_API}/sendMessage",
        data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
    ) as resp:
        if resp.status != 200:
            print(f"sendMessage failed: {resp.status} {(await resp.text())[:200]}", file=sys.stderr)


async def post_document(session: aiohttp.ClientSession, filename: str, content: bytes, caption: str) -> None:
    form = aiohttp.FormData()
    form.add_field("chat_id", CHANNEL_ID)
    form.add_field("caption", caption)
    form.add_field("document", content, filename=filename)
    async with session.post(f"{TELEGRAM_API}/sendDocument", data=form) as resp:
        if resp.status != 200:
            print(f"sendDocument failed: {resp.status} {(await resp.text())[:200]}", file=sys.stderr)


def format_working(working: list[dict]) -> str:
    lines = ["🟢 <b>بروكسيات شغالة</b>\n"]
    for p in working:
        lines.append(
            f"<code>{p['proxy']}</code> | {PROTO_LABELS.get(p['protocol'], p['protocol'])} "
            f"| {p['country']} | {p['latency']}ms"
        )
    return "\n".join(lines)


def format_file_body(working: list[dict]) -> str:
    return "\n".join(
        f"{p['proxy']} | {PROTO_LABELS.get(p['protocol'], p['protocol'])} | {p['country']} | {p['latency']}ms"
        for p in working
    )


async def main() -> None:
    proxies_by_protocol, working = await engine.scrape_check_smart()
    total = sum(len(v) for v in proxies_by_protocol.values())
    print(f"scraped={total} working={len(working)}")

    async with aiohttp.ClientSession() as session:
        if not working:
            await post_message(session, "⚠️ لم يتم العثور على أي بروكسي شغال في هذه الجولة.")
            return

        if len(working) > 30:
            body = format_file_body(working)
            await post_document(session, f"proxies_{total}.txt", body.encode("utf-8"),
                                 f"✅ عدد البروكسيات الشغالة: {len(working)}")
        else:
            await post_message(session, format_working(working))


if __name__ == "__main__":
    asyncio.run(main())
