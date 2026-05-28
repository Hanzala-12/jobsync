"""URL ingestion helpers with SSRF protections."""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAX_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT = 10
ALLOWED_INGESTION_DOMAINS = [host.strip().lower() for host in os.getenv("ALLOWED_INGESTION_DOMAINS", "").split(",") if host.strip()]
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]


def _host_matches_allowlist(hostname: str) -> bool:
    if not ALLOWED_INGESTION_DOMAINS:
        return False

    lowered = hostname.lower()
    return any(lowered == allowed or lowered.endswith(f".{allowed}") for allowed in ALLOWED_INGESTION_DOMAINS)


def _is_blocked_ip_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False

    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    return any(ip in network for network in _BLOCKED_NETWORKS)


def _hostname_resolves_to_blocked_address(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except Exception:
        return False

    for info in infos:
        addr = info[4][0]
        if _is_blocked_ip_address(addr):
            return True
    return False


def extract_job_text_from_url(url: str) -> dict:
    """Extract job description text from a URL with SSRF protections."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"raw_text": "", "url": url, "success": False, "error": "Invalid URL scheme"}

        hostname = parsed.hostname or ""
        if not hostname:
            return {"raw_text": "", "url": url, "success": False, "error": "Invalid hostname"}

        if not _host_matches_allowlist(hostname):
            return {"raw_text": "", "url": url, "success": False, "error": "Hostname not allowed"}

        if _is_blocked_ip_address(hostname) or _hostname_resolves_to_blocked_address(hostname):
            return {"raw_text": "", "url": url, "success": False, "error": "Hostname resolves to private or loopback address"}

        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobSync/2.0)"}
        with requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True) as resp:
            resp.raise_for_status()
            cl = resp.headers.get("Content-Length") or "0"
            try:
                if int(cl) > MAX_BYTES:
                    return {"raw_text": "", "url": url, "success": False, "error": "Content-Length exceeds limit"}
            except Exception:
                pass

            # Read up to MAX_BYTES
            content = []
            total = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    total += len(chunk)
                    if total > MAX_BYTES:
                        return {"raw_text": "", "url": url, "success": False, "error": "Content too large"}
                    content.append(chunk)

            text = b"".join(content).decode("utf-8", errors="ignore")

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try common job description containers
        extracted = ""
        for sel in ["div.job-description", "div.description", "article", "main", "div.content"]:
            elem = soup.select_one(sel)
            if elem:
                extracted = elem.get_text(separator="\n", strip=True)
                break

        if not extracted:
            extracted = (soup.body.get_text(separator="\n", strip=True) if soup.body else "")[:5000]

        return {"raw_text": extracted, "url": url, "success": True}
    except Exception as e:
        return {"raw_text": "", "url": url, "success": False, "error": str(e)}
