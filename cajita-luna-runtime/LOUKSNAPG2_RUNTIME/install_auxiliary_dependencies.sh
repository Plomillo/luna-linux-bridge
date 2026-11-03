#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "RUN_WITH_SUDO: sudo bash install_auxiliary_dependencies.sh" >&2
  exit 2
fi

if [[ ! -r /etc/os-release ]]; then
  echo "OS_RELEASE_UNAVAILABLE" >&2
  exit 3
fi
. /etc/os-release
case "${ID:-}" in
  debian|ubuntu) ;;
  *) echo "UNSUPPORTED_PACKAGE_FAMILY:${ID:-unknown}" >&2; exit 4 ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  apertium \
  apertium-eng-spa \
  apertium-fr-es \
  tesseract-ocr \
  tesseract-ocr-eng

command -v apertium
command -v tesseract
apertium --version | head -n 1
tesseract --version | head -n 1

echo "LOUKSNAPG2_AUXILIARY_HOST_DEPENDENCIES=PASS"
echo "WHISPER_CPP_AND_GGML_TINY_ARE_BUNDLED_SEPARATELY"
echo "ORIGINAL_CAJITA_WEIGHTS_WERE_NOT_MODIFIED"
