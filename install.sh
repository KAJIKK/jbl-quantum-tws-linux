#!/usr/bin/env bash
# Installation script for JBL Quantum TWS Battery Monitor on Linux

set -euo pipefail

APP_NAME="jbl-quantum-tws-linux"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
UDEV_RULES_DIR="/etc/udev/rules.d"

echo "=== JBL Quantum TWS Monitor Installer ==="
echo

# 1. Install Udev rules
echo "1. Installing udev rules (requires sudo)..."
sudo cp "${ROOT_DIR}/99-jbl-quantum-tws.rules" "${UDEV_RULES_DIR}/"
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "✓ Udev rule installed successfully."
echo

# 2. Copy application files
echo "2. Installing application files..."
mkdir -p "${INSTALL_DIR}"
cp -f "${ROOT_DIR}/jbl_quantum_tws_tray.py" "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/jbl_quantum_tws_tray.py"
echo "✓ Copied script to ${INSTALL_DIR}/jbl_quantum_tws_tray.py"
echo

# 3. Setup systemd user service
echo "3. Setting up systemd autostart service..."
mkdir -p "${SYSTEMD_DIR}"
cp -f "${ROOT_DIR}/jbl-quantum-tws-tray.service" "${SYSTEMD_DIR}/"
echo "Reloading user systemd daemon..."
systemctl --user daemon-reload
echo "Enabling and starting systemd service..."
systemctl --user enable jbl-quantum-tws-tray.service
systemctl --user restart jbl-quantum-tws-tray.service
echo "✓ Autostart service configured and started."
echo

echo "========================================="
echo "Installation complete!"
echo "The system tray monitor is now running and will auto-start when you log in."
echo
echo "⚠️ IMPORTANT: Please put the headphones into their charging case"
echo "   and pull them back out again to initialize the connection status!"
echo "========================================="
