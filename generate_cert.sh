#!/bin/bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes -subj "/C=JP/ST=Tokyo/L=Minato/O=MyOrg/CN=localhost"
echo "Self-signed certificate generated in certs/"
