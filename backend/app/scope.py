# Scope preview: CIDR host count, internal vs external tagging.
from __future__ import annotations

import ipaddress
from typing import Any


def is_private_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback or a.is_link_local
    except ValueError:
        return False


def is_private_cidr(cidr: str) -> bool:
    try:
        n = ipaddress.ip_network(cidr, strict=False)
        return n.is_private
    except ValueError:
        return False


def cidr_host_count(cidr: str) -> int:
    try:
        n = ipaddress.ip_network(cidr, strict=False)
        return n.num_addresses
    except ValueError:
        return 0


def infer_internal(target: dict[str, Any]) -> bool:
    """Tag as internal if private/local range."""
    t = target.get("type")
    v = (target.get("value") or "").strip()
    if t == "cidr":
        return is_private_cidr(v)
    if t == "ip":
        return is_private_ip(v)
    if t == "fqdn":
        # Localhost-style
        if v.lower() in ("localhost", "localhost.localdomain"):
            return True
        return False
    if t == "url":
        if "localhost" in v or "127.0.0.1" in v:
            return True
        return False
    return True  # default conservative


def parse_targets_for_scope(targets: list[dict]) -> dict:
    """Return scope preview: cidrs with host count, total hosts, has_external, warnings."""
    total_hosts = 0
    cidrs: list[dict] = []
    has_external = False
    for t in targets:
        typ = t.get("type")
        val = (t.get("value") or "").strip()
        if not val:
            continue
        if typ == "cidr":
            count = cidr_host_count(val)
            total_hosts += count
            cidrs.append({"cidr": val, "host_count": count, "internal": is_private_cidr(val)})
            if not is_private_cidr(val):
                has_external = True
        elif typ == "ip":
            total_hosts += 1
            if not is_private_ip(val):
                has_external = True
        elif typ in ("fqdn", "url"):
            has_external = True  # assume external unless localhost
    return {
        "cidrs": cidrs,
        "total_hosts": total_hosts,
        "has_external": has_external,
        "large_scope_warning": total_hosts > 256,
    }
