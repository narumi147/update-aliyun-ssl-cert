#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <example.com>"
    exit 1
fi

domain=$1
home_path=$HOME
cert_folder="${home_path}/.acme.sh/${domain}_ecc"

export CERT_PATH="${cert_folder}/${domain}.cer"
export CERT_KEY_PATH="${cert_folder}/${domain}.key"
export CA_CERT_PATH="${cert_folder}/ca.cer"
export CERT_FULLCHAIN_PATH="${cert_folder}/fullchain.cer"
export Le_Domain="${domain}"

echo "CERT_PATH=$CERT_PATH"
echo "CERT_KEY_PATH=$CERT_KEY_PATH"
echo "CA_CERT_PATH=$CA_CERT_PATH"
echo "CERT_FULLCHAIN_PATH=$CERT_FULLCHAIN_PATH"
echo "Le_Domain=$Le_Domain"
