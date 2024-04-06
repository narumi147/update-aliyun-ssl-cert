# Update Aliyun SSL Cert

使用 [acme.sh](https://github.com/acmesh-official/acme.sh) 签发通配符域名(`example.com`,`*.example.com`)，并通过本脚本上传至阿里云服务器

## Env

以下环境变量由`acme.sh`自动设置，若需手动运行脚本，可手动设置环境变量后运行。(也可在`config.json`中设置)

- `CERT_PATH`: 非必需
- `CERT_KEY_PATH`
- `CA_CERT_PATH`: 非必需
- `CERT_FULLCHAIN_PATH`
- `Le_Domain`

## config.json

可以设置多组域名的 AccessKey 和要更新的 CDN 和 DCDN(全站加速)域名，运行时只更新`Le_Domain`这一组的证书。

```json
{
  "domains": {
    "example.com": {},
    "another.com": {}
  }
}
```

## renew-hook

新建`update_ssl_cert.sh`

```bash
/path/to/python main.py --config path/to/config.json --delete-old-cert
```

运行`acme.sh`签署新证书并设置 renew hook

```bash
acme.sh --issue --dns dns_ali -d example.com -d "*.example.com" --renew-hook /path/to/update_ssl_cert.sh
```

## Aliyun 建立 RAM 用户并授权

新建一个 OpenAPI 调用权限的 RAM 用户，添加以下权限:

- AliyunDNSFullAccess: 管理云解析（DNS）的权限, acme.sh 用到
- AliyunYundunCertFullAccess: 管理云盾证书服务的权限
- AliyunCDNFullAccess: 管理 CDN 的权限
- AliyunDCDNFullAccess: 管理 DCDN 的权限

## References

- <https://www.wqy.ac.cn/p/2311-acme-aliyuncdn/>
