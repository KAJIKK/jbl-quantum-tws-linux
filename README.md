# JBL Quantum TWS Battery & Status Tray Monitor for Linux

A lightweight, native system tray utility designed to monitor the battery levels and status (microphone mute state, connection source, ANC modes) of **JBL Quantum TWS** wireless earbuds on Linux (KDE, GNOME, etc.) when connected via the 2.4GHz wireless USB-C dongle.

![Tray Icon Example](https://raw.githubusercontent.com/plugato/JBL_Baterry_Monitor/main/docs/tray_example.png) *(Optional screenshot reference)*

## 🌟 Features

*   **🔋 Battery Monitoring**: Decodes Left Earbud, Right Earbud, and Charging Case battery percentages.
*   **🎙️ Interactive Mic Control**: Toggle the microphone mute state directly by clicking on the tray action. The tray icon dynamically switches to a **crossed-out red microphone** when muted.
*   **🎧 ANC Mode Control**: Change active ANC profiles directly from the tray (ANC On, Full Passthrough, Ambient Aware, or Off).
*   **📶 Audio Source Control**: Toggle between **2.4GHz Dongle** and **Bluetooth** connections directly from the tray menu, forcing the headset to switch its active link.
*   **⚙️ Background Service**: Integrates as a systemd user service to launch automatically on login.

---

## 🛠️ Prerequisites

Make sure you have `python3`, `pyqt5`, and `hid` (or `hidapi`) bindings installed.

### Ubuntu/Debian
```bash
sudo apt install python3-pyqt5 python3-pip
pip3 install hidapi --user
```

### Arch Linux / CachyOS
```bash
sudo pacman -S python-pyqt5 python-hidapi
```

---

## 🚀 Installation & Setup

I have provided a complete installation script that handles the udev configuration (to access the dongle without root/sudo) and the systemd auto-start service.

### 1) Clone this repository
```bash
git clone https://github.com/YOUR_USERNAME/jbl-quantum-tws-linux.git
cd jbl-quantum-tws-linux
```

### 2) Run the installer script
```bash
chmod +x install.sh
./install.sh
```

*(Note: The installer will prompt for sudo once to copy the udev rule to `/etc/udev/rules.d/`)*

---

## ⚙️ How to Manage the Service

Since it runs as a systemd user service, you can manage it without root privileges:

*   **Check Status**: `systemctl --user status jbl-quantum-tws-tray.service`
*   **Restart Service**: `systemctl --user restart jbl-quantum-tws-tray.service`
*   **Stop Service**: `systemctl --user stop jbl-quantum-tws-tray.service`
*   **Start Service**: `systemctl --user start jbl-quantum-tws-tray.service`
*   **Read Logs**: `journalctl --user -u jbl-quantum-tws-tray.service -f`

---

## 📊 Decoded Telemetry & Control Format

For details, the USB dongle uses the following report formats:

### Telemetry (Input Reports)
*   **Report ID `0x0b` (Battery status)**: `data[2]` = Left %, `data[4]` = Right %, `data[6]` = Case %
*   **Report ID `0x06` (Mic Mute status)**: `0x00` = Muted, `0x01` = Unmuted
*   **Report ID `0x09` (Connection mode status)**: `0x00` = Bluetooth / Headphones off, `0x01` = 2.4GHz Dongle
*   **Report ID `0x02` (ANC mode status)**: `0x00` = Off, `0x01` = ANC On, `0x02` = Full Passthrough, `0x03` = Ambient Aware

### Control
*   **Feature Report ID `0x46` (ANC Mode Control)**: Send `[0x46, mode_val]` where `mode_val` is `0x00` (Off), `0x01` (ANC On), `0x02` (Full Passthrough), or `0x03` (Ambient Aware / TalkThru).
*   **Feature Report ID `0x68` (Audio Source / Connection Mode Control)**: Send `[0x68, source_val]` where `source_val` is `0x00` (Bluetooth) or `0x01` (2.4GHz Dongle).
*   **Output Report ID `0x2f` (Mic Mute Control)**: Write `[0x2f, mute_val]` where `mute_val` is `0x02` (Mute) or `0x04` (Unmute).

---

## 📄 License

This project is licensed under the MIT License.
