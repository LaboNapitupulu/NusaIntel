from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SERVICES = {"db", "migrate", "api", "worker", "web", "proxy"}


def fail(message: str) -> int:
    print(f"Production Compose contract failed: {message}", file=sys.stderr)
    return 2


def service_networks(service: dict[str, Any]) -> set[str]:
    networks = service.get("networks", {})
    return set(networks if isinstance(networks, list) else networks.keys())


def main() -> int:
    try:
        configuration = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return fail(f"invalid rendered Compose JSON ({error})")

    services: dict[str, dict[str, Any]] = configuration.get("services", {})
    if set(services) != EXPECTED_SERVICES:
        return fail("service set differs from the reviewed six-service topology")

    exposed = {name for name, service in services.items() if service.get("ports")}
    if exposed != {"proxy"}:
        return fail("only the TLS proxy may publish host ports")

    proxy_ports = {
        (
            str(item.get("published")),
            int(item.get("target")),
            item.get("protocol", "tcp"),
        )
        for item in services["proxy"]["ports"]
    }
    required_ports = {("80", 80, "tcp"), ("443", 443, "tcp"), ("443", 443, "udp")}
    if proxy_ports != required_ports:
        return fail("proxy must publish only TCP 80/443 and UDP 443")

    if service_networks(services["db"]) != {"data"}:
        return fail("database must be isolated on the internal data network")
    if "edge" not in service_networks(services["proxy"]):
        return fail("proxy must be attached to the edge network")
    if "egress" not in service_networks(services["proxy"]):
        return fail("proxy needs outbound access for ACME certificate management")
    if "data" not in service_networks(services["api"]):
        return fail("API must reach the internal data network")

    networks = configuration.get("networks", {})
    if not networks.get("data", {}).get("internal"):
        return fail("data network must be marked internal")
    if not networks.get("edge", {}).get("internal"):
        return fail("edge network must be marked internal")

    database_environment = services["db"].get("environment", {})
    password = database_environment.get("POSTGRES_PASSWORD", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,}", password):
        return fail("POSTGRES_PASSWORD must be a 32+ character URL-safe value")

    proxy_environment = services["proxy"].get("environment", {})
    app_domain = proxy_environment.get("APP_DOMAIN", "")
    api_domain = proxy_environment.get("API_DOMAIN", "")
    domains = {app_domain, api_domain}
    domain_pattern = re.compile(
        r"(?=.{4,253}\Z)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
        r"[a-zA-Z]{2,63}\Z"
    )
    if len(domains) != 2 or any(
        not domain_pattern.fullmatch(domain) for domain in domains
    ):
        return fail("APP_DOMAIN and API_DOMAIN must be different public DNS hostnames")

    if services["proxy"].get("image") != "caddy:2.11.4-alpine":
        return fail("Caddy must use the reviewed pinned image tag")

    api_environment = services["api"].get("environment", {})
    expected_database_url = (
        "postgresql+asyncpg://"
        f"{database_environment.get('POSTGRES_USER')}:{password}@db:5432/"
        f"{database_environment.get('POSTGRES_DB')}"
    )
    if api_environment.get("DATABASE_URL") != expected_database_url:
        return fail(
            "API database URL must be derived from the PostgreSQL service values"
        )
    try:
        cors_origins = json.loads(api_environment.get("CORS_ORIGINS", ""))
        allowed_hosts = json.loads(api_environment.get("ALLOWED_HOSTS", ""))
    except json.JSONDecodeError:
        return fail("API host/origin allowlists must be valid JSON")
    if cors_origins != [f"https://{app_domain}"] or api_domain not in allowed_hosts:
        return fail(
            "API host/origin allowlists must be derived from the public domains"
        )

    web_environment = services["web"].get("environment", {})
    if web_environment.get("NEXT_PUBLIC_API_BASE_URL") != f"https://{api_domain}":
        return fail("frontend API URL must be derived from API_DOMAIN")
    for service_name in ("web", "proxy"):
        if "BPS_API_KEY" in services[service_name].get("environment", {}):
            return fail(f"BPS secret must not enter the {service_name} container")

    application_tags: set[str] = set()
    for service_name in ("api", "migrate", "worker", "web"):
        image = services[service_name].get("image", "")
        tag = image.rpartition(":")[2]
        if not re.fullmatch(r"[0-9a-f]{7,40}", tag):
            return fail(f"{service_name} must use an explicit candidate image tag")
        application_tags.add(tag)
    if len(application_tags) != 1:
        return fail("all application services must use the same candidate image tag")

    for service_name in ("api", "worker", "web", "proxy"):
        service = services[service_name]
        if not service.get("read_only"):
            return fail(f"{service_name} root filesystem must be read-only")
        if "no-new-privileges:true" not in service.get("security_opt", []):
            return fail(f"{service_name} must disable privilege escalation")

    caddyfile = (REPOSITORY_ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    required_fragments = (
        "max_size 2MB",
        "/api/v1/datasets/*/exceptions",
        "/api/v1/incidents/*",
        "reverse_proxy api:8000",
        "reverse_proxy web:3000",
    )
    if any(fragment not in caddyfile for fragment in required_fragments):
        return fail("Caddyfile is missing a reviewed public-edge control")

    print(
        "Production Compose contract valid: "
        "services=6 published_services=proxy private_database=true admin_mutations=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
