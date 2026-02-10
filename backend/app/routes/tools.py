"""Standalone quick-access recon tools — no project required.

Each tool runs a lightweight operation directly (or in a short-lived container)
and returns inline results. Optionally, results can be saved to a project later.

Categories: Network, Web, OSINT.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
import subprocess
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _run(cmd: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run a subprocess asynchronously with a timeout. Returns (stdout, stderr, returncode)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode or 0
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        return "", "Command timed out", 1
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}", 127


def _validate_target(target: str) -> str:
    """Basic validation: strip, reject empty, reject obvious shell injection."""
    target = target.strip()
    if not target:
        raise HTTPException(400, "Target must not be empty.")
    # Block shell meta-characters
    bad = set(";&|`$(){}[]!#\n\r")
    if bad & set(target):
        raise HTTPException(400, "Target contains disallowed characters.")
    if len(target) > 253:
        raise HTTPException(400, "Target too long.")
    return target


# ---------------------------------------------------------------------------
# WHOIS / RDAP
# ---------------------------------------------------------------------------

class WhoisRequest(BaseModel):
    target: str = Field(..., description="Domain name or IP address")


class WhoisResponse(BaseModel):
    target: str
    raw: str
    timestamp: str


@router.post("/whois", response_model=WhoisResponse)
async def whois_lookup(body: WhoisRequest) -> WhoisResponse:
    target = _validate_target(body.target)
    stdout, stderr, rc = await _run(["whois", target], timeout=15)
    if rc != 0 and not stdout:
        raise HTTPException(502, f"whois failed: {stderr.strip()}")
    return WhoisResponse(
        target=target,
        raw=stdout or stderr,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# DNS Lookup
# ---------------------------------------------------------------------------

class DnsRequest(BaseModel):
    target: str = Field(..., description="Domain or IP to query")
    record_type: str = Field("A", description="DNS record type (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR, ANY)")


class DnsRecord(BaseModel):
    name: str
    type: str
    value: str


class DnsResponse(BaseModel):
    target: str
    record_type: str
    raw: str
    records: list[DnsRecord]
    timestamp: str


@router.post("/dns", response_model=DnsResponse)
async def dns_lookup(body: DnsRequest) -> DnsResponse:
    target = _validate_target(body.target)
    rtype = body.record_type.upper().strip()
    allowed = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "ANY", "SRV"}
    if rtype not in allowed:
        raise HTTPException(400, f"Unsupported record type. Allowed: {', '.join(sorted(allowed))}")

    stdout, stderr, rc = await _run(["dig", "+noall", "+answer", "+authority", target, rtype], timeout=10)

    records: list[DnsRecord] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if len(parts) >= 5:
            records.append(DnsRecord(name=parts[0], type=parts[3], value=" ".join(parts[4:])))

    return DnsResponse(
        target=target,
        record_type=rtype,
        raw=stdout or stderr,
        records=records,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Reverse DNS
# ---------------------------------------------------------------------------

class ReverseDnsRequest(BaseModel):
    ip: str


class ReverseDnsResponse(BaseModel):
    ip: str
    hostnames: list[str]
    timestamp: str


@router.post("/reverse-dns", response_model=ReverseDnsResponse)
async def reverse_dns(body: ReverseDnsRequest) -> ReverseDnsResponse:
    ip = _validate_target(body.ip)
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(400, "Must be a valid IP address.")

    stdout, stderr, rc = await _run(["dig", "+short", "-x", ip], timeout=10)
    hostnames = [h.strip().rstrip(".") for h in stdout.splitlines() if h.strip()]
    return ReverseDnsResponse(
        ip=ip,
        hostnames=hostnames,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Ping / Connectivity check
# ---------------------------------------------------------------------------

class PingRequest(BaseModel):
    target: str
    count: int = Field(4, ge=1, le=10)


class PingResponse(BaseModel):
    target: str
    alive: bool
    raw: str
    timestamp: str


@router.post("/ping", response_model=PingResponse)
async def ping_target(body: PingRequest) -> PingResponse:
    target = _validate_target(body.target)
    stdout, stderr, rc = await _run(["ping", "-c", str(body.count), "-W", "2", target], timeout=20)
    alive = rc == 0
    return PingResponse(
        target=target,
        alive=alive,
        raw=stdout or stderr,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Quick port scan (top ports, using nmap if available, else fallback to socket)
# ---------------------------------------------------------------------------

class PortScanRequest(BaseModel):
    target: str
    ports: str = Field("1-1024", description="Port range (e.g. '80,443' or '1-1024')")
    timeout_per_port: float = Field(1.0, ge=0.1, le=5.0)


class PortResult(BaseModel):
    port: int
    state: str
    service: str = ""


class PortScanResponse(BaseModel):
    target: str
    ports_scanned: str
    open_ports: list[PortResult]
    raw: str
    timestamp: str


@router.post("/portscan", response_model=PortScanResponse)
async def port_scan(body: PortScanRequest) -> PortScanResponse:
    target = _validate_target(body.target)

    # Try nmap first (may not be on host — that's fine, fall back)
    stdout, stderr, rc = await _run(
        ["nmap", "-Pn", "-p", body.ports, "--open", "-oG", "-", target],
        timeout=120,
    )

    open_ports: list[PortResult] = []

    if rc != 127:
        # Parse nmap grepable output
        for line in stdout.splitlines():
            if "Ports:" not in line:
                continue
            ports_section = line.split("Ports:")[1].strip()
            for entry in ports_section.split(","):
                entry = entry.strip()
                parts = entry.split("/")
                if len(parts) >= 5 and parts[1] == "open":
                    open_ports.append(PortResult(
                        port=int(parts[0]),
                        state="open",
                        service=parts[4] if len(parts) > 4 else "",
                    ))
        return PortScanResponse(
            target=target,
            ports_scanned=body.ports,
            open_ports=open_ports,
            raw=stdout,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Fallback: pure-Python socket scan
    port_list = _parse_port_range(body.ports)
    if len(port_list) > 4096:
        raise HTTPException(400, "Too many ports (max 4096 for socket fallback).")

    raw_lines: list[str] = []
    for port in port_list:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(body.timeout_per_port)
            result = sock.connect_ex((target, port))
            sock.close()
            if result == 0:
                svc = ""
                try:
                    svc = socket.getservbyport(port, "tcp")
                except OSError:
                    pass
                open_ports.append(PortResult(port=port, state="open", service=svc))
                raw_lines.append(f"{port}/tcp open {svc}")
        except (socket.gaierror, OSError):
            pass

    return PortScanResponse(
        target=target,
        ports_scanned=body.ports,
        open_ports=open_ports,
        raw="\n".join(raw_lines) or "(no open ports found)",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


def _parse_port_range(spec: str) -> list[int]:
    ports: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            lo_i, hi_i = int(lo), int(hi)
            if lo_i < 1 or hi_i > 65535 or lo_i > hi_i:
                raise HTTPException(400, f"Invalid port range: {chunk}")
            ports.extend(range(lo_i, hi_i + 1))
        else:
            p = int(chunk)
            if p < 1 or p > 65535:
                raise HTTPException(400, f"Invalid port: {p}")
            ports.append(p)
    return ports


# ---------------------------------------------------------------------------
# HTTP Headers
# ---------------------------------------------------------------------------

class HeadersRequest(BaseModel):
    url: str = Field(..., description="Full URL (http/https)")


class HeadersResponse(BaseModel):
    url: str
    status_code: int
    headers: dict[str, str]
    timestamp: str


@router.post("/headers", response_model=HeadersResponse)
async def http_headers(body: HeadersRequest) -> HeadersResponse:
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")
    _validate_target(url)

    stdout, stderr, rc = await _run(
        ["curl", "-sS", "-o", "/dev/null", "-D", "-", "-m", "10", "--max-redirs", "3", "-L", url],
        timeout=15,
    )
    if rc != 0 and not stdout:
        raise HTTPException(502, f"curl failed: {stderr.strip()}")

    headers: dict[str, str] = {}
    status_code = 0
    for line in stdout.splitlines():
        line = line.strip()
        if line.upper().startswith("HTTP/"):
            parts = line.split(None, 2)
            if len(parts) >= 2:
                try:
                    status_code = int(parts[1])
                except ValueError:
                    pass
        elif ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()

    return HeadersResponse(
        url=url,
        status_code=status_code,
        headers=headers,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Subnet / CIDR calculator (pure Python, no external tool)
# ---------------------------------------------------------------------------

class SubnetCalcRequest(BaseModel):
    cidr: str = Field(..., description="CIDR notation, e.g. 192.168.1.0/24")


class SubnetCalcResponse(BaseModel):
    cidr: str
    network_address: str
    broadcast_address: str
    netmask: str
    host_count: int
    first_host: str
    last_host: str
    is_private: bool


@router.post("/subnet-calc", response_model=SubnetCalcResponse)
async def subnet_calc(body: SubnetCalcRequest) -> SubnetCalcResponse:
    cidr = body.cidr.strip()
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        raise HTTPException(400, f"Invalid CIDR: {e}")

    hosts = list(net.hosts())
    return SubnetCalcResponse(
        cidr=str(net),
        network_address=str(net.network_address),
        broadcast_address=str(net.broadcast_address),
        netmask=str(net.netmask),
        host_count=net.num_addresses,
        first_host=str(hosts[0]) if hosts else str(net.network_address),
        last_host=str(hosts[-1]) if hosts else str(net.network_address),
        is_private=net.is_private,
    )


# ===========================================================================
# OSINT TOOLS
# ===========================================================================


# ---------------------------------------------------------------------------
# Subdomain Enumeration (passive DNS brute via dig against common prefixes)
# ---------------------------------------------------------------------------

_COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "smtp", "pop", "imap", "webmail", "ns1", "ns2",
    "dns", "mx", "vpn", "remote", "portal", "admin", "dev", "staging",
    "api", "app", "cdn", "cloud", "git", "ci", "jenkins", "test",
    "beta", "demo", "blog", "shop", "store", "m", "mobile", "docs",
    "wiki", "help", "support", "status", "monitor", "login", "sso",
    "auth", "id", "accounts", "intranet", "internal", "db", "sql",
    "redis", "elastic", "kibana", "grafana", "prometheus", "vault",
    "s3", "bucket", "assets", "static", "media", "img", "images",
    "video", "web", "proxy", "gateway", "lb", "edge", "node",
]


class SubdomainEnumRequest(BaseModel):
    domain: str


class SubdomainEnumResponse(BaseModel):
    domain: str
    subdomains: list[str]
    raw: str
    timestamp: str


@router.post("/subdomain-enum", response_model=SubdomainEnumResponse)
async def subdomain_enum(body: SubdomainEnumRequest) -> SubdomainEnumResponse:
    domain = _validate_target(body.domain)
    found: list[str] = []
    raw_lines: list[str] = []

    async def _check(prefix: str) -> None:
        fqdn = f"{prefix}.{domain}"
        stdout, stderr, rc = await _run(["dig", "+short", fqdn, "A"], timeout=5)
        ips = [l.strip() for l in stdout.splitlines() if l.strip() and not l.startswith(";")]
        if ips:
            found.append(fqdn)
            raw_lines.append(f"{fqdn} -> {', '.join(ips)}")

    # Run checks concurrently in batches
    batch_size = 20
    for i in range(0, len(_COMMON_SUBDOMAINS), batch_size):
        batch = _COMMON_SUBDOMAINS[i:i + batch_size]
        await asyncio.gather(*[_check(p) for p in batch])

    found.sort()
    return SubdomainEnumResponse(
        domain=domain,
        subdomains=found,
        raw="\n".join(raw_lines) or "(no subdomains resolved)",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Technology Detection (via HTTP headers + HTML meta heuristics)
# ---------------------------------------------------------------------------

class TechDetectRequest(BaseModel):
    url: str


class TechDetectResponse(BaseModel):
    url: str
    status_code: int
    technologies: list[str]
    headers: dict[str, str]
    timestamp: str


# Header/body patterns -> technology name
_TECH_SIGNATURES: list[tuple[str, str, str]] = [
    # (where, pattern, tech_name)
    ("header:x-powered-by", "php", "PHP"),
    ("header:x-powered-by", "asp.net", "ASP.NET"),
    ("header:x-powered-by", "express", "Express.js"),
    ("header:x-powered-by", "next.js", "Next.js"),
    ("header:server", "nginx", "Nginx"),
    ("header:server", "apache", "Apache"),
    ("header:server", "cloudflare", "Cloudflare"),
    ("header:server", "microsoft-iis", "IIS"),
    ("header:server", "litespeed", "LiteSpeed"),
    ("header:server", "openresty", "OpenResty"),
    ("header:x-drupal", "", "Drupal"),
    ("header:x-generator", "wordpress", "WordPress"),
    ("header:x-generator", "drupal", "Drupal"),
    ("header:x-shopify", "", "Shopify"),
    ("body", "wp-content", "WordPress"),
    ("body", "wp-includes", "WordPress"),
    ("body", "/sites/default/files", "Drupal"),
    ("body", "joomla", "Joomla"),
    ("body", "react", "React"),
    ("body", "__next", "Next.js"),
    ("body", "__nuxt", "Nuxt.js"),
    ("body", "angular", "Angular"),
    ("body", "vue.js", "Vue.js"),
    ("body", "jquery", "jQuery"),
    ("body", "bootstrap", "Bootstrap"),
    ("body", "tailwindcss", "Tailwind CSS"),
    ("body", "shopify", "Shopify"),
    ("body", "squarespace", "Squarespace"),
    ("body", "wix.com", "Wix"),
]


@router.post("/tech-detect", response_model=TechDetectResponse)
async def tech_detect(body: TechDetectRequest) -> TechDetectResponse:
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")
    _validate_target(url)

    # Fetch headers
    h_stdout, h_stderr, h_rc = await _run(
        ["curl", "-sS", "-o", "/dev/null", "-D", "-", "-m", "10", "--max-redirs", "3", "-L", url],
        timeout=15,
    )
    headers: dict[str, str] = {}
    status_code = 0
    for line in h_stdout.splitlines():
        line = line.strip()
        if line.upper().startswith("HTTP/"):
            parts = line.split(None, 2)
            if len(parts) >= 2:
                try: status_code = int(parts[1])
                except ValueError: pass
        elif ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()

    # Fetch body (first 50KB)
    b_stdout, _, _ = await _run(
        ["curl", "-sS", "-m", "10", "--max-redirs", "3", "-L", "-r", "0-51200", url],
        timeout=15,
    )

    techs: set[str] = set()
    for where, pattern, name in _TECH_SIGNATURES:
        if where.startswith("header:"):
            hkey = where.split(":", 1)[1]
            hval = ""
            for k, v in headers.items():
                if k.lower() == hkey.lower():
                    hval = v
                    break
            if hval and (not pattern or pattern.lower() in hval.lower()):
                techs.add(name)
        elif where == "body":
            if pattern.lower() in b_stdout.lower():
                techs.add(name)

    return TechDetectResponse(
        url=url,
        status_code=status_code,
        technologies=sorted(techs),
        headers=headers,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Email Harvest (passive: DNS MX + simple search via public sources)
# ---------------------------------------------------------------------------

class EmailHarvestRequest(BaseModel):
    domain: str


class EmailHarvestResponse(BaseModel):
    domain: str
    emails: list[str]
    mx_records: list[str]
    raw: str
    timestamp: str


@router.post("/email-harvest", response_model=EmailHarvestResponse)
async def email_harvest(body: EmailHarvestRequest) -> EmailHarvestResponse:
    domain = _validate_target(body.domain)

    # MX records
    mx_stdout, _, _ = await _run(["dig", "+short", domain, "MX"], timeout=10)
    mx_records = [l.strip() for l in mx_stdout.splitlines() if l.strip()]

    # Try to find emails from publicly reachable pages (homepage, contact)
    emails: set[str] = set()
    raw_lines: list[str] = [f"MX records: {', '.join(mx_records) or 'none'}"]

    for path in ["", "/contact", "/about", "/impressum"]:
        for scheme in ["https", "http"]:
            url = f"{scheme}://{domain}{path}"
            stdout, _, rc = await _run(
                ["curl", "-sS", "-m", "8", "--max-redirs", "2", "-L", url],
                timeout=12,
            )
            if rc == 0 and stdout:
                # Extract email-like strings
                found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", stdout)
                for e in found:
                    if domain.lower() in e.lower():
                        emails.add(e.lower())
                if found:
                    raw_lines.append(f"{url}: found {len(found)} email(s)")
                break  # https worked, skip http

    return EmailHarvestResponse(
        domain=domain,
        emails=sorted(emails),
        mx_records=mx_records,
        raw="\n".join(raw_lines),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Social Lookup (check username on public platforms via HTTP HEAD/GET)
# ---------------------------------------------------------------------------

class SocialLookupRequest(BaseModel):
    username: str


class SocialProfile(BaseModel):
    platform: str
    url: str
    found: bool


class SocialLookupResponse(BaseModel):
    username: str
    profiles: list[SocialProfile]
    timestamp: str


_SOCIAL_PLATFORMS = [
    ("GitHub", "https://github.com/{u}"),
    ("GitLab", "https://gitlab.com/{u}"),
    ("Twitter/X", "https://x.com/{u}"),
    ("Reddit", "https://www.reddit.com/user/{u}"),
    ("Instagram", "https://www.instagram.com/{u}/"),
    ("LinkedIn", "https://www.linkedin.com/in/{u}/"),
    ("YouTube", "https://www.youtube.com/@{u}"),
    ("TikTok", "https://www.tiktok.com/@{u}"),
    ("Pinterest", "https://www.pinterest.com/{u}/"),
    ("Medium", "https://medium.com/@{u}"),
    ("Dev.to", "https://dev.to/{u}"),
    ("Keybase", "https://keybase.io/{u}"),
    ("HackerOne", "https://hackerone.com/{u}"),
    ("Bugcrowd", "https://bugcrowd.com/{u}"),
]


@router.post("/social-lookup", response_model=SocialLookupResponse)
async def social_lookup(body: SocialLookupRequest) -> SocialLookupResponse:
    username = body.username.strip()
    if not username or not re.match(r"^[a-zA-Z0-9._\-]+$", username):
        raise HTTPException(400, "Username must be alphanumeric (dots, hyphens, underscores allowed).")

    profiles: list[SocialProfile] = []

    async def _check(platform: str, url_tpl: str) -> None:
        url = url_tpl.replace("{u}", username)
        stdout, stderr, rc = await _run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-m", "8",
             "-L", "--max-redirs", "2",
             "-A", "Mozilla/5.0 (compatible; recon-tool/1.0)",
             url],
            timeout=12,
        )
        code = stdout.strip()
        found = code in ("200", "301", "302")
        profiles.append(SocialProfile(platform=platform, url=url, found=found))

    batch_size = 7
    for i in range(0, len(_SOCIAL_PLATFORMS), batch_size):
        batch = _SOCIAL_PLATFORMS[i:i + batch_size]
        await asyncio.gather(*[_check(p, u) for p, u in batch])

    profiles.sort(key=lambda p: (not p.found, p.platform))
    return SocialLookupResponse(
        username=username,
        profiles=profiles,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Wayback Machine URLs (via CDX API — public, no key required)
# ---------------------------------------------------------------------------

class WaybackRequest(BaseModel):
    domain: str


class WaybackResponse(BaseModel):
    domain: str
    urls: list[str]
    total: int
    timestamp: str


@router.post("/wayback", response_model=WaybackResponse)
async def wayback_urls(body: WaybackRequest) -> WaybackResponse:
    domain = _validate_target(body.domain)

    cdx_url = f"http://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=text&fl=original&collapse=urlkey&limit=500"
    stdout, stderr, rc = await _run(
        ["curl", "-sS", "-m", "15", "--max-redirs", "2", cdx_url],
        timeout=20,
    )

    urls: list[str] = []
    if rc == 0 and stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if line and line.startswith(("http://", "https://")):
                urls.append(line)

    # Deduplicate
    urls = sorted(set(urls))

    return WaybackResponse(
        domain=domain,
        urls=urls,
        total=len(urls),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
