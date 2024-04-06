from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_cas20200407.client import Client as casClient
from alibabacloud_cdn20180510 import models as cdn_models
from alibabacloud_cdn20180510.client import Client as cdnClient
from alibabacloud_dcdn20180115 import models as dcdn_models
from alibabacloud_dcdn20180115.client import Client as dcdnClient
from alibabacloud_tea_openapi import models as open_api_models

from .utils import print_aliapi_params, validate_tea_resp

int64 = int

casClient.call_api = print_aliapi_params(casClient.call_api)
cdnClient.call_api = print_aliapi_params(cdnClient.call_api)
dcdnClient.call_api = print_aliapi_params(dcdnClient.call_api)


class AliApi:
    def __init__(self, key_id: str, key_secret: str) -> None:
        self.key_id = key_id
        self.key_secret = key_secret

    def get_base_config(self):
        return open_api_models.Config(
            access_key_id=self.key_id,
            access_key_secret=self.key_secret,
        )

    # https://help.aliyun.com/zh/ssl-certificate/developer-reference/api-cas-2020-04-07-listusercertificateorder
    def list_cert(
        self,
    ) -> list[cas_models.ListUserCertificateOrderResponseBodyCertificateOrderList]:
        config = self.get_base_config()
        config.endpoint = "cas.aliyuncs.com"
        client = casClient(config)

        request = cas_models.ListUserCertificateOrderRequest(
            order_type="UPLOAD", current_page=1, show_size=100
        )
        response = client.list_user_certificate_order(request)

        validate_tea_resp(response)

        return response.body.certificate_order_list

    # https://help.aliyun.com/zh/ssl-certificate/developer-reference/api-cas-2020-04-07-uploadusercertificate
    def upload_cert(self, cert_name: str, cert: str, key: str) -> int64:
        """
        return cert_id
        """
        config = self.get_base_config()
        config.endpoint = "cas.aliyuncs.com"
        client = casClient(config)

        request = cas_models.UploadUserCertificateRequest(
            name=cert_name,  # 字母数字下划线中划线
            cert=cert,  # PEM 格式证书内容
            key=key,  # PEM 格式证书的私钥内容
        )
        response = client.upload_user_certificate(request)

        validate_tea_resp(response)
        assert response.body.cert_id, "CertId not found"

        return response.body.cert_id

    # https://help.aliyun.com/zh/ssl-certificate/developer-reference/api-cas-2020-04-07-deleteusercertificate
    def delete_cert(self, cert_id: int) -> cas_models.DeleteUserCertificateResponseBody:
        config = self.get_base_config()
        config.endpoint = "cas.aliyuncs.com"
        client = casClient(config)

        request = cas_models.DeleteUserCertificateRequest(cert_id=cert_id)
        response = client.delete_user_certificate(request)

        validate_tea_resp(response)

        return response.body

    # https://help.aliyun.com/zh/cdn/developer-reference/api-cdn-2018-05-10-setcdndomainsslcertificate
    def set_cdn_cert(
        self,
        domain_name: str,
        cert_id: int64,
        cert_name: str,
    ) -> cdn_models.SetCdnDomainSSLCertificateResponseBody:
        config = self.get_base_config()
        config.endpoint = "cdn.aliyuncs.com"
        client = cdnClient(config)

        request = cdn_models.SetCdnDomainSSLCertificateRequest(
            domain_name=domain_name,
            cert_id=cert_id,
            cert_name=cert_name,
            cert_type="cas",
            sslprotocol="on",
        )
        response = client.set_cdn_domain_sslcertificate(request)

        validate_tea_resp(response)

        return response.body

    # https://help.aliyun.com/zh/dcdn/developer-reference/api-dcdn-2018-01-15-setdcdndomainsslcertificate
    def set_dcdn_cert(
        self,
        domain_name: str,
        cert_id: int64,
        cert_name: str,
    ) -> dcdn_models.SetDcdnDomainSSLCertificateResponseBody:
        config = self.get_base_config()
        config.endpoint = "dcdn.aliyuncs.com"
        client = dcdnClient(config)

        request = dcdn_models.SetDcdnDomainSSLCertificateRequest(
            domain_name=domain_name,
            cert_id=cert_id,
            cert_name=cert_name,
            cert_type="cas",
            sslprotocol="on",
        )
        response = client.set_dcdn_domain_sslcertificate(request)

        validate_tea_resp(response)

        return response.body
