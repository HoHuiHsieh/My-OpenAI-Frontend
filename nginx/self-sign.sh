#!/bin/bash
# self-sign.sh
# Generate a self-signed SSL certificate for Nginx.

openssl req \
    -x509   \
    -new    \
    -nodes  \
    -sha256 \
    -utf8   \
    -days 1 \
    -newkey rsa:2048 \
    -keyout nginx.key \
    -out nginx.crt \
    -config self-sign.conf