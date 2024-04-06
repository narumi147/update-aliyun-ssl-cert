"""
通过acme.sh签发通配符域名的SSL证书并设置改脚本为renew hook
上传证书至阿里云->替换CDN或DCDN的证书->删除旧证书

Usage: python main.py --config path/to/config.json --delete-old-cert
"""

import argparse
from datetime import datetime
from pathlib import Path

from sslcert.ali_api import AliApi
from sslcert.logger import logger
from sslcert.settings import Config, settings


def main(config_fp: Path, delete_old_cert: bool):
    config = Config.model_validate_json(config_fp.read_bytes())

    Le_Domain = settings.Le_Domain or config.Le_Domain
    CERT_KEY_PATH = settings.CERT_KEY_PATH or config.CERT_KEY_PATH
    CERT_FULLCHAIN_PATH = settings.CERT_FULLCHAIN_PATH or config.CERT_FULLCHAIN_PATH

    domain_config = config.domains.get(Le_Domain) if Le_Domain else None
    if domain_config is None:
        raise Exception(f"config not found for domain {Le_Domain}")

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

    # get existing cert list with matching domain name
    cert_list = [cert for cert in ali_api.list_cert() if cert.common_name == Le_Domain]

    # create cert
    cert_name = (
        Le_Domain.replace(".", "_") + "-" + datetime.now().strftime("%Y%m%d-%H%M%S")
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

    # update CDN/DCDN cert
    for domain in domain_config.CDN_DOMAINS:
        ali_api.set_cdn_cert(domain_name=domain, cert_id=cert_id, cert_name=cert_name)
        logger.info(f'Set CDN cert for "{domain}": {cert_id} {cert_name}')

    for domain in domain_config.DCDN_DOMAINS:
        ali_api.set_dcdn_cert(domain_name=domain, cert_id=cert_id, cert_name=cert_name)
        logger.info(f'Set DCDN cert for "{domain}": {cert_id} {cert_name}')

    # deleted unused cert
    if delete_old_cert:
        cert_to_delete = [
            cert
            for cert in cert_list
            if cert.common_name == Le_Domain and cert.certificate_id != cert_id
        ]
        if cert_to_delete:
            del_cert_id = cert_to_delete[0].certificate_id
            assert del_cert_id
            ali_api.delete_cert(del_cert_id)
            logger.warning(f"Deleted cert {del_cert_id}: {cert_to_delete[0].to_map()}")


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
    main(Path(args.config), args.delete_old_cert)
