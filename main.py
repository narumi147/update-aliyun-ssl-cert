"""
通过acme.sh签发证书并使用deploy hook调用本脚本
上传证书至阿里云->替换CDN或DCDN的证书->删除旧证书

Usage: python main.py --config path/to/config.json --delete-old-cert
"""

import argparse
from datetime import datetime
from pathlib import Path

from sslcert.ali_api import AliApi
from sslcert.cleanup import cleanup_old_certificates
from sslcert.logger import logger
from sslcert.settings import Config, settings


def main(config_fp: Path, delete_old_cert: bool) -> int:
    config = Config.model_validate_json(config_fp.read_bytes())

    Le_Domain = settings.Le_Domain or config.Le_Domain
    CERT_KEY_PATH = settings.CERT_KEY_PATH or config.CERT_KEY_PATH
    CERT_FULLCHAIN_PATH = settings.CERT_FULLCHAIN_PATH or config.CERT_FULLCHAIN_PATH

    domain_config = config.domains.get(Le_Domain) if Le_Domain else None
    if domain_config is None:
        raise ValueError(f"config not found for domain {Le_Domain}")

    assert (
        domain_config.AliAccessKeyId
        and domain_config.AliAccessKeySecret
        and Le_Domain
        and CERT_KEY_PATH
        and CERT_FULLCHAIN_PATH
    )

    logger.info(
        f'Updating ssl certs for "{Le_Domain}",'
        f" {len(domain_config.CDN_DOMAINS)} CDN domains, {len(domain_config.DCDN_DOMAINS)} DCDN domains"
    )

    ali_api = AliApi(domain_config.AliAccessKeyId, domain_config.AliAccessKeySecret)

    # create cert
    cert_name = (
        Le_Domain.replace(".", "_")
        + "-"
        + datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    )

    cert_fullchain = Path(CERT_FULLCHAIN_PATH).read_text()
    cert_fullchain = "\n".join(
        [line for line in cert_fullchain.splitlines() if line.strip()]
    )

    cert_key = Path(CERT_KEY_PATH).read_text()

    cert_id = ali_api.upload_cert(
        cert_name=cert_name, cert=cert_fullchain, key=cert_key
    )
    logger.info(f'Uploaded cert "{cert_name}" with ID {cert_id}')

    failed_domains = []
    for product, domains, set_cert in (
        ("CDN", domain_config.CDN_DOMAINS, ali_api.set_cdn_cert),
        ("DCDN", domain_config.DCDN_DOMAINS, ali_api.set_dcdn_cert),
    ):
        for domain in domains:
            try:
                set_cert(domain_name=domain, cert_id=cert_id, cert_name=cert_name)
            except Exception as error:  # noqa: BLE001 - Continue with other domains.
                logger.error(f'Failed to set {product} cert for "{domain}": {error}')
                failed_domains.append(f"{product}:{domain}")
                continue
            logger.info(f'Set {product} cert for "{domain}": {cert_id} {cert_name}')

    if failed_domains:
        logger.error(
            f"Certificate deployment completed with {len(failed_domains)} failures: "
            + ", ".join(failed_domains)
        )
    if delete_old_cert:
        try:
            cleanup_old_certificates(ali_api, Le_Domain, cert_id)
        except Exception as error:  # noqa: BLE001 - Cleanup is explicitly best-effort.
            logger.warning(
                f"Certificate cleanup failed after deployment attempts: {error}"
            )
    return 1 if failed_domains else 0


if __name__ == "__main__":
    logger.info(f"working directory: {Path.cwd().resolve()}")

    parser = argparse.ArgumentParser(description="Update Aliyun SSL Cert")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to config.json",
        required=False,
        default="config.json",
    )
    parser.add_argument(
        "--delete-old-cert",
        action="store_true",
        default=False,
        help="whether to delete the old cert, default False",
    )

    args = parser.parse_args()
    raise SystemExit(main(Path(args.config), args.delete_old_cert))
