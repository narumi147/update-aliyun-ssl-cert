#!/bin/sh

aliyun_custom_deploy() (
  cd "/opt/tools/update-aliyun-ssl-cert" || exit 1

  Le_Domain="$1" \
  CERT_KEY_PATH="$2" \
  CERT_PATH="$3" \
  CA_CERT_PATH="$4" \
  CERT_FULLCHAIN_PATH="$5" \
    ./.venv/bin/python ./main.py --config ./config.json --delete-old-cert
)
