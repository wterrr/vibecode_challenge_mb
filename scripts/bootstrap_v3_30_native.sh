#!/usr/bin/env bash
# V3-30 shared native AV setup: executes on *both* free/offline and paid runners.
# A hung package manager must fail clearly before any external model is invoked.
set -Eeuo pipefail
stage="start"
trap 'rc=$?; echo "::error title=V3-30 native dependency failure::stage=${stage} exit=${rc}"; exit "$rc"' ERR

native_ready() {
  command -v ffmpeg >/dev/null 2>&1 || return 1
  command -v espeak-ng >/dev/null 2>&1 || return 1
  command -v fc-match >/dev/null 2>&1 || return 1
  local family
  family="$(fc-match -f '%{family}' 'CMU Serif')" || return 1
  [[ "${family,,}" == *cmu* ]]
}

echo "V330_NATIVE_DEPS=START"
if native_ready; then
  echo "V330_NATIVE_DEPS=ALREADY_INSTALLED"
else
  stage="apt-update"
  echo "V330_NATIVE_DEPS=APT_UPDATE timeout=120s"
  timeout -k 10s 120s sudo apt-get \
    -o Acquire::Retries=0 -o Acquire::http::Timeout=20 \
    -o Acquire::https::Timeout=20 update -qq
  stage="apt-install"
  echo "V330_NATIVE_DEPS=APT_INSTALL timeout=360s no-recommends"
  timeout -k 10s 360s sudo env DEBIAN_FRONTEND=noninteractive \
    apt-get -o DPkg::Lock::Timeout=30 -o Acquire::Retries=0 \
    -y -qq --no-install-recommends install ffmpeg espeak-ng fonts-cmu fontconfig
fi
stage="verify"
echo "V330_NATIVE_DEPS=VERIFY"
if ! native_ready; then
  echo "::error title=V3-30 native dependency failure::required FFmpeg, eSpeak NG and CMU Serif font not found"
  exit 2
fi
command -v ffmpeg
command -v espeak-ng
fc-match -f '%{family}\n' 'CMU Serif'
echo "V330_NATIVE_DEPS=PASS"
