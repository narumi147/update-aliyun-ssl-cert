# Update Aliyun SSL Cert

通过本项目将 [acme.sh](https://github.com/acmesh-official/acme.sh) 已签发的证书上传至阿里云数字证书管理服务，再部署到指定的 CDN 和 DCDN 域名。

使用自定义 `deploy-hook` 调用本项目，不依赖内置的 `ali_cdn` / `ali_dcdn` 插件。已有证书可以直接接入和手动部署，无需重新 `--issue` 或强制续期。以下流程按 acme.sh **3.1.4** 核对。

## Python 环境

本项目采用宿主机 Python + 项目虚拟环境（venv）运行，保留阿里云 SDK。宿主机负责安装 Python，项目依赖安装到 `.venv`，由 acme.sh 的自定义 deploy-hook 调用该环境的解释器。

以下假设项目安装在服务器的 `/opt/tools/update-aliyun-ssl-cert`，请替换为实际路径。在运行 acme.sh 的服务器上，使用 Python 3.12 创建虚拟环境并安装锁定依赖：

```bash
cd /opt/tools/update-aliyun-ssl-cert
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip check
```

安装命令由运行 acme.sh 的用户执行；该用户还需能读取证书和配置，并能在项目目录下创建、写入 `logs/`。首次部署前准备好虚拟环境，后续 hook 直接调用 `./.venv/bin/python`，无需 `activate`，也不在续期时安装或更新依赖。

服务器只需用 pip 安装仓库提供的 `requirements.txt`，无需安装 Poetry。依赖由开发环境的 `pyproject.toml` 和 `poetry.lock` 管理；更新依赖后，在开发环境重新导出安装清单并提交，再在服务器显式安装更新后的清单：

```bash
poetry export --without-hashes -f requirements.txt -o requirements.txt
```

## config.json

在项目目录创建 `config.json`。可以设置多组证书主域名，运行时只更新 `Le_Domain` 对应的配置组。以下为 `chaldea.center` 的示例，AccessKey 请填入实际值：

```json
{
  "domains": {
    "chaldea.center": {
      "AliAccessKeyId": "YOUR_ACCESS_KEY_ID",
      "AliAccessKeySecret": "YOUR_ACCESS_KEY_SECRET",
      "CDN_DOMAINS": [
        "cn.chaldea.center",
        "data-cn.chaldea.center",
        "disk-dl.chaldea.center"
      ],
      "DCDN_DOMAINS": [
        "api.chaldea.center",
        "api-cn.chaldea.center",
        "master.chaldea.center",
        "worker-cn.chaldea.center",
        "countly.chaldea.center",
        "disk.chaldea.center",
        "api.atlas.chaldea.center",
        "static.atlas.chaldea.center"
      ]
    }
  }
}
```

从内置插件迁移时，将原来的空格分隔域名列表转为上述 JSON 数组：

| acme.sh 域名配置 | 本项目配置 |
| --- | --- |
| `SAVED_DEPLOY_ALI_CDN_DOMAIN` | `CDN_DOMAINS` |
| `SAVED_DEPLOY_ALI_DCDN_DOMAIN` | `DCDN_DOMAINS` |

本项目不会自动读取内置插件的 `SAVED_DEPLOY_*` 配置或 AccessKey，需在 `config.json` 中设置。该文件已被 `.gitignore` 排除。

### 泛域名加速的写法

`CDN_DOMAINS` / `DCDN_DOMAINS` 填写的是阿里云已接入的加速域名名称，脚本会原样传给部署接口。例如控制台中的泛域名为 `.srv.tsupolymer.com`，则配置填写 `.srv.tsupolymer.com`；证书自身的 SAN 则应包含 `*.srv.tsupolymer.com`。加速域名标识与证书 SAN 使用不同写法，清理时比较的是证书 SAN。

阿里云的 [DCDN 域名接口](https://help.aliyun.com/zh/edge-security-acceleration/dcdn/developer-reference/api-dcdn-2018-01-15-adddcdndomain) 使用点号开头的泛域名表示；[acme.sh 阿里云部署说明](https://github.com/acmesh-official/acme.sh/wiki/deployhooks#35-deploy-your-certificate-to-cdn-or-dcdn-of-alibaba-cloud-aliyun) 也使用 `.example.com` 作为部署目标。建议按控制台或域名查询 API 返回的名称填写，而不是用证书的 `*.example.com` 替换部署目标。

## 自定义 deploy-hook

### 安装适配脚本

仓库根目录已提供 `aliyun_custom.sh`，默认使用 `/opt/tools/update-aliyun-ssl-cert` 下的 `.venv`，并启用 `--delete-old-cert`。安装路径不同时，先修改该文件中的 `cd` 路径。

使用运行 acme.sh 的用户，在其安装目录下建立软链接。目录名为 `deploy`，不是 `deplot`。若已有同名 hook，先备份移走（仅首次迁移时执行；`-i` 会在备份已存在时询问是否覆盖）：

```bash
mv -i "$HOME/.acme.sh/deploy/aliyun_custom.sh" \
  "$HOME/.acme.sh/deploy/aliyun_custom.sh.before-repo-link"
```

如果尚无同名 hook，跳过上述备份命令。随后建立链接：

```bash
ln -s /opt/tools/update-aliyun-ssl-cert/aliyun_custom.sh \
  "$HOME/.acme.sh/deploy/aliyun_custom.sh"
```

位置参数是 acme.sh 的 deploy-hook 接口：它将域名、私钥、叶证书、CA、完整证书链依次传给 `<插件名>_deploy` 函数（另有第六个 PFX 参数，本项目不使用）。适配脚本将它们转换为本项目使用的环境变量，并将 Python 的退出码传回 acme.sh。不要将它与直接导出环境变量的 `renew-hook` / `reloadcmd` 混用。`--deploy-hook` 接收的是插件名 `aliyun_custom`，不是脚本路径。

acme.sh 会跟随软链接加载函数，hook 文件只需可读，无需执行权限。以后直接更新仓库中的 `aliyun_custom.sh`，后续部署便会加载修改后的内容。如果已经登记了 `aliyun_custom`，无需重复登记；首次登记或从其他插件切换时，执行下一节的 `--deploy --deploy-hook aliyun_custom` 命令。

### 已有证书迁移并立即部署

先安装适配脚本并填写 `config.json`，再查看已有证书的配置：

```bash
acme.sh --info -d chaldea.center --ecc
```

`Le_Keylength='ec-256'` 表示 ECC 证书，应使用 `--ecc`；RSA 证书去掉该选项。使用证书主域名 `chaldea.center` 即可，不需要再次传入泛域名。

备份 `--info` 输出的 `DOMAIN_CONF` 文件。默认 ECC 配置路径为：

```bash
cp -p "$HOME/.acme.sh/chaldea.center_ecc/chaldea.center.conf" \
  "$HOME/.acme.sh/chaldea.center_ecc/chaldea.center.conf.before-aliyun-custom"
```

如果配置中已有 `Le_RenewHook` 调用本项目，将该项清空为 `Le_RenewHook=''`，避免续期时重复上传。随后运行：

```bash
acme.sh --deploy \
  -d chaldea.center \
  --ecc \
  --deploy-hook aliyun_custom
```

该命令立即部署**当前证书**，并将原来的 `Le_DeployHook='ali_cdn,'`、`'ali_dcdn,'` 或两者组合整体替换为 `Le_DeployHook='aliyun_custom,'`。无需 `--issue`、`--renew` 或 `--force`。

保存新 hook 发生在执行部署之前；即使部署失败，配置也已切换。修复报错后重新执行上面的部署命令。`SAVED_DEPLOY_ALI_CDN_DOMAIN` / `SAVED_DEPLOY_ALI_DCDN_DOMAIN` 可以暂时保留，新插件不会使用它们。

官方 3.1.4 的 `ali_cdn` 和 `ali_dcdn` 是两个独立插件：仅登记 `ali_cdn` 时，即使保存了 DCDN 域名列表，也不会调用 `ali_dcdn`。本项目通过 `config.json` 同时管理两类目标。

### 保留 Caddy 安装与 reload

迁移时保留现有的 `Le_RealKeyPath`、`Le_RealFullChainPath` 和 `Le_ReloadCmd`。例如，仍使用以下安装路径：

```text
Le_RealKeyPath: /opt/docker/caddy/ssl/chaldea.center/privkey.pem
Le_RealFullChainPath: /opt/docker/caddy/ssl/chaldea.center/fullchain.pem
```

已有 `Le_ReloadCmd` 解码后的命令为：

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

自定义插件只负责阿里云部署。手动 `--deploy` 不会复制 Caddy 证书文件或执行 reload；后续正常续期成功时，acme.sh 会依次安装证书并 reload Caddy、执行 post/renew hook、执行保存的 deploy-hook。前面的步骤失败时，后续部署不会执行。

无需为迁移重新运行 `--install-cert`；该命令会重新保存安装配置，遗漏原有路径参数会清空对应路径。也无需修改已有的 `Le_Webroot='dns_cf'`、ZeroSSL 服务地址或证书签发参数。

### 手动重部署与验证

之后要再次部署现有证书，重复运行同一条命令：

```bash
acme.sh --deploy -d chaldea.center --ecc --deploy-hook aliyun_custom
```

检查命令退出码和项目的 `logs/sslcert.log`，并在阿里云控制台确认目标 CDN/DCDN 域名绑定的新证书。可再次运行 `acme.sh --info -d chaldea.center --ecc`，确认 `Le_DeployHook` 已替换且 Caddy 配置保留。

每次部署都会向阿里云上传一份证书，添加 `managed-by=acme.sh` 标签，并使用返回的证书 ID 部署到目标域名。

### 旧证书清理规则

Python CLI 的 `--delete-old-cert` 默认关闭；仓库提供的 `aliyun_custom.sh` 会显式开启它。全部配置域名的部署调用尝试结束后，查询并清理旧证书；部分域名部署失败也会执行清理。清理规则如下：

1. 查询全部分页的有效及过期上传证书，始终保留本次上传的证书 ID。
2. 首先仅以 `CommonName` 判断是否属于本次 `Le_Domain` 或其子域名，不自动推断公共后缀；例如 `*.atlas.chaldea.center` 属于 `chaldea.center` 的范围。范围外、缺失或无效的 `CommonName` 静默跳过。随后在循环内检查完整 `Sans`，全部 SAN 域名都必须属于该范围；跨根域名证书保留，即使已过期。
3. 范围内的过期证书删除，不要求其 SAN 是新证书的子集。
4. 范围内的未过期证书，仅在 SAN 域名集合为新证书 SAN 域名集合的子集时删除。比较忽略域名大小写和单个末尾句点；按域名项比较，不展开通配符。旧证书的 `api.chaldea.center` 不等同于新证书的 `*.chaldea.center`。
5. 不检查标签或上传来源，可以删除内置 hook、其他工具或人工上传的多张证书；不查询 CDN/DCDN 或其他云产品的引用关系。

SAN 信息无效或缺失、过期状态未知的候选会跳过。完整列表查询失败时跳过本次清理；新证书 SAN 查询失败时保留未过期候选，已过期候选仍按上述范围规则处理。单张删除失败记 WARNING 并继续处理其他证书，清理错误不改变已成功部署的退出码。

单个 CDN/DCDN 域名部署失败时，记录包含产品、域名和接口错误的 ERROR，继续处理其余域名。全部域名处理结束后汇总失败项，并在开启 `--delete-old-cert` 时继续清理旧证书；存在部署失败时，脚本在清理结束后返回退出码 1。上传失败仍直接终止并返回非零退出码；全部域名部署成功则返回 0，清理警告不改变该结果。失败域名可能仍使用旧证书，清理不会额外检查其引用关系。

因此，清理成功不表示所有云产品都已停止使用旧证书。核对清理日志中的实际删除及跳过结果；要只上传和部署，可以直接运行不带 `--delete-old-cert` 的 Python 命令。

### 手动设置环境变量并模拟 deploy-hook

使用运行 acme.sh 的同一个用户执行。下面假设证书主域名为 `chaldea.center`，使用默认 ECC 证书目录；RSA 证书目录去掉 `_ecc`，自定义证书目录则填写实际路径。

```bash
(
  export Le_Domain='chaldea.center'
  cert_dir="$HOME/.acme.sh/${Le_Domain}_ecc"
  export CERT_KEY_PATH="$cert_dir/$Le_Domain.key"
  export CERT_PATH="$cert_dir/$Le_Domain.cer"
  export CA_CERT_PATH="$cert_dir/ca.cer"
  export CERT_FULLCHAIN_PATH="$cert_dir/fullchain.cer"

  . "$HOME/.acme.sh/deploy/aliyun_custom.sh" || exit 1
  aliyun_custom_deploy \
    "$Le_Domain" \
    "$CERT_KEY_PATH" \
    "$CERT_PATH" \
    "$CA_CERT_PATH" \
    "$CERT_FULLCHAIN_PATH"
)
echo "deploy exit code: $?"
```

这会加载并调用与 acme.sh 相同的 hook 函数，实际上传、部署并按规则清理旧证书；不是 dry-run，也不会签发或续期证书。它不会登记 deploy-hook 或更新 acme.sh 的部署记录；首次接入仍需执行 `acme.sh --deploy --deploy-hook aliyun_custom`。子 Shell 内的环境变量不会影响当前终端。

仅执行 `sh ~/.acme.sh/deploy/aliyun_custom.sh` 会定义函数但不调用它。仅 export 变量后无参数调用 `aliyun_custom_deploy` 也不适用：函数会用空的位置参数覆盖传给 Python 的环境变量。

## 环境变量与直接运行

自定义 deploy-hook 通过位置参数显式设置以下环境变量；`renew-hook` / `reloadcmd` 则由 acme.sh 直接导出这些变量：

| 变量 | 用途 |
| --- | --- |
| `Le_Domain` | 必需，选择 `config.json` 中的证书主域名配置组 |
| `CERT_KEY_PATH` | 必需，私钥路径 |
| `CERT_FULLCHAIN_PATH` | 必需，完整证书链路径 |
| `CERT_PATH` | 可选，叶证书路径 |
| `CA_CERT_PATH` | 可选，CA 证书路径 |

也可以在 `config.json` 顶层填写这些值。环境变量优先于 `config.json`。

如果只想直接运行 Python 脚本，可以在项目目录执行：

```bash
cd /opt/tools/update-aliyun-ssl-cert
source ./export_env.sh chaldea.center
./.venv/bin/python ./main.py --config ./config.json
```

`export_env.sh` 当前使用运行用户的默认 ECC 证书目录 `~/.acme.sh/<domain>_ecc`；使用 RSA 或自定义证书目录时，请自行设置实际路径。直接运行 Python 不会替换 acme.sh 保存的 deploy-hook。

## Aliyun 权限管理

新建一个 OpenAPI 调用权限的 RAM 用户，添加以下权限:

- AliyunYundunCertFullAccess: 管理云盾证书服务的权限
- AliyunCDNFullAccess: 管理 CDN 的权限
- AliyunDCDNFullAccess: 管理 DCDN 的权限

DNS 验证权限由签发证书时使用的 DNS 插件决定，与本项目的部署权限独立。现有 `dns_cf` 配置使用 Cloudflare；只有使用 `dns_ali` 时，才需要另行配置阿里云 DNS 权限（例如 `AliyunDNSFullAccess`）。

## References

- [acme.sh 3.1.4：deploy-hook 调用与登记](https://github.com/acmesh-official/acme.sh/blob/3.1.4/acme.sh#L6227-L6324)
- [acme.sh 3.1.4：续期后自动部署](https://github.com/acmesh-official/acme.sh/blob/3.1.4/acme.sh#L5891-L5895)
- [官方 deploy-hook 文档](https://github.com/acmesh-official/acme.sh/wiki/deployhooks)
- [原参考文章](https://www.wqy.ac.cn/p/2311-acme-aliyuncdn/)
