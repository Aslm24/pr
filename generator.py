import config


def _generate_candidates(existing_proxies: set[str]) -> set[str]:
    candidates = set()
    ips = {p.split(":")[0] for p in existing_proxies}
    for ip in ips:
        for port in config.GENERATOR_COMMON_PORTS:
            candidate = f"{ip}:{port}"
            if candidate not in existing_proxies:
                candidates.add(candidate)
    return candidates


async def expand_with_generated(proxies_by_protocol: dict[str, set[str]]) -> dict[str, set[str]]:
    expanded = {proto: set(proxies) for proto, proxies in proxies_by_protocol.items()}

    for protocol, proxies in proxies_by_protocol.items():
        if not proxies:
            continue
        candidates = _generate_candidates(proxies)
        if candidates:
            expanded[protocol] |= candidates

    return expanded
