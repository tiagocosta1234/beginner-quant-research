#!/bin/bash
# Round 347 cloud setup: MetaTrader 5 under Wine in a Claude Code cloud container (Linux), portable mode, ready for cloud_run.py.
#   bash forex/early_mt5/ea_batch/cloud_setup.sh            # ~10 minutes; idempotent
# Needs outbound access to download.mql5.com and the MT5 broker trade server; credentials come from the environment
# (MT5BROKER_MT5_LOGIN, MT5BROKER_MT5_PASSWORD, MT5BROKER_MT5_SERVER), never from files in the repo.
set -euo pipefail
ROOT=${EA_CLOUD_ROOT:-/root/mt5cloud}
export WINEPREFIX=$ROOT/prefix WINEDEBUG=-all
MT="$WINEPREFIX/drive_c/Program Files/MetaTrader 5"
mkdir -p "$ROOT"
if ! command -v wine >/dev/null; then
  dpkg --add-architecture i386 || true
  DEBIAN_FRONTEND=noninteractive apt-get -qq update
  DEBIAN_FRONTEND=noninteractive apt-get -y -qq install wine64 wine winbind cabextract xvfb >/dev/null
fi
if [ ! -f "$MT/terminal64.exe" ]; then
  curl -sS --max-time 300 -o "$ROOT/mt5setup.exe" https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
  timeout 300 xvfb-run -a wineboot -i >/dev/null 2>&1 || true
  timeout 900 xvfb-run -a wine "$ROOT/mt5setup.exe" /auto >/dev/null 2>&1 || true
fi
[ -f "$MT/terminal64.exe" ] || { echo "MT5 install failed"; exit 1; }
if [ ! -f "$MT/MQL5/Include/Trade/Trade.mqh" ]; then          # first start unpacks the MQL5 standard library
  (cd "$MT" && timeout 150 xvfb-run -a wine terminal64.exe /portable >/dev/null 2>&1 || true)
  wineserver -k || true
fi
FT="$WINEPREFIX/drive_c/Program Files/MT5 broker Global Markets MT5 Terminal"
if [ ! -f "$FT/Config/servers.dat" ]; then                    # the MetaQuotes build does not know MT5 broker-Demo; MT5 broker's own build ships its server list
  curl -sS -L --max-time 300 -o "$ROOT/mt5broker5setup.exe" https://download.terminal.free/cdn/web/mt5broker.global.markets/mt5/mt5broker5setup.exe
  timeout 900 xvfb-run -a wine "$ROOT/mt5broker5setup.exe" /auto >/dev/null 2>&1 || true
  wineserver -k || true
fi
[ -f "$FT/Config/servers.dat" ] || { echo "MT5 broker server list missing"; exit 1; }
[ -f "$MT/Config/servers.dat.metaquotes" ] || cp "$MT/Config/servers.dat" "$MT/Config/servers.dat.metaquotes"
cp "$FT/Config/servers.dat" "$MT/Config/servers.dat"
mkdir -p "$WINEPREFIX/drive_c/ea"
echo "MT5 ready at $MT"
