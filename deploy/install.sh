#!/usr/bin/env bash
# Install CHC SOCIAL as a systemd timer that drains the post queue every 2 minutes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
sudo install -m 0644 "$HERE/chc-social-drain.service" /etc/systemd/system/
sudo install -m 0644 "$HERE/chc-social-drain.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chc-social-drain.timer
systemctl list-timers chc-social-drain.timer --no-pager
