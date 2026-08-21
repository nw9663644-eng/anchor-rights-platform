#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ufw fail2ban unattended-upgrades

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

sudo systemctl enable --now fail2ban
sudo systemctl enable --now unattended-upgrades

sudo nginx -t
sudo systemctl reload nginx

echo "Firewall, Fail2ban, automatic security updates, and Nginx checks are enabled."
