from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import csv
import os
import hashlib
import json
import threading
from datetime import datetime

# ─── CEK LIBRARY KAMERA (OpenCV + pyzbar) ────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

CAMERA_SCAN_AVAILABLE = CV2_AVAILABLE and PYZBAR_AVAILABLE

# ─── KONFIGURASI TEMA MODERN ──────────────────────────────────────────────────
Window.clearcolor = (0.07, 0.08, 0.1, 1)

# ─── KONFIGURASI AKUN (disimpan di file lokal) ────────────────────────────────
ACCOUNTS_FILE = "accounts.json"
DEFAULT_ADMIN_PASS = hashlib.sha256("admin123".encode()).hexdigest()
DEFAULT_USER_PASS  = hashlib.sha256("kasir123".encode()).hexdigest()

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {
        "admin": {"password": DEFAULT_ADMIN_PASS, "role": "admin"},
        "kasir": {"password": DEFAULT_USER_PASS,  "role": "user"},
    }

def save_accounts(data):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

ACCOUNTS = load_accounts()

# ─── WIDGET DASAR ─────────────────────────────────────────────────────────────
class ModernButton(Button):
    def __init__(self, bg_color=(0.12, 0.45, 1, 1), radius=[12], **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color  = (0, 0, 0, 0)
        self.bg_color = bg_color
        self.radius   = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

class ModernInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal  = ''
        self.background_active  = ''
        self.background_color   = (0.15, 0.17, 0.2, 1)
        self.foreground_color   = (1, 1, 1, 1)
        self.cursor_color       = (0.2, 0.5, 1, 1)
        self.padding            = [15, 12]
        self.font_size          = '15sp'


# ══════════════════════════════════════════════════════════════════════════════
# LAYAR LOGIN
# ══════════════════════════════════════════════════════════════════════════════
class LoginScreen(Screen):
    def __init__(self, on_success, **kwargs):
        super().__init__(**kwargs)
        self.on_success = on_success
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=60, spacing=20)
        root.add_widget(Widget())  # spacer atas

        root.add_widget(Label(
            text="[b]KASIRKU[/b]", markup=True,
            font_size='36sp', color=(0.2, 0.6, 1, 1),
            size_hint_y=None, height=60
        ))
        root.add_widget(Label(
            text="Silakan login untuk melanjutkan",
            font_size='14sp', color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None, height=30
        ))

        card = BoxLayout(orientation='vertical', spacing=15, padding=[0, 20])
        self.inp_user = ModernInput(hint_text="Username", size_hint_y=None, height=50, multiline=False)
        self.inp_pass = ModernInput(hint_text="Password", password=True, size_hint_y=None, height=50, multiline=False)
        self.lbl_err  = Label(text="", color=(1, 0.3, 0.3, 1), size_hint_y=None, height=30)

        btn_login = ModernButton(
            text="MASUK", bg_color=(0.1, 0.55, 0.3, 1),
            size_hint_y=None, height=55, font_size='18sp', bold=True
        )
        btn_login.bind(on_release=self.do_login)

        card.add_widget(self.inp_user)
        card.add_widget(self.inp_pass)
        card.add_widget(self.lbl_err)
        card.add_widget(btn_login)
        root.add_widget(card)

        root.add_widget(Label(
            text="Created by @ Junaid adzan isnam",
            font_size='11sp', color=(0.3, 0.3, 0.3, 1),
            size_hint_y=None, height=25
        ))
        root.add_widget(Widget())  # spacer bawah
        self.add_widget(root)

    def do_login(self, *args):
        username = self.inp_user.text.strip()
        password = self.inp_pass.text
        hashed   = hashlib.sha256(password.encode()).hexdigest()

        if username in ACCOUNTS and ACCOUNTS[username]["password"] == hashed:
            role = ACCOUNTS[username]["role"]
            self.lbl_err.text = ""
            self.on_success(username, role)
        else:
            self.lbl_err.text = "Username atau Password salah!"
            self.inp_pass.text = ""


# ══════════════════════════════════════════════════════════════════════════════
# LAYAR UTAMA KASIR
# ══════════════════════════════════════════════════════════════════════════════
class MainScreen(Screen):
    def __init__(self, username, role, on_logout, **kwargs):
        super().__init__(**kwargs)
        self.username  = username
        self.role      = role          # "admin" atau "user"
        self.on_logout = on_logout
        self._build()

    def _build(self):
        # Diteruskan ke KasirApp logic melalui widget internal
        self.app_widget = KasirMainWidget(
            username=self.username,
            role=self.role,
            on_logout=self.on_logout
        )
        self.add_widget(self.app_widget)


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET UTAMA APLIKASI KASIR
# ══════════════════════════════════════════════════════════════════════════════
class KasirMainWidget(BoxLayout):
    def __init__(self, username, role, on_logout, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.username  = username
        self.role      = role
        self.on_logout = on_logout

        self.inventory   = [
            {"nama": "Tisu Wajah", "harga": 10000, "stok": 10, "barcode": ""},
            {"nama": "Popok",      "harga": 30000, "stok": 10, "barcode": ""},
        ]
        self.cart        = []
        self.total_harga = 0
        self.selected_path      = None
        self.selected_path_qris = None
        self.foto_qris   = "Qris Toko muna.jpg"

        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                self.file_laporan = os.path.join(
                    primary_external_storage_path(), "laporan_penjualan.csv"
                )
            except:
                self.file_laporan = "laporan_penjualan.csv"
        else:
            self.file_laporan = "laporan_penjualan.csv"

        Window.bind(on_resize=self.on_window_resize)
        self._build_tabs()

    # ── Header strip ──────────────────────────────────────────────────────────
    def _build_header(self):
        header = BoxLayout(size_hint_y=None, height=40, padding=[10, 0])
        with header.canvas.before:
            Color(0.1, 0.12, 0.16, 1)
            RoundedRectangle(pos=header.pos, size=header.size)
        header.add_widget(Label(
            text=f"User: {self.username}  |  Role: {self.role.upper()}",
            font_size='13sp', color=(0.6, 0.8, 1, 1), halign='left'
        ))
        btn_logout = Button(
            text="Logout", size_hint=(None, 1), width=90,
            background_color=(0.7, 0.1, 0.1, 1), font_size='13sp'
        )
        btn_logout.bind(on_release=lambda *a: self.on_logout())
        header.add_widget(btn_logout)
        return header

    def _build_tabs(self):
        self.clear_widgets()
        self.add_widget(self._build_header())

        self.root_tabs = TabbedPanel(do_default_tab=False, background_color=(0, 0, 0, 0))

        # TAB KASIR
        self.tab_kasir = TabbedPanelItem(
            text="KASIR",
            background_normal='', background_down='',
            background_color=(0.1, 0.5, 0.9, 1)
        )
        self.main_kasir_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.build_kasir_ui()
        self.tab_kasir.add_widget(self.main_kasir_layout)

        # TAB STOK
        self.tab_list = TabbedPanelItem(
            text="STOK",
            background_normal='', background_color=(0.15, 0.17, 0.2, 1)
        )
        self.list_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.build_inventory_ui()
        self.tab_list.add_widget(self.list_layout)

        # TAB PENGATURAN (admin only)
        self.tab_import = TabbedPanelItem(
            text="PENGATURAN",
            background_normal='', background_color=(0.15, 0.17, 0.2, 1)
        )
        self.import_layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        self.build_import_ui()
        self.tab_import.add_widget(self.import_layout)

        # TAB OMZET
        self.tab_laporan = TabbedPanelItem(
            text="OMZET",
            background_normal='', background_color=(0.15, 0.17, 0.2, 1)
        )
        self.laporan_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.build_laporan_ui()
        self.tab_laporan.add_widget(self.laporan_layout)

        self.root_tabs.add_widget(self.tab_kasir)
        self.root_tabs.add_widget(self.tab_list)
        if self.role == "admin":
            self.root_tabs.add_widget(self.tab_import)
        self.root_tabs.add_widget(self.tab_laporan)
        self.add_widget(self.root_tabs)

    def on_window_resize(self, window, width, height):
        if hasattr(self, 'main_kasir_layout'):
            self.build_kasir_ui()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB KASIR
    # ══════════════════════════════════════════════════════════════════════════
    def build_kasir_ui(self):
        self.main_kasir_layout.clear_widgets()
        is_p = Window.width < Window.height

        # Baris pencarian + tombol scan barcode
        search_box = BoxLayout(size_hint_y=None, height=75, spacing=10)
        self.search_input_kasir = ModernInput(hint_text="Cari produk atau scan barcode…")
        self.search_input_kasir.bind(text=lambda inst, val: self.refresh_product_buttons())
        btn_scan_kasir = ModernButton(
            text="SCAN\nBARCODE",
            bg_color=(0.6, 0.3, 0.0, 1),
            size_hint_x=None, width=120
        )
        btn_scan_kasir.bind(on_release=self.open_barcode_scanner_kasir)
        search_box.add_widget(self.search_input_kasir)
        search_box.add_widget(btn_scan_kasir)
        self.main_kasir_layout.add_widget(search_box)

        body = BoxLayout(orientation='vertical' if is_p else 'horizontal', spacing=20)

        self.product_grid = GridLayout(cols=2 if is_p else 3, spacing=15, size_hint_y=None)
        self.product_grid.bind(minimum_height=self.product_grid.setter('height'))
        self.refresh_product_buttons()

        scroll_prod = ScrollView(size_hint=(1, 0.5) if is_p else (0.65, 1), bar_width=5)
        scroll_prod.add_widget(self.product_grid)
        body.add_widget(scroll_prod)

        cart_panel = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.5) if is_p else (0.35, 1),
            spacing=10, padding=15
        )
        with cart_panel.canvas.before:
            Color(0.12, 0.14, 0.18, 1)
            RoundedRectangle(pos=cart_panel.pos, size=cart_panel.size, radius=[15])

        self.cart_list_layout = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.cart_list_layout.bind(minimum_height=self.cart_list_layout.setter('height'))
        scroll_cart = ScrollView(bar_width=4, size_hint_y=1)
        scroll_cart.add_widget(self.cart_list_layout)

        self.count_label = Label(
            text="Pcs: 0", font_size='15sp',
            color=(0.2, 0.8, 0.2, 1), size_hint_y=None, height=50
        )
        self.total_label = Label(
            text=f"TOTAL: Rp {self.total_harga:,}", font_size='22sp',
            bold=True, color=(0.2, 0.6, 1, 1), size_hint_y=None, height=40
        )
        btn_pay = ModernButton(
            text="PROSES BAYAR", bg_color=(0.1, 0.6, 0.3, 1),
            size_hint_y=None, height=60
        )
        btn_pay.bind(on_release=self.show_payment_options)

        cart_panel.add_widget(Label(
            text="DETAIL PESANAN", color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None, height=30
        ))
        cart_panel.add_widget(scroll_cart)
        cart_panel.add_widget(self.count_label)
        cart_panel.add_widget(self.total_label)
        cart_panel.add_widget(btn_pay)
        body.add_widget(cart_panel)
        self.main_kasir_layout.add_widget(body)
        self.main_kasir_layout.add_widget(Label(
            text="Created by @ Junaid adzan isnam",
            size_hint_y=None, height=20, font_size='11sp', color=(0.4, 0.4, 0.4, 1)
        ))

    # ── Barcode scanner (Kasir) ───────────────────────────────────────────────
    def open_barcode_scanner_kasir(self, *args):
        """Buka dialog scan barcode untuk mencari / menambah produk ke keranjang."""
        self._open_barcode_popup(mode="kasir")

    def open_barcode_scanner_stok(self, *args):
        """Buka dialog scan barcode untuk mengisi field barcode produk baru."""
        self._open_barcode_popup(mode="stok", target_input=self.inp_barcode_stok)

    def _open_barcode_popup(self, mode="kasir", target_input=None):
        """
        Popup scan barcode dengan kamera nyata (OpenCV + pyzbar).
        Fallback ke input manual jika library tidak tersedia.
        """
        if CAMERA_SCAN_AVAILABLE:
            self._open_camera_scanner(mode=mode, target_input=target_input)
        else:
            self._open_manual_barcode_popup(mode=mode, target_input=target_input)

    # ── Kamera Scanner (OpenCV + pyzbar) ─────────────────────────────────────
    def _open_camera_scanner(self, mode="kasir", target_input=None):
        """Buka kamera menggunakan OpenCV, tampilkan frame di Kivy, decode barcode dengan pyzbar."""
        content = BoxLayout(orientation='vertical', spacing=0)

        # Widget gambar kamera
        from kivy.uix.image import Image as KvImage
        self._cam_image = KvImage(allow_stretch=True, keep_ratio=True)

        lbl_status = Label(
            text="Arahkan kamera ke barcode...",
            font_size='14sp', color=(1, 1, 0.4, 1),
            size_hint_y=None, height=38
        )

        btn_row = BoxLayout(size_hint_y=None, height=55, spacing=10, padding=[10, 5])
        btn_manual = ModernButton(text="Ketik Manual", bg_color=(0.3, 0.3, 0.5, 1))
        btn_close  = ModernButton(text="Tutup",        bg_color=(0.6, 0.1, 0.1, 1))
        btn_row.add_widget(btn_manual)
        btn_row.add_widget(btn_close)

        content.add_widget(self._cam_image)
        content.add_widget(lbl_status)
        content.add_widget(btn_row)

        popup = Popup(
            title="Scan Barcode - Kamera",
            content=content,
            size_hint=(0.95, 0.88),
            background_color=(0, 0, 0, 0.92)
        )

        # State kamera
        self._cam_active   = True
        self._cam_found    = False
        self._cam_cap      = None

        def open_camera_thread():
            cap = cv2.VideoCapture(0)
            self._cam_cap = cap
            if not cap.isOpened():
                Clock.schedule_once(lambda dt: setattr(
                    lbl_status, 'text',
                    "Kamera tidak bisa dibuka!\nPastikan izin kamera sudah diberikan."
                ))
                return
            while self._cam_active and not self._cam_found:
                ret, frame = cap.read()
                if not ret:
                    break

                # Decode barcode
                barcodes = pyzbar_decode(frame)
                if barcodes:
                    code = barcodes[0].data.decode("utf-8")
                    self._cam_found = True
                    # Gambar kotak hijau di sekitar barcode
                    for bc in barcodes:
                        pts = bc.polygon
                        if len(pts) == 4:
                            import numpy as np
                            pts_arr = [(p.x, p.y) for p in pts]
                            for i in range(4):
                                cv2.line(frame, pts_arr[i], pts_arr[(i+1)%4], (0,255,0), 3)
                    Clock.schedule_once(lambda dt, c=code: on_barcode_found(c))

                # Konversi frame → Kivy texture
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_flipped = cv2.flip(frame_rgb, 0)
                h, w, _ = frame_flipped.shape
                tex = Texture.create(size=(w, h), colorfmt='rgb')
                tex.blit_buffer(frame_flipped.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
                Clock.schedule_once(lambda dt, t=tex: setattr(self._cam_image, 'texture', t))

            cap.release()

        def on_barcode_found(code):
            lbl_status.text  = f"Barcode ditemukan: {code}"
            lbl_status.color = (0.2, 1.0, 0.4, 1)
            Clock.schedule_once(lambda dt: finish(code), 0.8)

        def finish(code):
            stop_camera()
            popup.dismiss()
            handle_code(code)

        def stop_camera():
            self._cam_active = False
            if self._cam_cap and self._cam_cap.isOpened():
                self._cam_cap.release()

        def handle_code(code):
            if mode == "kasir":
                found = next((i for i in self.inventory if i.get("barcode") == code), None)
                if found:
                    self.add_to_cart(found)
                else:
                    self._show_barcode_not_found(code)
            elif mode == "stok":
                if target_input:
                    target_input.text = code
                elif hasattr(self, 'inp_barcode_stok'):
                    self.inp_barcode_stok.text = code
            elif mode == "edit" and target_input:
                target_input.text = code

        def on_manual(*a):
            stop_camera()
            popup.dismiss()
            self._open_manual_barcode_popup(mode=mode, target_input=target_input)

        def on_close(*a):
            stop_camera()
            popup.dismiss()

        popup.bind(on_dismiss=lambda *a: stop_camera())
        btn_manual.bind(on_release=on_manual)
        btn_close.bind(on_release=on_close)

        # Mulai thread kamera
        t = threading.Thread(target=open_camera_thread, daemon=True)
        t.start()
        popup.open()

    def _show_barcode_not_found(self, code):
        """Popup kecil saat barcode tidak cocok dengan produk manapun."""
        content = BoxLayout(orientation='vertical', padding=20, spacing=12)
        content.add_widget(Label(
            text=f"Barcode scanned:\n[b]{code}[/b]", markup=True,
            font_size='15sp', halign='center', size_hint_y=None, height=55
        ))
        content.add_widget(Label(
            text="Produk tidak ditemukan.\nDaftarkan barcode ini di tab STOK.",
            font_size='13sp', color=(1, 0.5, 0.5, 1),
            halign='center', size_hint_y=None, height=55
        ))
        btn_ok = ModernButton(text="OK", bg_color=(0.3, 0.3, 0.5, 1), size_hint_y=None, height=50)
        content.add_widget(btn_ok)
        p = Popup(title="Produk Tidak Ditemukan", content=content, size_hint=(0.8, 0.45))
        btn_ok.bind(on_release=p.dismiss)
        p.open()

    # ── Fallback: Input Manual ────────────────────────────────────────────────
    def _open_manual_barcode_popup(self, mode="kasir", target_input=None):
        """Dialog ketik barcode manual – fallback jika kamera tidak tersedia."""
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)

        install_note = ""
        if not CAMERA_SCAN_AVAILABLE:
            missing = []
            if not CV2_AVAILABLE:    missing.append("opencv-python")
            if not PYZBAR_AVAILABLE: missing.append("pyzbar")
            install_note = (
                f"\n[color=ff8800]Install library untuk kamera:\n"
                f"pip install {' '.join(missing)}[/color]"
            )

        content.add_widget(Label(
            text=f"[b]Scan Barcode[/b]{install_note}",
            markup=True, font_size='14sp',
            color=(0.8, 0.8, 1, 1), size_hint_y=None, height=60,
            halign='center'
        ))

        inp_bc = ModernInput(
            hint_text="Ketik atau scan barcode di sini…",
            multiline=False, size_hint_y=None, height=55, font_size='18sp'
        )
        content.add_widget(inp_bc)

        lbl_result = Label(
            text="", font_size='14sp', color=(1, 1, 0.4, 1),
            size_hint_y=None, height=38
        )
        content.add_widget(lbl_result)

        btn_ok = ModernButton(
            text="KONFIRMASI", bg_color=(0.1, 0.6, 0.3, 1),
            size_hint_y=None, height=55
        )
        content.add_widget(btn_ok)

        popup = Popup(
            title="Scan Barcode", content=content,
            size_hint=(0.85, 0.60), background_color=(0, 0, 0, 0.88)
        )

        def on_confirm(*a):
            code = inp_bc.text.strip()
            if not code:
                lbl_result.text = "Barcode kosong!"; return
            if mode == "kasir":
                found = next((i for i in self.inventory if i.get("barcode") == code), None)
                if found:
                    self.add_to_cart(found)
                    lbl_result.text = f"{found['nama']} ditambahkan ke keranjang"
                    inp_bc.text = ""
                else:
                    lbl_result.text = "Produk tidak ditemukan"
            elif mode == "stok":
                if target_input:
                    target_input.text = code
                elif hasattr(self, 'inp_barcode_stok'):
                    self.inp_barcode_stok.text = code
                popup.dismiss()
            elif mode == "edit" and target_input:
                target_input.text = code
                popup.dismiss()

        btn_ok.bind(on_release=on_confirm)
        inp_bc.bind(on_text_validate=on_confirm)   # Enter dari scanner USB/BT
        popup.open()
        inp_bc.focus = True

    # ── Product buttons ───────────────────────────────────────────────────────
    def refresh_product_buttons(self):
        self.product_grid.clear_widgets()
        query = self.search_input_kasir.text.lower() if hasattr(self, 'search_input_kasir') else ""
        for item in self.inventory:
            if query and query not in item['nama'].lower() and query not in item.get('barcode', ''):
                continue
            stok_text = f"Stok: {item['stok']}" if item['stok'] > 0 else "HABIS"
            btn_color  = (0.15, 0.17, 0.2, 1) if item['stok'] > 0 else (0.3, 0.1, 0.1, 1)
            bc_text    = f"\n[size=10sp]BC: {item.get('barcode','-')}[/size]" if item.get('barcode') else ""
            btn = ModernButton(
                text=(
                    f"{item['nama']}\n[b]Rp {item['harga']:,}[/b]\n"
                    f"[size=12sp]{stok_text}[/size]{bc_text}"
                ),
                markup=True, bg_color=btn_color,
                size_hint_y=None, height=130,
                halign='center',
                disabled=(item['stok'] <= 0)
            )
            btn.bind(on_release=lambda x, it=item: self.add_to_cart(it))
            self.product_grid.add_widget(btn)

    def add_to_cart(self, item):
        if item['stok'] > 0:
            item['stok'] -= 1
            self.cart.append({'nama': item['nama'], 'harga': item['harga'], 'sisa_stok': item['stok']})
            self.total_harga += item['harga']
            self.update_cart_display()
            self.refresh_product_buttons()
            self.refresh_inventory_list()

    def hapus_cart(self, index):
        cart_item = self.cart.pop(index)
        for inv_item in self.inventory:
            if inv_item['nama'] == cart_item['nama']:
                inv_item['stok'] += 1
                break
        self.total_harga -= cart_item['harga']
        self.update_cart_display()
        self.refresh_product_buttons()
        self.refresh_inventory_list()

    def update_cart_display(self):
        self.cart_list_layout.clear_widgets()
        for index, item in enumerate(self.cart):
            row = BoxLayout(size_hint_y=None, height=45, spacing=10)
            row.add_widget(Label(text=item['nama'], size_hint_x=0.6, font_size='14sp'))
            row.add_widget(Label(text=f"{item['harga']:,}", size_hint_x=0.3, font_size='14sp'))
            btn_rm = Button(
                text="×", size_hint_x=0.1,
                color=(1, 0, 0, 1), background_color=(0, 0, 0, 0), font_size='20sp'
            )
            btn_rm.bind(on_release=lambda x, i=index: self.hapus_cart(i))
            row.add_widget(btn_rm)
            self.cart_list_layout.add_widget(row)
        self.count_label.text  = f"Pcs: {len(self.cart)}"
        self.total_label.text  = f"TOTAL: Rp {self.total_harga:,}"

    # ══════════════════════════════════════════════════════════════════════════
    # TAB STOK
    # ══════════════════════════════════════════════════════════════════════════
    def build_inventory_ui(self):
        self.list_layout.clear_widgets()

        # Search
        search_box_inv = BoxLayout(size_hint_y=None, height=75, spacing=10)
        self.search_input_inv = ModernInput(hint_text="Cari di list barang…")
        self.search_input_inv.bind(text=lambda inst, val: self.refresh_inventory_list())
        search_box_inv.add_widget(self.search_input_inv)
        self.list_layout.add_widget(search_box_inv)

        # Baris header kolom input
        header_input = BoxLayout(size_hint_y=None, height=28, spacing=8, padding=[4, 0])
        for lbl_text, sx in [("Nama Produk", 0.30), ("Harga (Rp)", 0.20),
                              ("Stok", 0.12), ("Barcode", 0.22), ("", 0.09), ("", 0.07)]:
            header_input.add_widget(Label(
                text=lbl_text, font_size='12sp',
                color=(0.5, 0.7, 1, 1), size_hint_x=sx,
                halign='left', valign='middle'
            ))
        self.list_layout.add_widget(header_input)

        # Input form + tombol scan barcode
        input_area = BoxLayout(size_hint_y=None, height=52, spacing=8, padding=[4, 0])
        self.input_nama       = ModernInput(hint_text="Nama produk",  size_hint_x=0.30, font_size='13sp')
        self.input_harga      = ModernInput(hint_text="Harga",        size_hint_x=0.20, input_filter='int', font_size='13sp')
        self.input_stok       = ModernInput(hint_text="Stok",         size_hint_x=0.12, input_filter='int', font_size='13sp')
        self.inp_barcode_stok = ModernInput(hint_text="Kode barcode", size_hint_x=0.22, font_size='13sp')

        btn_scan_stok = ModernButton(
            text="SCAN", bg_color=(0.55, 0.28, 0.0, 1),
            size_hint_x=0.09, font_size='12sp'
        )
        btn_scan_stok.bind(on_release=self.open_barcode_scanner_stok)

        btn_add = ModernButton(text="SIMPAN", bg_color=(0.1, 0.6, 0.3, 1), size_hint_x=0.07, font_size='12sp')
        btn_add.bind(on_release=self.add_new_item)

        input_area.add_widget(self.input_nama)
        input_area.add_widget(self.input_harga)
        input_area.add_widget(self.input_stok)
        input_area.add_widget(self.inp_barcode_stok)
        input_area.add_widget(btn_scan_stok)
        input_area.add_widget(btn_add)
        self.list_layout.add_widget(input_area)

        # Garis pemisah
        sep = BoxLayout(size_hint_y=None, height=2)
        with sep.canvas.before:
            Color(0.2, 0.25, 0.3, 1)
            RoundedRectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, *a: w.canvas.before.clear() or
                 setattr(w, '_sep_draw', None))
        self.list_layout.add_widget(sep)

        # Header kolom list
        col_header = BoxLayout(size_hint_y=None, height=30, spacing=8, padding=[10, 0])
        for h_text, h_sx in [("Nama Produk", 0.30), ("Harga", 0.20),
                              ("Stok", 0.12), ("Barcode", 0.22), ("Aksi", 0.16)]:
            col_header.add_widget(Label(
                text=h_text, font_size='12sp', bold=True,
                color=(0.4, 0.6, 0.9, 1), size_hint_x=h_sx,
                halign='left', valign='middle'
            ))
        self.list_layout.add_widget(col_header)

        self.inv_display = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.inv_display.bind(minimum_height=self.inv_display.setter('height'))
        self.refresh_inventory_list()
        scroll = ScrollView()
        scroll.add_widget(self.inv_display)
        self.list_layout.add_widget(scroll)

    def refresh_inventory_list(self):
        self.inv_display.clear_widgets()
        query = self.search_input_inv.text.lower() if hasattr(self, 'search_input_inv') else ""
        for index, item in enumerate(self.inventory):
            if query and query not in item['nama'].lower():
                continue
            row = BoxLayout(size_hint_y=None, height=52, spacing=8, padding=[10, 4])
            with row.canvas.before:
                Color(0.12, 0.14, 0.18, 0.7)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[6])
            row.bind(pos=lambda w, *a: w.canvas.before.clear())

            bc_disp = item.get('barcode', '') or '-'

            lbl_nama = Label(
                text=item['nama'], size_hint_x=0.30,
                font_size='13sp', halign='left', valign='middle',
                text_size=(None, None), shorten=True, shorten_from='right'
            )
            lbl_nama.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

            lbl_harga = Label(
                text=f"Rp {item['harga']:,}", size_hint_x=0.20,
                color=(0.2, 0.6, 1, 1), font_size='13sp',
                halign='left', valign='middle'
            )
            lbl_stok = Label(
                text=str(item['stok']), size_hint_x=0.12,
                font_size='13sp', halign='center', valign='middle'
            )
            lbl_bc = Label(
                text=bc_disp, size_hint_x=0.22,
                font_size='12sp', color=(0.8, 0.75, 0.4, 1),
                halign='left', valign='middle',
                shorten=True, shorten_from='right'
            )
            lbl_bc.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

            btn_box = BoxLayout(size_hint_x=0.16, spacing=6)
            btn_edit = ModernButton(text="Edit",  bg_color=(0.2, 0.5, 0.8, 1), font_size='12sp')
            btn_del  = ModernButton(text="Hapus", bg_color=(0.8, 0.2, 0.2, 1), font_size='12sp')
            btn_edit.bind(on_release=lambda x, i=index: self.popup_edit_harga(i))
            btn_del.bind(on_release=lambda x,  i=index: self.delete_item(i))
            btn_box.add_widget(btn_edit)
            btn_box.add_widget(btn_del)

            row.add_widget(lbl_nama)
            row.add_widget(lbl_harga)
            row.add_widget(lbl_stok)
            row.add_widget(lbl_bc)
            row.add_widget(btn_box)
            self.inv_display.add_widget(row)

    def add_new_item(self, instance):
        if self.input_nama.text and self.input_harga.text.isdigit() and self.input_stok.text.isdigit():
            self.inventory.append({
                "nama":    self.input_nama.text,
                "harga":   int(self.input_harga.text),
                "stok":    int(self.input_stok.text),
                "barcode": self.inp_barcode_stok.text.strip(),
            })
            self.input_nama.text = ""
            self.input_harga.text = ""
            self.input_stok.text = ""
            self.inp_barcode_stok.text = ""
            self.refresh_inventory_list()
            self.refresh_product_buttons()

    def popup_edit_harga(self, index):
        item = self.inventory[index]
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        new_price_input   = ModernInput(text=str(item['harga']), input_filter='int', hint_text="Harga Baru")
        new_stok_input    = ModernInput(text=str(item['stok']),  input_filter='int', hint_text="Stok Baru")
        new_barcode_input = ModernInput(text=item.get('barcode',''), hint_text="Barcode (opsional)")
        btn_scan_edit     = ModernButton(text="Scan Barcode", bg_color=(0.6, 0.3, 0.0, 1), size_hint_y=None, height=45)
        btn_save          = ModernButton(text="UPDATE DATA", bg_color=(0.1, 0.6, 0.3, 1))

        content.add_widget(Label(text=f"Update [b]{item['nama']}[/b]", markup=True, halign='center'))
        content.add_widget(new_price_input)
        content.add_widget(new_stok_input)
        content.add_widget(new_barcode_input)
        content.add_widget(btn_scan_edit)
        content.add_widget(btn_save)

        popup = Popup(title="Edit Barang", content=content, size_hint=(0.85, 0.65))

        def scan_for_edit(*a):
            self._open_barcode_popup(mode="edit", target_input=new_barcode_input)

        def save_edit(*a):
            if new_price_input.text and new_stok_input.text:
                self.inventory[index]['harga']   = int(new_price_input.text)
                self.inventory[index]['stok']    = int(new_stok_input.text)
                self.inventory[index]['barcode'] = new_barcode_input.text.strip()
                self.refresh_inventory_list()
                self.refresh_product_buttons()
                popup.dismiss()

        btn_scan_edit.bind(on_release=scan_for_edit)
        btn_save.bind(on_release=save_edit)
        popup.open()


    def delete_item(self, index):
        self.inventory.pop(index)
        self.refresh_inventory_list()
        self.refresh_product_buttons()

    # ══════════════════════════════════════════════════════════════════════════
    # PEMBAYARAN
    # ══════════════════════════════════════════════════════════════════════════
    def show_payment_options(self, instance):
        if not self.cart: return
        content = BoxLayout(orientation='vertical', padding=25, spacing=15)
        content.add_widget(Label(text="Total Tagihan:", font_size='14sp'))
        content.add_widget(Label(text=f"Rp {self.total_harga:,}", font_size='30sp', bold=True))

        self.input_bayar = ModernInput(
            hint_text="Uang Tunai (Rp)", input_filter='int',
            font_size='24sp', halign='center'
        )
        content.add_widget(self.input_bayar)

        self.lbl_kembalian = Label(
            text="Kembalian: Rp 0", color=(0.2, 0.8, 0.2, 1), font_size='18sp'
        )
        content.add_widget(self.lbl_kembalian)
        self.input_bayar.bind(text=self.update_kembalian_label)

        btn_box = BoxLayout(spacing=15, size_hint_y=None, height=60)
        btn_cash = ModernButton(text="TUNAI / CASH", bg_color=(0.1, 0.6, 0.3, 1))
        btn_qris = ModernButton(text="SCAN QRIS",    bg_color=(0.1, 0.4, 0.9, 1))
        btn_box.add_widget(btn_cash)
        btn_box.add_widget(btn_qris)
        content.add_widget(btn_box)

        popup = Popup(
            title='Konfirmasi Pembayaran', content=content,
            size_hint=(0.9, 0.7), background_color=(0, 0, 0, 0.8)
        )
        btn_cash.bind(on_release=lambda x: (
            self.finish_payment(popup, "Cash")
            if self.input_bayar.text and int(self.input_bayar.text) >= self.total_harga
            else None
        ))
        btn_qris.bind(on_release=lambda x: self.show_qris_popup(popup))
        popup.open()

    def update_kembalian_label(self, instance, value):
        try:
            bayar = int(value) if value else 0
            selisih = bayar - self.total_harga
            if selisih >= 0:
                self.lbl_kembalian.text  = f"Kembalian: Rp {selisih:,}"
                self.lbl_kembalian.color = (0.2, 0.8, 0.2, 1)
            else:
                self.lbl_kembalian.text  = f"Kurang: Rp {abs(selisih):,}"
                self.lbl_kembalian.color = (0.9, 0.2, 0.2, 1)
        except:
            pass

    # ── QRIS Payment Popup ────────────────────────────────────────────────────
    def show_qris_popup(self, parent_popup):
        parent_popup.dismiss()
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)

        content.add_widget(Label(
            text=f"[b]Scan QRIS - Total Rp {self.total_harga:,}[/b]",
            markup=True, font_size='16sp', size_hint_y=None, height=35
        ))
        content.add_widget(Image(source=self.foto_qris, keep_ratio=True, size_hint_y=0.5))

        content.add_widget(Label(
            text="Setelah transfer, upload bukti bayar\natau klik Konfirmasi Manual:",
            font_size='13sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=45
        ))

        btn_row = BoxLayout(size_hint_y=None, height=60, spacing=10)
        btn_upload = ModernButton(text="Upload\nBukti", bg_color=(0.4, 0.2, 0.7, 1))
        btn_manual = ModernButton(text="Konfirmasi\nManual",  bg_color=(0.1, 0.6, 0.3, 1))
        btn_row.add_widget(btn_upload)
        btn_row.add_widget(btn_manual)
        content.add_widget(btn_row)

        self.lbl_qris_status = Label(
            text="", font_size='13sp',
            color=(1, 1, 0.4, 1), size_hint_y=None, height=30
        )
        content.add_widget(self.lbl_qris_status)

        popup_qris = Popup(
            title='Pembayaran QRIS', content=content,
            size_hint=(0.92, 0.88), background_color=(0, 0, 0, 0.85)
        )

        btn_upload.bind(on_release=lambda *a: self.upload_bukti_qris(popup_qris))
        btn_manual.bind(on_release=lambda *a: self.konfirmasi_qris_manual(popup_qris))
        popup_qris.open()

    def upload_bukti_qris(self, parent_popup):
        """Pilih file gambar sebagai bukti transfer QRIS."""
        content = BoxLayout(orientation='vertical', padding=10)
        fc = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg'])
        content.add_widget(fc)
        btn_sel = ModernButton(text="Gunakan Gambar Ini", size_hint_y=None, height=55)
        content.add_widget(btn_sel)
        popup_fc = Popup(title="Pilih Bukti Pembayaran", content=content, size_hint=(0.95, 0.92))

        def on_select(*a):
            if fc.selection:
                bukti_path = fc.selection[0]
                popup_fc.dismiss()
                self._verifikasi_bukti_qris(parent_popup, bukti_path)

        btn_sel.bind(on_release=on_select)
        popup_fc.open()

    def _verifikasi_bukti_qris(self, parent_popup, bukti_path):
        """Tampilkan gambar bukti + tombol Setujui / Tolak (untuk admin / kasir)."""
        content = BoxLayout(orientation='vertical', padding=15, spacing=12)
        content.add_widget(Label(
            text="[b]Verifikasi Bukti Pembayaran QRIS[/b]", markup=True,
            font_size='15sp', size_hint_y=None, height=35
        ))
        content.add_widget(Image(source=bukti_path, keep_ratio=True, size_hint_y=0.55))
        content.add_widget(Label(
            text=f"Total: Rp {self.total_harga:,}",
            font_size='16sp', bold=True, color=(0.2, 0.8, 0.4, 1),
            size_hint_y=None, height=35
        ))

        btn_row = BoxLayout(size_hint_y=None, height=60, spacing=10)
        btn_setuju = ModernButton(text="SETUJUI\nPEMBAYARAN", bg_color=(0.1, 0.6, 0.3, 1))
        btn_tolak  = ModernButton(text="TOLAK",               bg_color=(0.7, 0.1, 0.1, 1))
        btn_row.add_widget(btn_setuju)
        btn_row.add_widget(btn_tolak)
        content.add_widget(btn_row)

        popup_verify = Popup(
            title="Verifikasi QRIS", content=content,
            size_hint=(0.9, 0.85), background_color=(0, 0, 0, 0.88)
        )

        def setujui(*a):
            popup_verify.dismiss()
            parent_popup.dismiss()
            self.finish_payment_qris_verified(bukti_path)

        def tolak(*a):
            popup_verify.dismiss()
            if hasattr(self, 'lbl_qris_status'):
                self.lbl_qris_status.text = "Pembayaran DITOLAK - coba lagi"
                self.lbl_qris_status.color = (1, 0.3, 0.3, 1)

        btn_setuju.bind(on_release=setujui)
        btn_tolak.bind(on_release=tolak)
        popup_verify.open()

    def konfirmasi_qris_manual(self, parent_popup):
        """Konfirmasi pembayaran QRIS tanpa bukti gambar (kasir konfirmasi lisan)."""
        content = BoxLayout(orientation='vertical', padding=25, spacing=15)
        content.add_widget(Label(
            text="[b]Konfirmasi Pembayaran QRIS[/b]", markup=True,
            font_size='16sp', size_hint_y=None, height=35
        ))
        content.add_widget(Label(
            text=f"Total: Rp {self.total_harga:,}", font_size='22sp',
            bold=True, color=(0.2, 0.8, 0.4, 1), size_hint_y=None, height=40
        ))
        content.add_widget(Label(
            text="Pastikan notifikasi transfer sudah\nditerima sebelum konfirmasi!",
            font_size='13sp', color=(1, 0.85, 0.2, 1), size_hint_y=None, height=50
        ))

        btn_row = BoxLayout(size_hint_y=None, height=60, spacing=10)
        btn_ya   = ModernButton(text="YA, SUDAH\nDITERIMA",  bg_color=(0.1, 0.6, 0.3, 1))
        btn_batal = ModernButton(text="BATAL",               bg_color=(0.5, 0.2, 0.2, 1))
        btn_row.add_widget(btn_ya)
        btn_row.add_widget(btn_batal)
        content.add_widget(btn_row)

        popup_conf = Popup(
            title="Konfirmasi Manual QRIS", content=content,
            size_hint=(0.85, 0.6), background_color=(0, 0, 0, 0.88)
        )

        def on_ya(*a):
            popup_conf.dismiss()
            parent_popup.dismiss()
            self.finish_payment(popup_conf, "QRIS-Manual")

        btn_ya.bind(on_release=on_ya)
        btn_batal.bind(on_release=lambda *a: popup_conf.dismiss())
        popup_conf.open()

    def finish_payment_qris_verified(self, bukti_path):
        """Simpan transaksi QRIS setelah bukti diverifikasi."""
        self.finish_payment(None, "QRIS-Bukti", extra_info=bukti_path)

    def finish_payment(self, popup, metode, extra_info=""):
        if metode == "Cash":
            if not self.input_bayar.text or int(self.input_bayar.text) < self.total_harga:
                return
        now = datetime.now()
        file_exists = os.path.exists(self.file_laporan)
        try:
            with open(self.file_laporan, mode='a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Tanggal", "Jam", "Produk", "Harga", "Metode",
                                     "Status", "Sisa Stok", "Info"])
                for item in self.cart:
                    writer.writerow([
                        now.strftime("%Y-%m-%d"),
                        now.strftime("%H:%M:%S"),
                        item['nama'],
                        item['harga'],
                        metode,
                        "Terbeli (1)",
                        item['sisa_stok'],
                        extra_info
                    ])
            self.cart = []
            self.total_harga = 0
            self.update_cart_display()
            if popup:
                try: popup.dismiss()
                except: pass
        except:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # TAB PENGATURAN (admin only)
    # ══════════════════════════════════════════════════════════════════════════
    def build_import_ui(self):
        self.import_layout.clear_widgets()

        # ── Import CSV ────────────────────────────────────────────────────────
        self.import_layout.add_widget(Label(
            text="Import Produk (CSV)", font_size='18sp', bold=True,
            size_hint_y=None, height=35
        ))
        btn_open_folder = ModernButton(
            text="PILIH FILE CSV", bg_color=(0.2, 0.5, 0.8, 1),
            size_hint_y=None, height=65
        )
        btn_open_folder.bind(on_release=self.buka_file_chooser)
        self.import_layout.add_widget(btn_open_folder)

        self.btn_import_aksi = ModernButton(
            text="KONFIRMASI IMPORT", bg_color=(0.1, 0.6, 0.3, 1),
            size_hint_y=None, height=65, disabled=True
        )
        self.btn_import_aksi.bind(on_release=self.proses_import_csv)
        self.import_layout.add_widget(self.btn_import_aksi)

        self.import_layout.add_widget(BoxLayout(size_hint_y=None, height=15))

        # ── QRIS ──────────────────────────────────────────────────────────────
        self.import_layout.add_widget(Label(
            text="Pengaturan QRIS Pembayaran", font_size='18sp', bold=True,
            size_hint_y=None, height=35
        ))
        btn_upload_qris = ModernButton(
            text="UPLOAD / GANTI FOTO QRIS", bg_color=(0.6, 0.2, 0.8, 1),
            size_hint_y=None, height=65
        )
        btn_upload_qris.bind(on_release=self.buka_file_chooser_qris)
        self.import_layout.add_widget(btn_upload_qris)

        self.import_layout.add_widget(BoxLayout(size_hint_y=None, height=15))

        # ── Ganti Password ────────────────────────────────────────────────────
        self.import_layout.add_widget(Label(
            text="Manajemen Akun", font_size='18sp', bold=True,
            size_hint_y=None, height=35
        ))
        btn_change_pass = ModernButton(
            text="GANTI PASSWORD AKUN", bg_color=(0.4, 0.35, 0.1, 1),
            size_hint_y=None, height=65
        )
        btn_change_pass.bind(on_release=self.popup_ganti_password)
        self.import_layout.add_widget(btn_change_pass)

        self.status_import = Label(text="Status: Siap", color=(0.5, 0.5, 0.5, 1))
        self.import_layout.add_widget(self.status_import)

    # ── File chooser CSV ──────────────────────────────────────────────────────
    def buka_file_chooser(self, instance):
        content = BoxLayout(orientation='vertical', padding=10)
        self.file_chooser = FileChooserIconView(filters=['*.csv'])
        content.add_widget(self.file_chooser)
        btn_select = ModernButton(text="Pilih File Ini", size_hint_y=None, height=60)
        content.add_widget(btn_select)
        self.popup_file = Popup(title="Pilih File CSV", content=content, size_hint=(0.95, 0.95))
        btn_select.bind(on_release=self.file_selected_confirm)
        self.popup_file.open()

    def file_selected_confirm(self, instance):
        if self.file_chooser.selection:
            self.selected_path = self.file_chooser.selection[0]
            self.btn_import_aksi.disabled = False
            self.status_import.text = f"CSV Terpilih: {os.path.basename(self.selected_path)}"
            self.popup_file.dismiss()

    def proses_import_csv(self, instance):
        try:
            with open(self.selected_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 4:
                        stok    = int(row[4]) if len(row) > 4 else 0
                        barcode = row[5].strip() if len(row) > 5 else ""
                        self.inventory.append({
                            "nama":    row[2],
                            "harga":   int(float(row[3])),
                            "stok":    stok,
                            "barcode": barcode,
                        })
            self.refresh_inventory_list()
            self.refresh_product_buttons()
            self.status_import.text = "Berhasil Import CSV!"
        except Exception as e:
            self.status_import.text = f"Gagal Import: {e}"

    # ── File chooser QRIS ─────────────────────────────────────────────────────
    def buka_file_chooser_qris(self, instance):
        content = BoxLayout(orientation='vertical', padding=10)
        self.file_chooser_qris = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg'])
        content.add_widget(self.file_chooser_qris)
        btn_select = ModernButton(text="Gunakan Foto Ini sebagai QRIS", size_hint_y=None, height=60)
        content.add_widget(btn_select)
        self.popup_file_qris = Popup(title="Pilih Gambar QRIS", content=content, size_hint=(0.95, 0.95))
        btn_select.bind(on_release=self.qris_selected_confirm)
        self.popup_file_qris.open()

    def qris_selected_confirm(self, instance):
        if self.file_chooser_qris.selection:
            self.foto_qris = self.file_chooser_qris.selection[0]
            self.status_import.text = "QRIS Berhasil Diganti!"
            self.popup_file_qris.dismiss()

    # ── Ganti password ────────────────────────────────────────────────────────
    def popup_ganti_password(self, *args):
        content = BoxLayout(orientation='vertical', padding=20, spacing=12)
        content.add_widget(Label(
            text="[b]Ganti Password Akun[/b]", markup=True,
            font_size='16sp', size_hint_y=None, height=35
        ))
        inp_user    = ModernInput(hint_text="Username", multiline=False, size_hint_y=None, height=48)
        inp_old     = ModernInput(hint_text="Password Lama", password=True, multiline=False, size_hint_y=None, height=48)
        inp_new     = ModernInput(hint_text="Password Baru", password=True, multiline=False, size_hint_y=None, height=48)
        inp_confirm = ModernInput(hint_text="Konfirmasi Password Baru", password=True, multiline=False, size_hint_y=None, height=48)
        lbl_msg     = Label(text="", font_size='13sp', color=(1, 0.4, 0.4, 1), size_hint_y=None, height=30)
        btn_save    = ModernButton(text="SIMPAN", bg_color=(0.1, 0.6, 0.3, 1), size_hint_y=None, height=50)

        for w in [inp_user, inp_old, inp_new, inp_confirm, lbl_msg, btn_save]:
            content.add_widget(w)

        popup = Popup(title="Ganti Password", content=content, size_hint=(0.85, 0.75))

        def do_change(*a):
            username = inp_user.text.strip()
            old_h    = hashlib.sha256(inp_old.text.encode()).hexdigest()
            if username not in ACCOUNTS:
                lbl_msg.text = "Username tidak ditemukan"; return
            if ACCOUNTS[username]["password"] != old_h:
                lbl_msg.text = "Password lama salah"; return
            if inp_new.text != inp_confirm.text:
                lbl_msg.text = "Konfirmasi password tidak cocok"; return
            if len(inp_new.text) < 6:
                lbl_msg.text = "Password minimal 6 karakter"; return
            ACCOUNTS[username]["password"] = hashlib.sha256(inp_new.text.encode()).hexdigest()
            save_accounts(ACCOUNTS)
            lbl_msg.text  = "Password berhasil diubah!"
            lbl_msg.color = (0.2, 0.9, 0.3, 1)

        btn_save.bind(on_release=do_change)
        popup.open()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB OMZET – Dashboard Modern
    # ══════════════════════════════════════════════════════════════════════════
    def build_laporan_ui(self):
        self.laporan_layout.clear_widgets()
        self.laporan_layout.padding  = [14, 10, 14, 10]
        self.laporan_layout.spacing  = 10
        self._filter_mode = "semua"

        # ── Kartu Grand Total ─────────────────────────────────────────────────
        grand_card = BoxLayout(
            orientation='vertical', size_hint_y=None, height=88,
            padding=[22, 8], spacing=2
        )
        self._setup_card_bg(grand_card, (0.05, 0.32, 0.18, 1), radius=18)

        self.lbl_grand_sub = Label(
            text="Total Omzet Keseluruhan",
            font_size='12sp', color=(0.55, 0.95, 0.72, 1),
            halign='center', size_hint_y=None, height=20
        )
        self.lbl_grand_val = Label(
            text="Rp 0", font_size='32sp', bold=True,
            color=(0.22, 1.0, 0.58, 1), halign='center'
        )
        self.lbl_grand_trx = Label(
            text="0 transaksi", font_size='11sp',
            color=(0.4, 0.75, 0.55, 1), halign='center',
            size_hint_y=None, height=16
        )
        grand_card.add_widget(self.lbl_grand_sub)
        grand_card.add_widget(self.lbl_grand_val)
        grand_card.add_widget(self.lbl_grand_trx)
        self.laporan_layout.add_widget(grand_card)

        # ── 3 Kartu Periode (Hari / Minggu / Bulan) ───────────────────────────
        periode_row = BoxLayout(size_hint_y=None, height=100, spacing=10)
        card_specs = [
            ("Hari Ini",   "lbl_hari_val",   "lbl_hari_trx",   (0.08, 0.22, 0.52, 1)),
            ("Minggu Ini", "lbl_minggu_val", "lbl_minggu_trx", (0.32, 0.10, 0.52, 1)),
            ("Bulan Ini",  "lbl_bulan_val",  "lbl_bulan_trx",  (0.50, 0.24, 0.05, 1)),
        ]
        for judul, attr_val, attr_trx, warna in card_specs:
            c = BoxLayout(orientation='vertical', padding=[10, 8], spacing=2)
            self._setup_card_bg(c, warna, radius=14)
            lbl_j = Label(text=judul, font_size='11sp',
                          color=(0.8, 0.88, 1, 0.9), halign='center',
                          size_hint_y=None, height=18)
            lbl_v = Label(text="Rp 0", font_size='15sp', bold=True,
                          color=(1, 1, 1, 1), halign='center')
            lbl_t = Label(text="0 trx", font_size='10sp',
                          color=(0.7, 0.7, 0.8, 0.8), halign='center',
                          size_hint_y=None, height=16)
            c.add_widget(lbl_j); c.add_widget(lbl_v); c.add_widget(lbl_t)
            setattr(self, attr_val, lbl_v)
            setattr(self, attr_trx, lbl_t)
            periode_row.add_widget(c)
        self.laporan_layout.add_widget(periode_row)

        # ── Kartu Breakdown Metode Bayar ──────────────────────────────────────
        metode_row = BoxLayout(size_hint_y=None, height=72, spacing=10)
        metode_specs = [
            ("Cash / Tunai", "lbl_met_cash", (0.10, 0.42, 0.24, 1)),
            ("QRIS",         "lbl_met_qris", (0.10, 0.32, 0.70, 1)),
            ("Lainnya",      "lbl_met_lain", (0.30, 0.30, 0.30, 1)),
        ]
        for judul, attr, warna in metode_specs:
            c = BoxLayout(orientation='vertical', padding=[8, 6], spacing=1)
            self._setup_card_bg(c, warna, radius=12)
            lbl_j = Label(text=judul, font_size='10sp',
                          color=(0.75, 0.90, 0.80, 0.9), halign='center',
                          size_hint_y=None, height=16)
            lbl_v = Label(text="Rp 0", font_size='13sp', bold=True,
                          color=(1, 1, 1, 1), halign='center')
            c.add_widget(lbl_j); c.add_widget(lbl_v)
            setattr(self, attr, lbl_v)
            metode_row.add_widget(c)
        self.laporan_layout.add_widget(metode_row)

        # ── Bar filter ────────────────────────────────────────────────────────
        filter_wrap = BoxLayout(size_hint_y=None, height=38,
                                padding=[0, 2], spacing=6)
        self._filter_btns = {}
        for label, key in [("Semua", "semua"), ("Bulan Ini", "bulan"),
                            ("Minggu Ini", "minggu"), ("Hari Ini", "hari")]:
            btn = Button(
                text=label, font_size='12sp',
                background_normal='', background_down='',
                background_color=(0.16, 0.20, 0.28, 1),
                color=(0.75, 0.75, 0.80, 1)
            )
            btn.bind(on_release=lambda x, k=key: self._set_filter(k))
            self._filter_btns[key] = btn
            filter_wrap.add_widget(btn)
        self.laporan_layout.add_widget(filter_wrap)
        self._set_filter("semua", rebuild=False)

        # ── Tombol aksi ───────────────────────────────────────────────────────
        aksi_row = BoxLayout(size_hint_y=None, height=42, spacing=10)
        btn_ref = ModernButton(
            text="Refresh", bg_color=(0.16, 0.20, 0.28, 1),
            font_size='13sp'
        )
        btn_ref.bind(on_release=lambda *a: self.refresh_laporan())
        btn_reset = ModernButton(
            text="Reset Omzet", bg_color=(0.50, 0.08, 0.08, 1),
            font_size='13sp'
        )
        btn_reset.bind(on_release=self._confirm_reset_omzet)
        aksi_row.add_widget(btn_ref)
        aksi_row.add_widget(btn_reset)
        self.laporan_layout.add_widget(aksi_row)

        # ── Label judul list ──────────────────────────────────────────────────
        self.lbl_list_judul = Label(
            text="Riwayat Transaksi", font_size='13sp', bold=True,
            color=(0.55, 0.70, 1, 1),
            size_hint_y=None, height=28, halign='left'
        )
        self.laporan_layout.add_widget(self.lbl_list_judul)

        # ── List transaksi (scrollable) ───────────────────────────────────────
        self.trx_list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.trx_list_layout.bind(minimum_height=self.trx_list_layout.setter('height'))
        scroll_trx = ScrollView(bar_width=4, bar_color=(0.3, 0.5, 1, 0.6))
        scroll_trx.add_widget(self.trx_list_layout)
        self.laporan_layout.add_widget(scroll_trx)

        self.refresh_laporan()

    # ── Helper: setup background rounded rect pada card ───────────────────────
    def _setup_card_bg(self, widget, color, radius=14):
        """Gambar background rounded rect dan daftarkan bind resize."""
        def _draw(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(*color)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[radius])
        widget.bind(pos=_draw, size=_draw)
        _draw(widget)

    # ── Helper: redraw generik (untuk widget lama yg masih pakai _redraw_bg) ──
    def _redraw_bg(self, widget, *args):
        if hasattr(widget, '_bg_color'):
            widget.canvas.before.clear()
            with widget.canvas.before:
                Color(*widget._bg_color)
                RoundedRectangle(pos=widget.pos, size=widget.size,
                                 radius=getattr(widget, '_bg_radius', [10]))

    # ── Set filter aktif ──────────────────────────────────────────────────────
    def _set_filter(self, key, rebuild=True):
        self._filter_mode = key
        for k, btn in self._filter_btns.items():
            if k == key:
                btn.background_color = (0.12, 0.42, 1, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.16, 0.20, 0.28, 1)
                btn.color = (0.70, 0.70, 0.78, 1)
        if rebuild:
            self.refresh_laporan()

    # ── Reset omzet ───────────────────────────────────────────────────────────
    def _confirm_reset_omzet(self, *args):
        content = BoxLayout(orientation='vertical', padding=22, spacing=14)
        content.add_widget(Label(
            text="Hapus semua data laporan?\nTindakan ini tidak bisa dibatalkan.",
            font_size='14sp', color=(1, 0.85, 0.4, 1),
            halign='center', size_hint_y=None, height=55
        ))
        btn_row = BoxLayout(size_hint_y=None, height=52, spacing=12)
        btn_ya    = ModernButton(text="YA, HAPUS",  bg_color=(0.65, 0.08, 0.08, 1))
        btn_batal = ModernButton(text="BATAL",      bg_color=(0.20, 0.24, 0.32, 1))
        btn_row.add_widget(btn_ya); btn_row.add_widget(btn_batal)
        content.add_widget(btn_row)
        pop = Popup(title="Konfirmasi Reset", content=content,
                    size_hint=(0.82, 0.38), background_color=(0, 0, 0, 0.88))
        def do_reset(*a):
            if os.path.exists(self.file_laporan):
                os.remove(self.file_laporan)
            pop.dismiss()
            self.refresh_laporan()
        btn_ya.bind(on_release=do_reset)
        btn_batal.bind(on_release=pop.dismiss)
        pop.open()

    # ── Baca data CSV ─────────────────────────────────────────────────────────
    def _baca_transaksi(self):
        rows = []
        if not os.path.exists(self.file_laporan):
            return rows
        try:
            with open(self.file_laporan, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for r in reader:
                    if len(r) >= 5:
                        rows.append({
                            "tgl":    r[0].strip(),
                            "jam":    r[1].strip(),
                            "produk": r[2].strip(),
                            "harga":  int(float(r[3])) if r[3].strip() else 0,
                            "metode": r[4].strip(),
                        })
        except:
            pass
        return rows

    # ── Refresh semua angka + list ────────────────────────────────────────────
    def refresh_laporan(self):
        from datetime import date, timedelta

        today     = date.today()
        str_today = today.strftime("%Y-%m-%d")
        monday    = today - timedelta(days=today.weekday())
        str_mon   = monday.strftime("%Y-%m-%d")
        str_bulan = today.strftime("%Y-%m")

        semua = self._baca_transaksi()

        def tot(rows): return sum(r["harga"] for r in rows)

        hari_rows   = [r for r in semua if r["tgl"] == str_today]
        minggu_rows = [r for r in semua if r["tgl"] >= str_mon]
        bulan_rows  = [r for r in semua if r["tgl"].startswith(str_bulan)]

        # cash / qris / lainnya (semua data)
        cash_rows = [r for r in semua if "cash" in r["metode"].lower()]
        qris_rows = [r for r in semua if "qris" in r["metode"].lower()]
        lain_rows = [r for r in semua
                     if "cash" not in r["metode"].lower()
                     and "qris" not in r["metode"].lower()]

        # Kartu grand total
        self.lbl_grand_val.text = f"Rp {tot(semua):,}"
        self.lbl_grand_trx.text = f"{len(semua)} transaksi"

        # Kartu periode
        self.lbl_hari_val.text   = f"Rp {tot(hari_rows):,}"
        self.lbl_hari_trx.text   = f"{len(hari_rows)} trx"
        self.lbl_minggu_val.text = f"Rp {tot(minggu_rows):,}"
        self.lbl_minggu_trx.text = f"{len(minggu_rows)} trx"
        self.lbl_bulan_val.text  = f"Rp {tot(bulan_rows):,}"
        self.lbl_bulan_trx.text  = f"{len(bulan_rows)} trx"

        # Kartu metode
        self.lbl_met_cash.text = f"Rp {tot(cash_rows):,}"
        self.lbl_met_qris.text = f"Rp {tot(qris_rows):,}"
        self.lbl_met_lain.text = f"Rp {tot(lain_rows):,}"

        # Pilih data sesuai filter lalu render list
        filter_map = {
            "hari": hari_rows, "minggu": minggu_rows,
            "bulan": bulan_rows, "semua": semua
        }
        tampil = filter_map.get(self._filter_mode, semua)

        # Update judul list
        judul_map = {
            "hari": "Transaksi Hari Ini",
            "minggu": "Transaksi Minggu Ini",
            "bulan": "Transaksi Bulan Ini",
            "semua": "Riwayat Transaksi",
        }
        self.lbl_list_judul.text = (
            f"{judul_map.get(self._filter_mode, 'Riwayat Transaksi')}"
            f"  —  Rp {tot(tampil):,}  ({len(tampil)} trx)"
        )

        self._render_trx_list(tampil)

    # ── Render list transaksi ─────────────────────────────────────────────────
    def _render_trx_list(self, rows):
        self.trx_list_layout.clear_widgets()

        if not rows:
            empty = BoxLayout(size_hint_y=None, height=60, padding=[12, 10])
            self._setup_card_bg(empty, (0.11, 0.13, 0.17, 1), radius=12)
            empty.add_widget(Label(
                text="Belum ada transaksi pada periode ini.",
                font_size='13sp', color=(0.45, 0.48, 0.55, 1), halign='center'
            ))
            self.trx_list_layout.add_widget(empty)
            return

        # Kelompokkan per tanggal (terbaru di atas)
        from collections import OrderedDict
        grouped = OrderedDict()
        for r in reversed(rows):
            grouped.setdefault(r["tgl"], []).append(r)

        METODE_COLOR = {
            "cash":        (0.10, 0.52, 0.28, 1),
            "qris":        (0.10, 0.38, 0.80, 1),
            "qris-manual": (0.10, 0.38, 0.80, 1),
            "qris-bukti":  (0.10, 0.38, 0.80, 1),
        }

        for tgl, trx_hari in grouped.items():
            subtotal = sum(r["harga"] for r in trx_hari)

            # ── Header grup tanggal ───────────────────────────────────────────
            hdr = BoxLayout(size_hint_y=None, height=30,
                            padding=[12, 4], spacing=8)
            self._setup_card_bg(hdr, (0.14, 0.17, 0.23, 1), radius=8)

            # Format tanggal lebih ramah
            try:
                from datetime import datetime as dt2
                tgl_fmt = dt2.strptime(tgl, "%Y-%m-%d").strftime("%d %b %Y")
            except:
                tgl_fmt = tgl

            hdr.add_widget(Label(
                text=tgl_fmt, font_size='12sp', bold=True,
                color=(0.55, 0.75, 1, 1), halign='left', size_hint_x=0.45
            ))
            hdr.add_widget(Label(
                text=f"{len(trx_hari)} transaksi",
                font_size='11sp', color=(0.55, 0.60, 0.68, 1),
                halign='center', size_hint_x=0.30
            ))
            hdr.add_widget(Label(
                text=f"Rp {subtotal:,}", font_size='12sp', bold=True,
                color=(0.28, 0.92, 0.55, 1), halign='right', size_hint_x=0.25
            ))
            self.trx_list_layout.add_widget(hdr)

            # ── Baris tiap transaksi ──────────────────────────────────────────
            for idx, r in enumerate(trx_hari):
                row_bg = (0.11, 0.14, 0.19, 1) if idx % 2 == 0 else (0.13, 0.17, 0.23, 1)
                row = BoxLayout(size_hint_y=None, height=54,
                                padding=[12, 6], spacing=10)
                self._setup_card_bg(row, row_bg, radius=10)

                # Kolom kiri: nama + jam + metode badge
                left = BoxLayout(orientation='vertical', size_hint_x=0.60, spacing=2)

                nama_row = BoxLayout(size_hint_y=None, height=22, spacing=8)

                # Badge metode (kecil, inline dengan nama)
                met_key   = r["metode"].lower()
                met_color = METODE_COLOR.get(met_key, (0.30, 0.30, 0.35, 1))
                badge_lbl = Label(
                    text=r["metode"].upper(),
                    font_size='9sp', bold=True, color=(1, 1, 1, 1),
                    size_hint=(None, 1), width=52
                )
                badge_wrap = BoxLayout(size_hint=(None, 1), width=52)
                self._setup_card_bg(badge_wrap, met_color, radius=6)
                badge_wrap.add_widget(badge_lbl)
                nama_row.add_widget(badge_wrap)

                nama_lbl = Label(
                    text=r["produk"], font_size='13sp', bold=True,
                    color=(0.92, 0.93, 0.95, 1), halign='left', valign='middle'
                )
                nama_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
                nama_row.add_widget(nama_lbl)
                left.add_widget(nama_row)

                jam_lbl = Label(
                    text=r["jam"], font_size='11sp',
                    color=(0.40, 0.45, 0.55, 1),
                    halign='left', size_hint_y=None, height=18
                )
                left.add_widget(jam_lbl)
                row.add_widget(left)

                # Kolom kanan: harga
                harga_lbl = Label(
                    text=f"Rp {r['harga']:,}",
                    font_size='14sp', bold=True,
                    color=(0.28, 0.90, 0.55, 1),
                    size_hint_x=0.40, halign='right', valign='middle'
                )
                harga_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
                row.add_widget(harga_lbl)

                self.trx_list_layout.add_widget(row)


# ══════════════════════════════════════════════════════════════════════════════
# APP ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
class KasirApp(App):
    def build(self):
        self.title = "Kasirku – @ Junaid adzan isnam"
        self.sm = ScreenManager()

        def on_login_success(username, role):
            main = MainScreen(
                name="main",
                username=username,
                role=role,
                on_logout=self.do_logout
            )
            if "main" in [s.name for s in self.sm.screens]:
                self.sm.remove_widget(self.sm.get_screen("main"))
            self.sm.add_widget(main)
            self.sm.current = "main"

        login = LoginScreen(name="login", on_success=on_login_success)
        self.sm.add_widget(login)
        return self.sm

    def do_logout(self):
        if "main" in [s.name for s in self.sm.screens]:
            self.sm.remove_widget(self.sm.get_screen("main"))
        self.sm.current = "login"
        # Reset input login
        login = self.sm.get_screen("login")
        login.inp_user.text = ""
        login.inp_pass.text = ""
        login.lbl_err.text  = ""


if __name__ == '__main__':
    KasirApp().run()
