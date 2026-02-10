# BLACKWALL — Local Recon Suite

A locally hosted web application for orchestrating reconnaissance workflows. Built as a single-operator tool for authorized penetration testing engagements, Blackwall provides a unified interface across OSINT, active scanning, web enumeration, and cloud asset discovery.

## What it does

Blackwall replaces the scattered CLI-tool-and-notes workflow with a structured pipeline. It runs recon tools inside Docker containers, normalizes their output, correlates findings across modules, and ranks the most likely pathway to initial access — all from a single browser tab.

### Modules

- **OSINT** — WHOIS/RDAP lookups, DNS discovery, subdomain enumeration, email harvesting, social username checks, Wayback Machine historical URL retrieval, and web technology fingerprinting. All passive, no API keys, no scraping.
- **Active Scanning** — Configurable Nmap port scans (SYN/TCP connect), OS detection, curated NSE script sets, NetBIOS/SMB and SNMP enumeration. Aggressiveness is user-controlled on a 1–10 scale.
- **Web Enumeration** — Directory and file brute-forcing, recursive scanning, custom wordlists, HTTP status code filtering, robots.txt and sitemap.xml parsing, parameter discovery with response diffing, and CMS fingerprinting.
- **Cloud Discovery** — Multi-provider identification (AWS, Azure, GCP) via DNS patterns, certificate SANs, headers, and URLs. Safe unauthenticated validation only. Assets tagged by shared responsibility model.

### Standalone Tools

A dedicated Tools page provides quick-access utilities that work independently of any project: Ping, DNS Lookup, Reverse DNS, Port Scan, Subnet Calculator, HTTP Headers, Tech Detect, WHOIS, Subdomain Enum, Email Harvest, Social Lookup, and Wayback URLs. DNS and Ping are also embedded directly on the Dashboard.

### Correlation and Pathway Ranking

Findings from all modules are normalized, deduplicated, and linked across targets, IPs, ports, services, web routes, and cloud assets. A ranking engine scores initial access hypotheses based on external exposure, service risk heuristics, CVE enrichment, and misconfiguration indicators. The top pathway is surfaced prominently on the Dashboard.

### Reporting

One-click generation of Markdown and PDF reports containing an executive summary, attack surface overview, detailed technical findings with CVSS vectors (auto-derived, with accuracy disclaimer), Cyber Kill Chain mapping, and tool configuration appendices.

## Architecture

- **Backend** — Python / FastAPI serving a REST API and WebSocket updates. PostgreSQL for structured data, disk artifact store for raw outputs and reports.
- **Frontend** — Vite + React single-page application with a Cyberpunk 2077-inspired dark theme. All assets self-hosted (no CDN). Fonts are Rajdhani and Share Tech Mono via bundled @fontsource packages.
- **Toolchain** — Docker Compose orchestrates Postgres and recon tool containers (Nmap, Gobuster, dnsutils). Tool images use pinned versions for reproducibility.
- **Job System** — In-process priority queue with concurrency control. Jobs support pause (stop + restart), cancel, rerun, best-effort progress/ETA, and in-app completion alerts.

## Safety

- Binds to `127.0.0.1` only. Not designed for remote or multi-user access.
- Mandatory authorization checkbox before any active scan executes. External/public targets require an additional admin approval step.
- Scope preview shows CIDR host count and flags large scopes. Targets are auto-tagged as internal or external.
- Noise/detectability scoring (1–10) with a warning gate for high-noise or external scans.
- No exploitation, no payloads, no credential attacks. Recon only.

## Supported platforms

Fedora Linux, Arch Linux, and EndeavourOS with out-of-box install scripts. Best-effort support for macOS and Windows via Docker Desktop.

## License

For educational use. Ensure you have authorization before testing any target.
