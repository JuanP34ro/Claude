#!/bin/sh
cd "$(dirname "$0")" || exit 1
printf 'Este modo permite acceso desde la red local, sin contraseña. Solo usa una red de confianza.\nContinuar [s/N]? '
read -r answer
case "$answer" in s|S) exec python3 server.py --lan ;; *) exit 0 ;; esac
