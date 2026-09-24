import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Comma-separated Telegram user IDs, e.g. "5495732905,123456789".
# Defaults to the previously-hardcoded ID so behavior doesn't silently
# change if this isn't set — but set it explicitly in your environment
# (or as an Actions/systemd secret) going forward rather than relying on
# the default.
_owner_ids_raw = os.getenv("OWNER_IDS", "5495732905")
OWNER_IDS: list[int] = [int(uid.strip()) for uid in _owner_ids_raw.split(",") if uid.strip()]

MAX_CHANNELS_PER_USER = 0

PROXY_SOURCES = {
    "http": [
        "https://raw.githubusercontent.com/gproxynet/free-proxy-list/main/http.txt",
        "https://raw.githubusercontent.com/hproxy-com/free-proxy-list/main/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/relayglass/free-proxy-list/main/protocol/http/http.txt",
        "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        "https://vakhov.github.io/fresh-proxy-list/http.txt",
        "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",
    ],

    "https": [
        "https://raw.githubusercontent.com/hproxy-com/free-proxy-list/main/https.txt",
        "https://raw.githubusercontent.com/relayglass/free-proxy-list/main/protocol/https/https.txt",
        "https://vakhov.github.io/fresh-proxy-list/https.txt",
    ],

    "socks4": [
        "https://raw.githubusercontent.com/gproxynet/free-proxy-list/main/socks4.txt",
        "https://raw.githubusercontent.com/hproxy-com/free-proxy-list/main/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/relayglass/free-proxy-list/main/protocol/socks4/socks4.txt",
        "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
        "https://vakhov.github.io/fresh-proxy-list/socks4.txt",
        "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks4.txt",
    ],

    "socks5": [
        "https://raw.githubusercontent.com/gproxynet/free-proxy-list/main/socks5.txt",
        "https://raw.githubusercontent.com/hproxy-com/free-proxy-list/main/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/relayglass/free-proxy-list/main/protocol/socks5/socks5.txt",
        "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
        "https://vakhov.github.io/fresh-proxy-list/socks5.txt",
        "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
    ],
}

PROXYSCRAPE_API = (
    "https://api.proxyscrape.com/v3/free-proxy-list/get"
    "?request=display_proxies&protocol={proto}&timeout=10000&country=all&ssl=all&anonymity=all"
)
PROXYSCRAPE_PROTOCOLS = ["http", "socks4", "socks5"]

GITHUB_SEARCH_QUERIES = [
    "socks5.txt in:path",
    "socks4.txt in:path",
    "http.txt proxy in:path",
    "proxy_list.txt in:path",
]
# No hardcoded fallback — the old token here was leaked (pasted in plaintext
# during development) and should be treated as burned. Rotate it at
# https://github.com/settings/tokens, then set GITHUB_TOKEN as a real
# environment variable (a GitHub Actions secret in CI, or your shell/systemd
# env on a server) — never back in source. Running without it still works,
# just at GitHub's lower unauthenticated Search API rate limit.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

GENERATOR_COMMON_PORTS = ["8080", "3128", "1080", "4145"]

CHECK_URL = "http://httpbin.org/ip"
CHECK_TIMEOUT = 2
MAX_CONCURRENT_CHECKS = 800

GEOIP_API = "http://ip-api.com/json/{ip}?fields=status,countryCode"

AUTO_INTERVAL_HOURS = 3
AUTO_LOOP_TICK_MINUTES = 10
PUBLISH_BATCH_AS_FILE_THRESHOLD = 30

DB_PATH = "proxybot.db"
