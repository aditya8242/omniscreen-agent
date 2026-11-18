import tkinter as tk
from tkinter import font as tkfont
import requests
import threading
import time
from typing import Optional, Any, Dict, List
from io import BytesIO
import qrcode
from PIL import Image, ImageTk

# Apple Cupertino Dark Mode Palette
BG_CANVAS = "#0B0B0D"
CARD_SURFACE = "#151518"
CARD_SECONDARY = "#1E1E22"
BORDER_HAIRLINE = "#27272C"
BORDER_HIGHLIGHT = "#383840"

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#98989E"
TEXT_MUTED = "#686870"

APPLE_BLUE = "#0A84FF"
APPLE_BLUE_HOVER = "#0071E3"
APPLE_GREEN = "#30D158"
APPLE_ORANGE = "#FF9F0A"
APPLE_PURPLE = "#BF5AF2"
APPLE_RED = "#FF453A"

class OmniScreenWidget:
    def __init__(
        self,
        hub_url: str = "http://127.0.0.1:8765",
        win32_agent: Optional[Any] = None,
        tv_sensor: Optional[Any] = None,
        lan_ip: str = "127.0.0.1"
    ):
        self.hub_url = hub_url.rstrip("/")
        self.win32_agent = win32_agent
        self.tv_sensor = tv_sensor
        self.lan_ip = lan_ip

        self.root = tk.Tk()
        self.root.title("OmniScreen Reality")
        self.root.geometry("420x680")
        self.root.minsize(400, 640)
        self.root.configure(bg=BG_CANVAS)

        # Pin floating window on top
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        self._is_fetching = False
        self._qr_image_tk = None
        self._show_pairing = False

        self._init_typography()
        self._build_interface()

        # Initial asynchronous calculation
        self.root.after(400, self.calculate_reality)

        # Periodic silent background refresh every 20 seconds
        self._schedule_periodic_refresh()

    def _init_typography(self):
        # Apple SF Pro fallback hierarchy
        self.font_nav_title = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.font_hero_time = tkfont.Font(family="Segoe UI", size=36, weight="bold")
        self.font_hero_unit = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.font_caption = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.font_body = tkfont.Font(family="Segoe UI", size=10)
        self.font_body_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_sub = tkfont.Font(family="Segoe UI", size=9)
        self.font_metric_num = tkfont.Font(family="Segoe UI", size=14, weight="bold")

    def _build_interface(self):
        # 1. Navigation / Header Bar
        nav_frame = tk.Frame(self.root, bg=BG_CANVAS)
        nav_frame.pack(fill="x", padx=20, pady=(16, 12))

        app_title = tk.Label(
            nav_frame,
            text="OmniScreen Reality",
            font=self.font_nav_title,
            fg=TEXT_PRIMARY,
            bg=BG_CANVAS
        )
        app_title.pack(side="left")

        self.status_pill = tk.Label(
            nav_frame,
            text="● Live Sync",
            font=self.font_caption,
            fg=APPLE_GREEN,
            bg=CARD_SURFACE,
            padx=10,
            pady=4,
            relief="flat"
        )
        self.status_pill.pack(side="right")

        # 2. Hero Screen Time Card (Apple Screen Time Design)
        hero_card = tk.Frame(
            self.root,
            bg=CARD_SURFACE,
            highlightbackground=BORDER_HAIRLINE,
            highlightthickness=1,
            padx=18,
            pady=16
        )
        hero_card.pack(fill="x", padx=16, pady=(0, 10))

        lbl_hero_tag = tk.Label(
            hero_card,
            text="TRUE COMBINED EXPOSURE",
            font=self.font_caption,
            fg=TEXT_MUTED,
            bg=CARD_SURFACE
        )
        lbl_hero_tag.pack(anchor="w")

        self.lbl_hero_display = tk.Label(
            hero_card,
            text="0m",
            font=self.font_hero_time,
            fg=TEXT_PRIMARY,
            bg=CARD_SURFACE
        )
        self.lbl_hero_display.pack(anchor="w", pady=(2, 2))

        self.lbl_hero_detail = tk.Label(
            hero_card,
            text="De-duplicated interval union across all screens today",
            font=self.font_sub,
            fg=TEXT_SECONDARY,
            bg=CARD_SURFACE
        )
        self.lbl_hero_detail.pack(anchor="w")

        # 3. Comparative Metric Strip (Raw vs Union vs Overlap)
        metric_strip = tk.Frame(self.root, bg=BG_CANVAS)
        metric_strip.pack(fill="x", padx=16, pady=(0, 10))

        # Col 1: Raw Total
        c1 = tk.Frame(metric_strip, bg=CARD_SURFACE, highlightbackground=BORDER_HAIRLINE, highlightthickness=1, padx=10, pady=8)
        c1.pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Label(c1, text="RAW TOTAL", font=self.font_caption, fg=TEXT_MUTED, bg=CARD_SURFACE).pack(anchor="w")
        self.lbl_metric_raw = tk.Label(c1, text="0m", font=self.font_metric_num, fg=TEXT_PRIMARY, bg=CARD_SURFACE)
        self.lbl_metric_raw.pack(anchor="w")

        # Col 2: Second-Screening Overlap
        c2 = tk.Frame(metric_strip, bg=CARD_SURFACE, highlightbackground=BORDER_HAIRLINE, highlightthickness=1, padx=10, pady=8)
        c2.pack(side="left", fill="both", expand=True, padx=(4, 0))
        tk.Label(c2, text="2ND SCREENING", font=self.font_caption, fg=APPLE_ORANGE, bg=CARD_SURFACE).pack(anchor="w")
        self.lbl_metric_overlap = tk.Label(c2, text="0m", font=self.font_metric_num, fg=APPLE_ORANGE, bg=CARD_SURFACE)
        self.lbl_metric_overlap.pack(anchor="w")

        # 4. Inset Grouped Device Breakdown Card
        self.dev_card = tk.Frame(
            self.root,
            bg=CARD_SURFACE,
            highlightbackground=BORDER_HAIRLINE,
            highlightthickness=1,
            padx=16,
            pady=12
        )
        self.dev_card.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        top_row = tk.Frame(self.dev_card, bg=CARD_SURFACE)
        top_row.pack(fill="x", pady=(0, 8))

        lbl_dev_hdr = tk.Label(
            top_row,
            text="CONNECTED DEVICES & USAGE",
            font=self.font_caption,
            fg=TEXT_MUTED,
            bg=CARD_SURFACE
        )
        lbl_dev_hdr.pack(side="left")

        self.btn_toggle_pairing = tk.Button(
            top_row,
            text="Pair Mobile",
            font=self.font_caption,
            fg=APPLE_BLUE,
            bg=CARD_SURFACE,
            activeforeground=APPLE_BLUE_HOVER,
            activebackground=CARD_SURFACE,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._toggle_pairing_view
        )
        self.btn_toggle_pairing.pack(side="right")

        self.device_list_container = tk.Frame(self.dev_card, bg=CARD_SURFACE)
        self.device_list_container.pack(fill="both", expand=True)

        # 5. AirDrop-Style Mobile Pairing / QR Card (Hidden by default, toggleable)
        self.pairing_card = tk.Frame(
            self.dev_card,
            bg=CARD_SECONDARY,
            highlightbackground=BORDER_HAIRLINE,
            highlightthickness=1,
            padx=12,
            pady=12
        )
        # Pack only when toggled

        # 6. Bottom Action Bar
        action_frame = tk.Frame(self.root, bg=BG_CANVAS)
        action_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.btn_calculate = tk.Button(
            action_frame,
            text="Calculate Reality",
            font=self.font_body_bold,
            bg=APPLE_BLUE,
            fg="#FFFFFF",
            activebackground=APPLE_BLUE_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=10,
            command=self.calculate_reality
        )
        self.btn_calculate.pack(fill="x")

        # LAN address & Auto-Detect beacon footer note
        self.lbl_footer = tk.Label(
            self.root,
            text=f"LAN IP: {self.lan_ip}:8765  |  Auto-Discovery Beacon: Active",
            font=self.font_caption,
            fg=TEXT_MUTED,
            bg=BG_CANVAS
        )
        self.lbl_footer.pack(pady=(0, 12))

    def _toggle_pairing_view(self):
        self._show_pairing = not self._show_pairing
        if self._show_pairing:
            self.btn_toggle_pairing.config(text="Hide Pairing", fg=APPLE_ORANGE)
            self._render_pairing_card()
            self.device_list_container.pack_forget()
            self.pairing_card.pack(fill="both", expand=True)
        else:
            self.btn_toggle_pairing.config(text="Pair Mobile", fg=APPLE_BLUE)
            self.pairing_card.pack_forget()
            self.device_list_container.pack(fill="both", expand=True)

    def _render_pairing_card(self):
        for w in self.pairing_card.winfo_children():
            w.destroy()

        lbl_title = tk.Label(
            self.pairing_card,
            text="Instant Mobile Pairing",
            font=self.font_body_bold,
            fg=TEXT_PRIMARY,
            bg=CARD_SECONDARY
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            self.pairing_card,
            text="Method 1: In the Android app, tap 'Auto-Detect PC'\nMethod 2: Scan QR code below or enter LAN IP manually",
            font=self.font_sub,
            fg=TEXT_SECONDARY,
            bg=CARD_SECONDARY,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(2, 8))

        # Generate QR Code in memory
        try:
            qr = qrcode.QRCode(box_size=3, border=1)
            qr.add_data(f"http://{self.lan_ip}:8765")
            qr.make(fit=True)
            img = qr.make_image(fill_color="#FFFFFF", back_color="#1E1E22")
            self._qr_image_tk = ImageTk.PhotoImage(img)
            lbl_qr = tk.Label(self.pairing_card, image=self._qr_image_tk, bg=CARD_SECONDARY)
            lbl_qr.pack(pady=4)
        except Exception:
            pass

        lbl_addr = tk.Label(
            self.pairing_card,
            text=f"Address: {self.lan_ip}:8765",
            font=self.font_body_bold,
            fg=APPLE_GREEN,
            bg=CARD_SECONDARY
        )
        lbl_addr.pack(pady=(4, 0))

    def calculate_reality(self):
        """
        Asynchronous, non-blocking calculation.
        Pushes and fetches on background worker thread. GUI never freezes.
        """
        if self._is_fetching:
            return
        self._is_fetching = True
        self.btn_calculate.config(text="Updating Reality...", bg=BORDER_HIGHLIGHT, state="disabled")
        self.status_pill.config(text="● Syncing", fg=APPLE_ORANGE)

        threading.Thread(target=self._async_fetch_reality, daemon=True).start()

    def _async_fetch_reality(self):
        # 1. Flush local agents non-blockingly
        if self.win32_agent:
            try:
                self.win32_agent.flush_now()
            except Exception:
                pass

        if self.tv_sensor:
            try:
                self.tv_sensor.flush_now()
            except Exception:
                pass

        # 2. Query Reality Hub
        data = None
        error_msg = None
        try:
            res = requests.get(f"{self.hub_url}/api/reality", timeout=2.5)
            if res.status_code == 200:
                data = res.json()
            else:
                error_msg = f"HTTP {res.status_code}"
        except Exception as e:
            error_msg = "Offline"

        # 3. Post back to Tkinter event loop
        self.root.after(0, self._apply_reality_update, data, error_msg)

    def _apply_reality_update(self, data: Optional[Dict[str, Any]], error_msg: Optional[str]):
        self._is_fetching = False
        self.btn_calculate.config(text="Calculate Reality", bg=APPLE_BLUE, state="normal")

        if not data:
            self.status_pill.config(text=f"● {error_msg or 'Offline'}", fg=APPLE_RED)
            return

        self.status_pill.config(text="● Live Sync", fg=APPLE_GREEN)

        # Update Hero Combined Exposure
        true_exp = data.get("true_exposure_formatted", "0m")
        self.lbl_hero_display.config(text=true_exp)

        raw_total = data.get("raw_total_formatted", "0m")
        overlap = data.get("second_screening_formatted", "0m")
        dev_count = data.get("device_count", 0)

        self.lbl_hero_detail.config(
            text=f"De-duplicated interval union across {dev_count} device{'s' if dev_count != 1 else ''}"
        )
        self.lbl_metric_raw.config(text=raw_total)
        self.lbl_metric_overlap.config(text=overlap)

        # Update Device List
        for w in self.device_list_container.winfo_children():
            w.destroy()

        devices = data.get("devices", [])
        if not devices:
            empty_lbl = tk.Label(
                self.device_list_container,
                text="No device sessions recorded today yet.\nPC and paired mobile devices sync automatically.",
                font=self.font_sub,
                fg=TEXT_MUTED,
                bg=CARD_SURFACE,
                justify="left"
            )
            empty_lbl.pack(anchor="w", pady=12)
            return

        for dev in devices:
            dev_name = dev.get("device_name", "Device")
            dev_type = dev.get("device_type", "pc").upper()
            dev_time = dev.get("formatted", "0m")
            top_apps = dev.get("top_apps", [])

            # Badge color
            color_map = {
                "PC": APPLE_BLUE,
                "ANDROID": APPLE_PURPLE,
                "IOS": APPLE_PURPLE,
                "TV": APPLE_ORANGE
            }
            dot_color = color_map.get(dev_type, APPLE_BLUE)

            # Inset Device Row
            dev_row = tk.Frame(
                self.device_list_container,
                bg=CARD_SECONDARY,
                highlightbackground=BORDER_HAIRLINE,
                highlightthickness=1,
                padx=12,
                pady=8
            )
            dev_row.pack(fill="x", pady=4)

            header_line = tk.Frame(dev_row, bg=CARD_SECONDARY)
            header_line.pack(fill="x")

            lbl_name = tk.Label(
                header_line,
                text=f"[{dev_type}] {dev_name}",
                font=self.font_body_bold,
                fg=dot_color,
                bg=CARD_SECONDARY
            )
            lbl_name.pack(side="left")

            lbl_duration = tk.Label(
                header_line,
                text=dev_time,
                font=self.font_body_bold,
                fg=TEXT_PRIMARY,
                bg=CARD_SECONDARY
            )
            lbl_duration.pack(side="right")

            if top_apps:
                apps_text = "  ·  ".join(f"{a['app_name']} ({a['formatted']})" for a in top_apps[:3])
                lbl_apps = tk.Label(
                    dev_row,
                    text=apps_text,
                    font=self.font_caption,
                    fg=TEXT_SECONDARY,
                    bg=CARD_SECONDARY,
                    anchor="w"
                )
                lbl_apps.pack(fill="x", pady=(4, 0))

    def _schedule_periodic_refresh(self):
        # Auto-refresh quietly every 20 seconds
        self.root.after(20000, self._periodic_tick)

    def _periodic_tick(self):
        if not self._is_fetching:
            self.calculate_reality()
        self._schedule_periodic_refresh()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    widget = OmniScreenWidget()
    widget.run()
