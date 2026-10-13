"""Delete uploaded certificates within the explicitly selected domain scope."""

import re

from .ali_api import AliApi
from .logger import logger


def _normalize_domain(domain: str) -> str:
    domain = domain.strip().removesuffix(".").lower()
    wildcard = domain.startswith("*.")
    name = domain[2:] if wildcard else domain
    if len(name) > 253 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in name.split(".")
    ):
        raise ValueError(f"Invalid certificate domain: {domain!r}")
    return "*." + name if wildcard else name


def _certificate_domains(sans: str | None) -> set[str]:
    if not sans:
        raise ValueError("Certificate is missing its complete SAN domain list")
    return {_normalize_domain(domain) for domain in sans.split(",")}


def _belongs_to_domain(name: str, root: str) -> bool:
    name = name.removeprefix("*.")
    return name == root or name.endswith("." + root)


def cleanup_old_certificates(api: AliApi, domain: str, current_cert_id: int) -> None:
    """Cleanup errors are warnings and must not change a successful deployment."""
    try:
        root = _normalize_domain(domain).removeprefix("*.")
        certificates = api.list_cert()
    except Exception as error:  # noqa: BLE001
        logger.warning(f"Skipping certificate cleanup for {domain}: {error}")
        return

    # Fetch the new SAN list only when a valid old certificate needs comparison.
    current_domains = None
    current_domains_failed = False
    deleted_count = 0
    for certificate in certificates:
        cert_id = certificate.certificate_id
        if cert_id == current_cert_id:
            continue
        if not cert_id:
            logger.warning("Skipping certificate without an ID")
            continue

        try:
            domains = _certificate_domains(certificate.sans)
        except ValueError as error:
            logger.warning(f"Skipping cert {cert_id}: {error}")
            continue

        if not all(_belongs_to_domain(name, root) for name in domains):
            logger.info(f"Keeping cert {cert_id}: domains outside {root}")
            continue

        if certificate.expired is not True:
            if certificate.expired is not False:
                logger.warning(f"Skipping cert {cert_id}: missing expiration status")
                continue
            if current_domains_failed:
                continue
            if current_domains is None:
                try:
                    current = api.get_cert(current_cert_id)
                    if current.id != current_cert_id:
                        raise ValueError(
                            "Current certificate detail has a different ID"
                        )
                    current_domains = _certificate_domains(current.sans)
                except Exception as error:  # noqa: BLE001
                    logger.warning(f"Skipping unexpired certificate cleanup: {error}")
                    current_domains_failed = True
                    continue
            if not domains.issubset(current_domains):
                logger.info(f"Keeping cert {cert_id}: SAN domains are not a subset")
                continue

        try:
            api.delete_cert(cert_id)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Failed to delete cert {cert_id}: {error}")
            continue
        deleted_count += 1
        logger.info(f"Deleted cert {cert_id}, expired={certificate.expired}")

    logger.info(
        f"Certificate cleanup for {domain}: deleted {deleted_count} certificates"
    )
