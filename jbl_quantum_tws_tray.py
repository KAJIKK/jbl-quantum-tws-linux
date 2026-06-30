#!/usr/bin/env python3
"""
JBL Quantum TWS - Battery and Status Monitor for Linux (KDE/GNOME System Tray)

This script uses USB HID communication to read telemetry data from the JBL
Quantum TWS USB dongle (VID 0x0ecb, PID 0x208a) and display the battery levels 
(Left, Right, Case), connection mode, mic mute status, and ANC settings 
in the Linux system tray.

License: MIT
"""

import sys
import os
import time
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QActionGroup
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
import hid

# Device Constants
VENDOR_ID = 0x0ecb
PRODUCT_ID = 0x208a

class JBLBatteryMonitor(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Initialize device states
        self.left_bat = -1
        self.right_bat = -1
        self.case_bat = -1
        self.mic_muted = False
        self.anc_mode = "Unknown"
        self.conn_mode = "2.4GHz Dongle"
        
        # Setup system tray icon
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.get_icon(connected=False))
        self.tray.setVisible(True)
        
        # Build tray context menu with forced white text color stylesheet for both active and disabled states
        self.menu = QMenu()
        self.menu.setStyleSheet("QMenu::item { color: white; } QMenu::item:disabled { color: white; }")
        self.setup_menu()
        self.tray.setContextMenu(self.menu)
        
        # Device handle
        self.device = None
        
        # Polling/listening timer (runs every 250ms for real-time responsiveness)
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_device)
        self.timer.start(250)
        
        # Initial poll
        self.poll_device()
        
    def setup_menu(self):
        """Builds the context menu structure for the tray icon."""
        self.title_action = QAction("JBL Quantum TWS (Disconnected)", self.menu)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)
        self.menu.addSeparator()
        
        # Interactive Audio Source Submenu
        self.source_menu = QMenu("Source: --", self.menu)
        self.menu.addMenu(self.source_menu)
        
        self.source_dongle_action = QAction("2.4GHz Dongle", self.source_menu, checkable=True)
        self.source_dongle_action.triggered.connect(lambda: self.set_audio_source(1))
        self.source_menu.addAction(self.source_dongle_action)
        
        self.source_bt_action = QAction("Bluetooth", self.source_menu, checkable=True)
        self.source_bt_action.triggered.connect(lambda: self.set_audio_source(0))
        self.source_menu.addAction(self.source_bt_action)
        
        self.source_group = QActionGroup(self)
        self.source_group.addAction(self.source_dongle_action)
        self.source_group.addAction(self.source_bt_action)
        
        # Interactive ANC Submenu
        self.anc_menu = QMenu("ANC Mode: --", self.menu)
        self.menu.addMenu(self.anc_menu)
        
        self.anc_off_action = QAction("Off", self.anc_menu, checkable=True)
        self.anc_off_action.triggered.connect(lambda: self.set_anc_mode(0))
        self.anc_menu.addAction(self.anc_off_action)
        
        self.anc_on_action = QAction("ANC On", self.anc_menu, checkable=True)
        self.anc_on_action.triggered.connect(lambda: self.set_anc_mode(1))
        self.anc_menu.addAction(self.anc_on_action)
        
        self.anc_passthru_action = QAction("Full Passthrough", self.anc_menu, checkable=True)
        self.anc_passthru_action.triggered.connect(lambda: self.set_anc_mode(2))
        self.anc_menu.addAction(self.anc_passthru_action)
        
        self.anc_ambient_action = QAction("Ambient Aware / TalkThru", self.anc_menu, checkable=True)
        self.anc_ambient_action.triggered.connect(lambda: self.set_anc_mode(3))
        self.anc_menu.addAction(self.anc_ambient_action)
        
        # Group actions to make them mutually exclusive
        self.anc_group = QActionGroup(self)
        self.anc_group.addAction(self.anc_off_action)
        self.anc_group.addAction(self.anc_on_action)
        self.anc_group.addAction(self.anc_passthru_action)
        self.anc_group.addAction(self.anc_ambient_action)
        
        # Interactive Mic Mute toggle action
        self.mic_action = QAction("Mic: --", self.menu)
        self.mic_action.triggered.connect(self.toggle_mic_mute)
        self.menu.addAction(self.mic_action)
        
        self.menu.addSeparator()
        
        self.left_action = QAction("Left: --", self.menu)
        self.left_action.setEnabled(False)
        self.menu.addAction(self.left_action)
        
        self.right_action = QAction("Right: --", self.menu)
        self.right_action.setEnabled(False)
        self.menu.addAction(self.right_action)
        
        self.case_action = QAction("Case: --", self.menu)
        self.case_action.setEnabled(False)
        self.menu.addAction(self.case_action)
        
        self.menu.addSeparator()
        
        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)
        
    def get_icon(self, connected, mic_muted=False, earbuds_active=True):
        """Generates dynamic tray icons using QPainter for fallback compatibility."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Determine color theme based on connection state
        if not connected or not earbuds_active:
            color = QColor("#757575") # Neutral grey
        elif mic_muted:
            color = QColor("#d50000") # Warning red
        else:
            color = QColor("#ff6d00") # Signature JBL orange
            
        painter.setPen(color)
        painter.setBrush(QColor("transparent"))
        
        if connected and earbuds_active and mic_muted:
            # Draw crossed microphone icon
            painter.setBrush(color)
            painter.drawRoundedRect(12, 6, 8, 12, 4, 4)
            painter.setBrush(QColor("transparent"))
            painter.drawArc(8, 10, 16, 12, 180 * 16, 180 * 16)
            painter.drawLine(16, 22, 16, 25)
            painter.drawLine(10, 25, 22, 25)
            
            # Diagonal line representing mute state
            painter.setPen(QColor("#d50000"))
            pen = painter.pen()
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(6, 6, 26, 26)
        else:
            # Draw standard headphones icon
            painter.drawArc(4, 4, 24, 24, 0, 180 * 16)
            painter.drawArc(6, 6, 20, 20, 0, 180 * 16)
            painter.setBrush(color)
            painter.drawRoundedRect(2, 14, 6, 12, 2, 2)
            painter.drawRoundedRect(24, 14, 6, 12, 2, 2)
            
        painter.end()
        return QIcon(pixmap)
        
    def open_device(self):
        """Attempts to open the HID device using either the pure Python or C-binding API."""
        # Try opening via hid.Device (pure Python backend)
        try:
            dev = hid.Device(vid=VENDOR_ID, pid=PRODUCT_ID)
            dev.nonblocking = True
            return dev
        except (AttributeError, Exception):
            pass
            
        # Try opening via hid.device (C-binding backend)
        try:
            dev = hid.device()
            for d in hid.enumerate():
                if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID:
                    dev.open_path(d['path'])
                    dev.set_nonblocking(1)
                    return dev
        except Exception:
            pass
            
        return None

    def poll_device(self):
        """Polls the device for updates or reads outstanding queued packets."""
        if not self.device:
            self.device = self.open_device()
            if self.device:
                # Retrieve initial states via Feature Reports
                try:
                    # Connection Mode (0x68)
                    res_conn = self.device.get_feature_report(0x68, 64)
                    if res_conn and len(res_conn) >= 7:
                        self.conn_mode = "2.4GHz Dongle" if res_conn[1] == 0x01 else "Bluetooth"
                        self.left_bat = res_conn[2]
                        self.right_bat = res_conn[4]
                        self.case_bat = res_conn[6]
                        
                    # ANC Mode (0x46)
                    res_anc = self.device.get_feature_report(0x46, 64)
                    if res_anc and len(res_anc) >= 2:
                        val = res_anc[1]
                        if val == 0x00:
                            self.anc_mode = "Off"
                        elif val == 0x01:
                            self.anc_mode = "ANC On"
                        elif val == 0x02:
                            self.anc_mode = "Full Passthrough"
                        elif val == 0x03:
                            self.anc_mode = "Ambient Aware / TalkThru"
                            
                    # Mic Mute state (0x06)
                    res_mic = self.device.get_feature_report(0x06, 64)
                    if res_mic and len(res_mic) >= 2:
                        self.mic_muted = (res_mic[1] == 0x00)
                except Exception:
                    pass
                self.update_ui(connected=True)
            else:
                self.handle_disconnect()
                return
                
        # Non-blocking read loop to drain pending updates
        try:
            has_updates = False
            while True:
                try:
                    data = self.device.read(64, timeout=2)
                except TypeError:
                    data = self.device.read(64)
                    
                if not data:
                    break
                    
                if self.handle_packet(data):
                    has_updates = True
                    
            if has_updates:
                self.update_ui(connected=True)
        except Exception:
            self.handle_disconnect()
            
    def handle_packet(self, data):
        """Parses individual HID packets according to their report IDs."""
        if not data or len(data) < 2:
            return False
            
        report_id = data[0]
        
        if report_id == 0x0b and len(data) >= 7:
            self.left_bat = data[2]
            self.right_bat = data[4]
            self.case_bat = data[6]
            return True
            
        elif report_id == 0x06:
            # Mic mute state: 0x00 = Muted, 0x01 = Unmuted
            self.mic_muted = (data[1] == 0x00)
            return True
            
        elif report_id == 0x02:
            # ANC profile mapping
            val = data[1]
            if val == 0x00:
                self.anc_mode = "Off"
            elif val == 0x01:
                self.anc_mode = "ANC On"
            elif val == 0x02:
                self.anc_mode = "Full Passthrough"
            elif val == 0x03:
                self.anc_mode = "Ambient Aware / TalkThru"
            else:
                self.anc_mode = f"Unknown ({val})"
            return True
            
        elif report_id == 0x09:
            # Connection mode source: 0x00 = Bluetooth, 0x01 = 2.4GHz Wireless
            val = data[1]
            if val == 0x01:
                self.conn_mode = "2.4GHz Dongle"
            elif val == 0x00:
                self.conn_mode = "Bluetooth"
            else:
                self.conn_mode = f"Unknown ({val})"
            return True
        return False
            
    def update_ui(self, connected):
        """Updates the menu actions, tooltip description, and status icons."""
        if not connected:
            self.handle_disconnect()
            return
            
        # Format battery level indicators
        l_str = f"{self.left_bat}%" if 1 <= self.left_bat <= 100 else "Off/Charging"
        r_str = f"{self.right_bat}%" if 1 <= self.right_bat <= 100 else "Off/Charging"
        c_str = f"{self.case_bat}%" if 0 <= self.case_bat <= 100 else "Unknown"
        
        is_left_on = (1 <= self.left_bat <= 100)
        is_right_on = (1 <= self.right_bat <= 100)
        is_any_on = (is_left_on or is_right_on) and (self.conn_mode != "Bluetooth")
        
        # Connection mode check
        self.source_menu.setEnabled(True)
        self.source_menu.setTitle(f"Source: {self.conn_mode}")
        if self.conn_mode == "Bluetooth":
            self.source_bt_action.setChecked(True)
        else:
            self.source_dongle_action.setChecked(True)
            
        if not is_any_on:
            # Handle state when both earbuds are off (charging inside case)
            if self.conn_mode == "Bluetooth":
                active_source = "Bluetooth"
                status_title = "JBL Quantum TWS (Bluetooth Mode)"
                l_str = "Bluetooth"
                r_str = "Bluetooth"
            else:
                active_source = "Off / Charging"
                status_title = "JBL Quantum TWS (Off/Charging)"
                
            self.title_action.setText(status_title)
            self.anc_menu.setTitle("ANC Mode: --")
            self.anc_menu.setEnabled(False)
            self.mic_action.setText("Mic: --")
            self.mic_action.setEnabled(False)
            self.left_action.setText(f"Left: {l_str}")
            self.right_action.setText(f"Right: {r_str}")
            self.case_action.setText(f"Case: {c_str}")
            
            tooltip = f"JBL Quantum TWS\n[Status: {active_source}]\nCase: {c_str}"
            self.tray.setToolTip(tooltip)
            self.tray.setIcon(self.get_icon(True, mic_muted=False, earbuds_active=False))
        else:
            # Active headset session
            active_source = self.conn_mode
            mic_str = "Muted (Click to Unmute)" if self.mic_muted else "Unmuted (Click to Mute)"
            
            self.title_action.setText("JBL Quantum TWS (Connected)")
            
            # Enable interactive elements
            self.anc_menu.setEnabled(True)
            self.anc_menu.setTitle(f"ANC Mode: {self.anc_mode}")
            
            # Check the correct action in menu
            if self.anc_mode == "Off":
                self.anc_off_action.setChecked(True)
            elif self.anc_mode == "ANC On":
                self.anc_on_action.setChecked(True)
            elif self.anc_mode == "Full Passthrough":
                self.anc_passthru_action.setChecked(True)
            elif self.anc_mode == "Ambient Aware / TalkThru":
                self.anc_ambient_action.setChecked(True)
                
            self.mic_action.setEnabled(True)
            self.mic_action.setText(f"Mic: {mic_str}")
            
            self.left_action.setText(f"Left: {l_str}")
            self.right_action.setText(f"Right: {r_str}")
            self.case_action.setText(f"Case: {c_str}")
            
            tooltip = (f"JBL Quantum TWS\n"
                       f"[{active_source} | Mic: {'MUTED' if self.mic_muted else 'Unmuted'} | {self.anc_mode}]\n"
                       f"Left: {l_str} | Right: {r_str} | Case: {c_str}")
            self.tray.setToolTip(tooltip)
            self.tray.setIcon(self.get_icon(True, self.mic_muted, earbuds_active=True))
        
    def handle_disconnect(self):
        """Resets states and icons when device link is severed."""
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
            
        self.title_action.setText("JBL Quantum TWS (Disconnected)")
        self.source_menu.setTitle("Source: --")
        self.source_menu.setEnabled(False)
        self.anc_menu.setTitle("ANC Mode: --")
        self.anc_menu.setEnabled(False)
        self.mic_action.setText("Mic: --")
        self.mic_action.setEnabled(False)
        self.left_action.setText("Left: --")
        self.right_action.setText("Right: --")
        self.case_action.setText("Case: --")
        self.tray.setToolTip("JBL Quantum TWS (Disconnected)")
        self.tray.setIcon(self.get_icon(False))

    def send_feature(self, report_id, value):
        """Sends a Feature Report to the device, handling backend differences."""
        if not self.device:
            return False
        try:
            # Try bytes payload first (pure Python hid.Device)
            try:
                payload = bytes([report_id, value])
                self.device.send_feature_report(payload)
                return True
            except (TypeError, AttributeError):
                pass
                
            # Fallback to list (C-binding hid.device)
            payload = [report_id, value]
            self.device.send_feature_report(payload)
            return True
        except Exception as e:
            print(f"Error sending feature report: {e}")
            return False

    def send_output(self, report_id, payload):
        """Sends an Output Report to the device, handling backend differences.
        payload should be a list of bytes excluding the report_id."""
        if not self.device:
            return False
        try:
            full_payload = [report_id] + payload
            # Try bytes payload first (pure Python hid.Device)
            try:
                self.device.write(bytes(full_payload))
                return True
            except (TypeError, AttributeError):
                pass
                
            # Fallback to list (C-binding hid.device)
            self.device.write(full_payload)
            return True
        except Exception as e:
            print(f"Error sending output report: {e}")
            return False

    def set_anc_mode(self, mode):
        """Sends Feature Report 0x46 to update the ANC mode."""
        self.send_feature(0x46, mode)

    def set_audio_source(self, source_type):
        """Sends Feature Report 0x68 to switch between Dongle (1) and Bluetooth (0)."""
        self.send_feature(0x68, source_type)

    def toggle_mic_mute(self):
        """Toggles the microphone mute state using Output Report 0x2f."""
        new_muted_state = not self.mic_muted
        val = 0x02 if new_muted_state else 0x04
        self.send_output(0x2f, [val])
        
    def quit(self):
        """Cleans up devices and terminates the main execution thread."""
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
        self.app.quit()
        
    def run(self):
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    monitor = JBLBatteryMonitor()
    monitor.run()
