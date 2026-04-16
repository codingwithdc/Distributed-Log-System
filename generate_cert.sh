#!/bin/bash
openssl req -new -x509 -days 365 -nodes -out server.crt -keyout server.key -subj "/CN=127.0.0.1"

