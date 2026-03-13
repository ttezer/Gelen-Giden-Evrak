import sys, os, json, shutil, logging, datetime, pytesseract
print("-" * 50)
print("Herşey VATAN için... Tacettin TEZER")
print("-" * 50)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QMessageBox, QFileDialog, QFrame, QDateEdit, QInputDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QCloseEvent, QPixmap

# Loglama Yapılandırması
logging.basicConfig(
    filename="sistem.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

from database import DatabaseManager
from viewer import DocumentViewer
from sorgu_sayfasi import SorguSayfasi
from scanner import ScannerManager

def resource_path(relative_path):
    """ PyInstaller için iç ve dış dosya yollarını yönetir. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base_dir():
    """ Programın çalıştırıldığı ana klasörü döner (.exe ise dış klasör). """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class BelgeKayitSistemi(QMainWindow):
    def __init__(self):
        super().__init__()
        # Çalışma dizinini programın bulunduğu yere sabitle
        os.chdir(get_base_dir())
        
        self.config = self.load_config()  # Config ÖNCE yüklenmeli
        self.db = DatabaseManager(arsiv_dir=self.config.get("arsiv_klasoru", "Arsiv"))
        self.scanner = ScannerManager(wia_guid=self.config.get("wia_format_guid"))
        self.setup_tesseract()
        self.init_ui()

    def load_config(self):
        # HATA DÜZELTİLDİ: Metod gövdesi doğru girintilendi (IndentationError giderildi)
        default_cfg = {
            "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            "arsiv_klasoru": "Arsiv",
            "varsayilan_tip": "Gelen",
            "varsayilan_kategori": "Otobüs",
            "wia_format_guid": "{B96B3CA3-0728-11D3-9D7B-0000F81EF32E}",
            "log_dosyasi": "sistem.log",
            "sirket_adi": "Belge Arşiv Sistemi",
            "logo_dosyasi": "logo.png"
        }
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    default_cfg.update(user_cfg)
            except Exception as e:
                logging.error(f"Config Okuma Hatası: {e}")
        else:
            # Yapılandırma dosyası yoksa varsayılanı oluştur (Portable mod)
            try:
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(default_cfg, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Config yazma hatası: {e}")
        return default_cfg

    def setup_tesseract(self):
        t_path = self.config.get("tesseract_path")
        if not os.path.exists(t_path): t_path = shutil.which("tesseract")
        if t_path: pytesseract.pytesseract.tesseract_cmd = t_path

    def init_ui(self):
        sirket = self.config.get("sirket_adi", "Belge Arşiv Sistemi")
        self.setWindowTitle(f"🏛️ {sirket} ARŞİV KAYIT VE OCR SİSTEMİ v27.8")
        self.resize(1600, 950)
        self.setStyleSheet("""
            QMainWindow { background-color: #1A1F25; }
            QLabel { color: #ECEFF4; font-family: 'Segoe UI', sans-serif; }
            
            /* Modern Giriş Kutuları */
            QLineEdit, QComboBox, QDateEdit { 
                padding: 10px 15px; 
                min-height: 45px;
                border: 1px solid #2C3E50; 
                border-radius: 12px; 
                background-color: #242B33; 
                color: #ECEFF4; 
                font-size: 15px;
                selection-background-color: #3498DB;
            }
            
            QLineEdit:hover, QComboBox:hover, QDateEdit:hover {
                border-color: #34495E;
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { 
                border: 2px solid #3498DB; 
                background-color: #1E252B;
            }

            /* QComboBox Özel Tasarım */
            QComboBox { combobox-popup: 0; }
            QComboBox::drop-down {
                border-left: 1px solid #2C3E50;
                background-color: #242B33;
                width: 40px;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #3498DB;
            }
            QComboBox QAbstractItemView {
                background-color: #242B33;
                color: #ECEFF4;
                border: 1px solid #34495E;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                selection-background-color: #3498DB;
                outline: none;
                padding: 5px;
            }
            QComboBox::item { 
                padding: 10px;
                border-radius: 8px;
                margin: 2px 5px;
            }
            QComboBox::item:selected {
                background-color: #3498DB;
                color: white;
            }
            
            /* QDateEdit Özel Tasarım */
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 40px;
                border-left: 1px solid #2C3E50;
                background-color: #242B33;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #3498DB;
            }
            
            /* Takvim Widget Modernleştirme */
            QCalendarWidget QWidget { background-color: #1A1F25; color: #ECEFF4; }
            QCalendarWidget QTableView { 
                background-color: #242B33; 
                selection-background-color: #3498DB; 
                border-radius: 12px;
            }
            QCalendarWidget QToolButton {
                color: white;
                background: transparent;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
            QCalendarWidget QToolButton:hover { background-color: #3498DB; }
            
            /* Paneller */
            QFrame#LeftPanel {
                background-color: #242B33;
            QInputDialog QLabel, QMessageBox QLabel {
                color: white;
                font-size: 14px;
            }
            QInputDialog QLineEdit {
                background-color: #2C3E50;
                color: white;
                border: 1px solid #3498DB;
                border-radius: 5px;
                padding: 5px;
            }
            QInputDialog QPushButton, QMessageBox QPushButton {
                background-color: #2980B9;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QInputDialog QPushButton:hover, QMessageBox QPushButton:hover {
                background-color: #3498DB;
            }
        """)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QHBoxLayout(main_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_panel.setFixedWidth(430)
        # Stil QMainWindow'da global olarak tanımlandı
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # LOGO: Önce dışarıdaki logo.png'ye bak, yoksa içindeki gömülü olana bak
        logo_path = self.config.get("logo_dosyasi", "logo.png")
        sirket_adi = self.config.get("sirket_adi", "Belge Arşiv Sistemi")
        
        self.lbl_main_logo = QLabel()
        self.lbl_main_logo.setObjectName("MainLogo")
        self.lbl_main_logo.setStyleSheet("""
            QLabel#MainLogo { 
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F0F4F8);
                border-radius: 20px; 
                padding: 15px; 
                border: 1px solid #D1D8E0;
            }
        """)
        
        # Logo arama sırası: 1. Dış Dosya, 2. Gömülü Dosya
        final_logo_path = logo_path if os.path.exists(logo_path) else resource_path(logo_path)
        
        if os.path.exists(final_logo_path):
            pix = QPixmap(final_logo_path)
            self.lbl_main_logo.setPixmap(pix.scaledToWidth(280, Qt.SmoothTransformation))
        else:
            self.lbl_main_logo.setText(sirket_adi.upper())
            self.lbl_main_logo.setStyleSheet("font-size: 32px; font-weight: bold; color: #3498DB; background: white; border-radius: 20px; padding: 10px;")
        
        self.lbl_main_logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_main_logo)
        layout.addSpacing(10)

        title = QLabel("EVRAK KAYIT FORMU")
        title.setFont(QFont("Segoe UI Semibold", 18))
        title.setStyleSheet("color: #ECEFF4; margin-top: 5px; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        
        # Başlık + Alan Yönetimi menüsü satırı
        title_row = QHBoxLayout()
        title_row.addWidget(title, 1)
        
        from PySide6.QtWidgets import QMenu
        self.btn_alan_menu = QPushButton("⚙️")
        self.btn_alan_menu.setCursor(Qt.PointingHandCursor)
        self.btn_alan_menu.setFixedSize(45, 45)
        self.btn_alan_menu.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; color: white;
                border-radius: 12px; font-size: 20px; border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #34495E; border-color: #3498DB; }
            QPushButton::menu-indicator { image: none; }
        """)
        alan_menu = QMenu(self)
        alan_menu.setStyleSheet("""
            QMenu { 
                background-color: #242B33; color: #ECEFF4; 
                border: 1px solid #34495E; border-radius: 12px; 
                font-size: 14px; padding: 5px;
            }
            QMenu::item { padding: 10px 30px; border-radius: 8px; margin: 2px; }
            QMenu::item:selected { background-color: #3498DB; color: white; }
        """)
        alan_menu.addAction("➕ Yeni Alan Ekle", self.yeni_alan_ekle)
        alan_menu.addAction("✏️ Alanı Düzenle", self.alan_duzenle)
        alan_menu.addAction("🗑️ Alanı Sil", self.alan_sil)
        self.btn_alan_menu.setMenu(alan_menu)
        title_row.addWidget(self.btn_alan_menu, 0)
        layout.addLayout(title_row)
        layout.addSpacing(15)

        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        
        varsayilan_tip = self.config.get("varsayilan_tip", "Gelen")
        varsayilan_kat = self.config.get("varsayilan_kategori", "Otobüs")
        
        # === SABİT ALANLAR ===
        self.fields = {}
        self.field_labels = {}  # key -> QLabel widget (dinamik güncelleme için)
        
        # Evrak Tipi (sabit)
        self.fields["tip"] = QComboBox()
        self.fields["tip"].addItems(["Gelen", "Giden"])
        if varsayilan_tip in ["Gelen", "Giden"]:
            self.fields["tip"].setCurrentText(varsayilan_tip)
        
        # Kategori (sabit)
        self.fields["kat"] = QComboBox()
        kat_items = self.db.get_kategoriler()
        if not kat_items: kat_items = ["Genel"]
        self.fields["kat"].addItems(kat_items)
        if varsayilan_kat in kat_items:
            self.fields["kat"].setCurrentText(varsayilan_kat)
        
        # Evrak Tarihi (sabit)
        self.fields["tarih"] = QDateEdit(QDate.currentDate())
        self.fields["tarih"].setCalendarPopup(True)
        self.fields["tarih"].setDisplayFormat("dd.MM.yyyy")
        
        # Sabit alanları grid'e yerleştir
        sabit_alanlar = [
            ("Evrak Tipi", "tip"),
            ("Kategori", "kat"),
        ]
        row_idx = 0
        for label_text, key in sabit_alanlar:
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet("font-weight: bold; color: #95A5A6; font-size: 13px;")
            self.grid.addWidget(lbl, row_idx, 0)
            
            if key == "kat":
                kat_layout = QHBoxLayout()
                kat_layout.setContentsMargins(0, 0, 0, 0)
                kat_layout.addWidget(self.fields[key], 1)
                
                self.btn_kat_menu = QPushButton("⚙️")
                self.btn_kat_menu.setCursor(Qt.PointingHandCursor)
                self.btn_kat_menu.setFixedSize(40, 40)
                self.btn_kat_menu.setStyleSheet("""
                    QPushButton {
                        background-color: #2C3E50; color: white;
                        border-radius: 10px; font-size: 18px; border: 1px solid #34495E;
                    }
                    QPushButton:hover { background-color: #34495E; border-color: #3498DB; }
                    QPushButton::menu-indicator { image: none; }
                """)
                kat_menu = QMenu(self)
                kat_menu.setStyleSheet("""
                    QMenu { 
                        background-color: #242B33; color: #ECEFF4; 
                        border: 1px solid #34495E; border-radius: 12px; padding: 5px;
                    }
                    QMenu::item { padding: 8px 25px; border-radius: 6px; }
                    QMenu::item:selected { background-color: #3498DB; }
                """)
                kat_menu.addAction("➕ Yeni Kategori", self.yeni_kategori_ekle)
                kat_menu.addAction("✏️ Düzenle", self.kategori_duzenle)
                kat_menu.addAction("🗑️ Sil", self.kategori_sil)
                self.btn_kat_menu.setMenu(kat_menu)
                kat_layout.addWidget(self.btn_kat_menu, 0)
                self.grid.addLayout(kat_layout, row_idx, 1)
            else:
                self.grid.addWidget(self.fields[key], row_idx, 1)
            row_idx += 1
        
        # === DİNAMİK ALANLAR (DB'den yüklenir) ===
        self.dinamik_alan_baslangic_row = row_idx
        self._dinamik_alanlari_olustur()
        
        # Evrak Tarihi - dinamik alanlardan sonra en sona
        self.tarih_row = None  # _dinamik_alanlari_olustur içinde ayarlanır
        layout.addLayout(self.grid)
        layout.addSpacing(15)
        
        self.btn_scan = self.create_btn("📸 BELGE TARA", "#3498DB")
        self.btn_file = self.create_btn("📁 DOSYA SEÇ", "#9B59B6")
        self.btn_save = self.create_btn("💾 SİSTEME KAYDET", "#27AE60", height=65, glow=True)
        self.btn_search = self.create_btn("🔍 ARŞİVDE ARA", "#E67E22")
        self.btn_exit = self.create_btn("🚪 SİSTEMDEN ÇIK", "#E74C3C", height=40)
        
        self.btn_scan.clicked.connect(self.tara)
        self.btn_file.clicked.connect(self.dosya_sec)
        self.btn_save.clicked.connect(self.kaydet)
        self.btn_search.clicked.connect(self.sorgula)
        self.btn_exit.clicked.connect(self.close)

        layout.addWidget(self.btn_scan); layout.addWidget(self.btn_file)
        layout.addSpacing(10); layout.addWidget(self.btn_save)
        layout.addSpacing(10); layout.addWidget(self.btn_search)
        layout.addSpacing(10); layout.addWidget(self.btn_exit)
        
        # === İMZA (Herşey VATAN için... Tacettin TEZER) ===
        layout.addStretch(1) # Boşluk bırak
        imza = QLabel("Herşey VATAN için... Tacettin TEZER")
        imza.setStyleSheet("color: #34495E; font-size: 11px; font-style: italic; margin-top: 10px;")
        imza.setAlignment(Qt.AlignCenter)
        layout.addWidget(imza)
        
        self.main_layout.addWidget(left_panel)

    def setup_right_panel(self):
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        ctrl_bar = QHBoxLayout()
        btn_style = "min-width: 65px; min-height: 55px; font-size: 28px;"
        
        self.btn_prev = self.create_btn("⬅️", "#34495E", style=btn_style)
        self.btn_next = self.create_btn("➡️", "#34495E", style=btn_style)
        self.btn_z_in = self.create_btn("🔍+", "#2980B9", style=btn_style)
        self.btn_z_out = self.create_btn("🔍-", "#2980B9", style=btn_style)
        self.btn_z_res = self.create_btn("🔍1:1", "#16A085", style=btn_style)
        self.btn_rot = self.create_btn("🔄", "#8E44AD", style=btn_style)
        self.btn_clear = self.create_btn("🗑️ TEMİZLE", "#C0392B", 
                                          style="min-width: 160px; min-height: 55px; font-size: 20px; font-weight: bold;")
        
        for b in [self.btn_prev, self.btn_next, self.btn_z_in, self.btn_z_out, 
                  self.btn_z_res, self.btn_rot, self.btn_clear]:
            ctrl_bar.addWidget(b)
        
        right_layout.addLayout(ctrl_bar)
        self.viewer = DocumentViewer()
        self.viewer.setStyleSheet("background-color: #242B33; border: 2px solid #34495E; border-radius: 12px;")
        self.viewer.request_menu.connect(self.ocr_menu)
        right_layout.addWidget(self.viewer)
        
        self.lbl_page = QLabel("Sayfa: 0 / 0")
        self.lbl_page.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_page)
        
        self.viewer.page_changed.connect(lambda c, t: self.lbl_page.setText(f"Sayfa: {c} / {t}"))
        self.btn_prev.clicked.connect(self.viewer.prev_page)
        self.btn_next.clicked.connect(self.viewer.next_page)
        self.btn_z_in.clicked.connect(self.viewer.zoom_in)
        self.btn_z_out.clicked.connect(self.viewer.zoom_out)
        self.btn_z_res.clicked.connect(self.viewer.reset_zoom)
        self.btn_rot.clicked.connect(lambda: self.viewer.rotate_img(90))
        self.btn_clear.clicked.connect(self.komple_temizle)

        self.main_layout.addWidget(right_container, 1)

    def create_btn(self, text, color, height=50, style="", glow=False):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        
        # Daha modern, degrade ve animasyonlu buton CSS'i
        s = f"""
            QPushButton {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                            stop:0 {color}, stop:1 {self._darken_color(color)});
                color: white;
                font-weight: bold;
                border-radius: {height // 2}px;
                min-height: {height}px;
                padding: 0 20px;
                border: none;
                font-family: 'Segoe UI Semibold', sans-serif;
                {style}
            }}
            QPushButton:hover {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                            stop:0 {self._lighten_color(color)}, stop:1 {color});
                margin-top: -2px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            QPushButton:pressed {{
                background: {color};
                margin-top: 1px;
            }}
        """
        if glow:
            s += f"""
                QPushButton {{
                    border: 2px solid #2ECC71;
                    box-shadow: 0 0 15px rgba(46, 204, 113, 0.4);
                }}
            """
        
        btn.setStyleSheet(s)
        return btn

    def _darken_color(self, hex_color, amount=0.2):
        """Renk değerini koyulaştıran yardımcı metod."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        dark_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#%02x%02x%02x' % dark_rgb

    def _lighten_color(self, hex_color, amount=0.2):
        """Renk değerini açıklaştıran yardımcı metod."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        light_rgb = tuple(min(255, int(c + (255 - c) * amount)) for c in rgb)
        return '#%02x%02x%02x' % light_rgb

    def yeni_kategori_ekle(self):
        text, ok = QInputDialog.getText(self, "Yeni Kategori", "Kategori Adı:")
        if ok and text.strip():
            kategori_adi = text.strip()
            if self.db.add_kategori(kategori_adi):
                self.fields["kat"].clear()
                self.fields["kat"].addItems(self.db.get_kategoriler())
                self.fields["kat"].setCurrentText(kategori_adi)
            else:
                QMessageBox.warning(self, "Uyarı", "Bu kategori zaten var veya eklenemedi!")

    def kategori_duzenle(self):
        mevcut = self.fields["kat"].currentText()
        if not mevcut or mevcut == "Genel":
            return QMessageBox.warning(self, "Uyarı", "'Genel' kategorisi veya boş seçim düzenlenemez!")
            
        text, ok = QInputDialog.getText(self, "Kategori Düzenle", f"'{mevcut}' için yeni ad:", text=mevcut)
        if ok and text.strip() and text.strip() != mevcut:
            yeni_ad = text.strip()
            if self.db.update_kategori(mevcut, yeni_ad):
                self.fields["kat"].clear()
                self.fields["kat"].addItems(self.db.get_kategoriler())
                self.fields["kat"].setCurrentText(yeni_ad)
                QMessageBox.information(self, "Başarılı", "Kategori ve bağlı evraklar güncellendi.")
            else:
                QMessageBox.warning(self, "Hata", "Kategori güncellenemedi (İsim çakışması olabilir).")

    def kategori_sil(self):
        mevcut = self.fields["kat"].currentText()
        if not mevcut or mevcut == "Genel":
            return QMessageBox.warning(self, "Uyarı", "'Genel' kategorisi veya boş seçim silinemez!")
            
        cevap = QMessageBox.question(self, "Silme Onayı", 
            f"'{mevcut}' kategorisini silmek istediğinize emin misiniz?\n(Bu kategoriye ait mevcut evraklar 'Genel' kategorisine taşınacaktır.)",
            QMessageBox.Yes | QMessageBox.No)
            
        if cevap == QMessageBox.Yes:
            if self.db.remove_kategori(mevcut):
                # Evraklar tablosundaki silinen kategorileri Genel'e aktar
                with self.db.get_connection() as conn:
                    conn.execute("UPDATE evraklar SET kategori='Genel' WHERE kategori=?", (mevcut,))
                
                self.fields["kat"].clear()
                self.fields["kat"].addItems(self.db.get_kategoriler())
                self.fields["kat"].setCurrentText("Genel")
                QMessageBox.information(self, "Başarılı", "Kategori silindi ve ilgili evraklar 'Genel'e aktarıldı.")
            else:
                QMessageBox.warning(self, "Hata", "Kategori silinemedi!")

    def komple_temizle(self):
        self.viewer.clear_view()
        self.lbl_page.setText("Sayfa: 0 / 0")
        for widget in self.fields.values():
            if isinstance(widget, QLineEdit): widget.clear()
            elif isinstance(widget, QComboBox): widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit): widget.setDate(QDate.currentDate())
        self.fields["ad1"].setFocus()

    def closeEvent(self, event: QCloseEvent):
        msg = QMessageBox(self)
        msg.setWindowTitle("Sistem Çıkış")
        msg.setText("Uygulamadan ayrılıyorsunuz?")
        evet = msg.addButton("Evet", QMessageBox.YesRole)
        hayir = msg.addButton("Hayır", QMessageBox.NoRole)
        msg.setIcon(QMessageBox.Question)
        msg.exec()
        if msg.clickedButton() == evet: event.accept()
        else: event.ignore()

    def tara(self):
        path = self.scanner.scan_to_file()
        if path: self.viewer.load_file(path)

    def dosya_sec(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", 
                                               "Belgeler (*.pdf *.jpg *.png *.jpeg)")
        if path: self.viewer.load_file(path)

    def ocr_menu(self, text, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2C3E50; color: white; border: 1px solid #34495E; font-size: 14px; }
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background-color: #3498DB; }
        """)
        # Dinamik alanlardan menü oluştur (tarih hariç)
        alan_tanimlari = self.db.get_alan_tanimlari()
        for alan in alan_tanimlari:
            key = alan['alan_key']
            adi = alan['alan_adi']
            if key in self.fields:
                widget = self.fields[key]
                menu.addAction(f"{adi}'ye Aktar", lambda w=widget, t=text: w.setText(t))
        menu.exec(pos.toPoint())

    def _dinamik_alanlari_olustur(self):
        """Dinamik alanları DB'den okuyarak form grid'ine yerleştirir."""
        alan_tanimlari = self.db.get_alan_tanimlari()
        row_idx = self.dinamik_alan_baslangic_row
        
        for alan in alan_tanimlari:
            key = alan['alan_key']
            adi = alan['alan_adi']
            
            lbl = QLabel(f"{adi}:")
            lbl.setStyleSheet("font-weight: bold; color: #BDC3C7;")
            self.field_labels[key] = lbl
            self.grid.addWidget(lbl, row_idx, 0)
            
            widget = QLineEdit()
            self.fields[key] = widget
            self.grid.addWidget(widget, row_idx, 1)
            row_idx += 1
        
        # Evrak Tarihi en sona
        lbl_tarih = QLabel("Evrak Tarihi:")
        lbl_tarih.setStyleSheet("font-weight: bold; color: #95A5A6; font-size: 13px;")
        self.grid.addWidget(lbl_tarih, row_idx, 0)
        self.grid.addWidget(self.fields["tarih"], row_idx, 1)
        self.tarih_row = row_idx

    def _formu_yeniden_olustur(self):
        """Dinamik alanları temizleyip yeniden oluşturur."""
        # Grid'deki dinamik satırları (dinamik_alan_baslangic_row'dan itibaren) tamamen temizle
        max_row = self.grid.rowCount()
        for row in range(self.dinamik_alan_baslangic_row, max_row + 1):
            for col in range(self.grid.columnCount()):
                item = self.grid.itemAtPosition(row, col)
                if item is not None:
                    w = item.widget()
                    if w is not None and w != self.fields.get("tarih"):
                        self.grid.removeWidget(w)
                        w.setParent(None)
                        w.deleteLater()
                    elif w == self.fields.get("tarih"):
                        self.grid.removeWidget(w)
        
        # fields ve field_labels dict'lerinden dinamik kayıtları temizle
        for key in list(self.fields.keys()):
            if key not in ("tip", "kat", "tarih"):
                self.fields.pop(key)
        self.field_labels.clear()
        
        # Yeniden oluştur
        self._dinamik_alanlari_olustur()

    def yeni_alan_ekle(self):
        text, ok = QInputDialog.getText(self, "Yeni Alan Ekle", "Alan Adı (ör: Cihaz No):")
        if ok and text.strip():
            basarili, sonuc = self.db.add_alan(text.strip())
            if basarili:
                self._formu_yeniden_olustur()
                QMessageBox.information(self, "Başarılı", f"'{text.strip()}' alanı eklendi.")
            else:
                QMessageBox.warning(self, "Hata", f"Alan eklenemedi: {sonuc}")

    def alan_duzenle(self):
        alan_tanimlari = self.db.get_alan_tanimlari()
        if not alan_tanimlari:
            return QMessageBox.warning(self, "Uyarı", "Düzenlenecek alan bulunamadı.")
        
        alan_listesi = [a['alan_adi'] for a in alan_tanimlari]
        from PySide6.QtWidgets import QInputDialog
        secilen, ok = QInputDialog.getItem(self, "Alan Düzenle", "Düzenlemek istediğiniz alanı seçin:", 
                                            alan_listesi, 0, False)
        if not ok:
            return
        
        # Seçilen alanın key'ini bul
        secilen_alan = next(a for a in alan_tanimlari if a['alan_adi'] == secilen)
        
        yeni_ad, ok2 = QInputDialog.getText(self, "Alan Düzenle", 
                                              f"'{secilen}' için yeni ad:", text=secilen)
        if ok2 and yeni_ad.strip() and yeni_ad.strip() != secilen:
            if self.db.update_alan(secilen_alan['alan_key'], yeni_ad.strip()):
                self._formu_yeniden_olustur()
                QMessageBox.information(self, "Başarılı", f"Alan adı '{yeni_ad.strip()}' olarak güncellendi.")
            else:
                QMessageBox.warning(self, "Hata", "Alan güncellenemedi.")

    def alan_sil(self):
        alan_tanimlari = self.db.get_alan_tanimlari()
        if not alan_tanimlari:
            return QMessageBox.warning(self, "Uyarı", "Silinecek alan bulunamadı.")
        
        alan_listesi = [a['alan_adi'] for a in alan_tanimlari]
        from PySide6.QtWidgets import QInputDialog
        secilen, ok = QInputDialog.getItem(self, "Alanı Sil", "Silmek istediğiniz alanı seçin:", 
                                            alan_listesi, 0, False)
        if not ok:
            return
        
        secilen_alan = next(a for a in alan_tanimlari if a['alan_adi'] == secilen)
        
        cevap = QMessageBox.question(self, "Silme Onayı", 
            f"'{secilen}' alanını kaldırmak istediğinize emin misiniz?\n(Mevcut veriler korunur, alan sadece gizlenir.)",
            QMessageBox.Yes | QMessageBox.No)
        
        if cevap == QMessageBox.Yes:
            if self.db.remove_alan(secilen_alan['alan_key']):
                self._formu_yeniden_olustur()
                QMessageBox.information(self, "Başarılı", f"'{secilen}' alanı kaldırıldı.")
            else:
                QMessageBox.warning(self, "Hata", "Alan silinemedi.")


    def kaydet(self):
        if not self.viewer.current_image:
            return QMessageBox.warning(self, "Hata", "Önce bir belge yükleyin!")
        try:
            tip = self.fields["tip"].currentText()
            kat = self.fields["kat"].currentText()
            
            is_pdf = self.viewer.pdf_doc is not None
            source_file_path = self.viewer.current_file_path
            
            if is_pdf:
                self.viewer.pdf_doc.close()
                self.viewer.pdf_doc = None

            zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            data = {
                "tip": tip, "kategori": kat, 
                "tarih": self.fields["tarih"].date().toString("dd.MM.yyyy"),
                "kayit_zamani": zaman
            }
            
            # Dinamik alanları data dict'e ekle
            alan_tanimlari = self.db.get_alan_tanimlari()
            for alan in alan_tanimlari:
                key = alan['alan_key']
                if key in self.fields:
                    data[key] = self.fields[key].text()

            ok, result_data = self.db.secure_insert_evrak(
                data, is_pdf, self.viewer.current_image, source_file_path
            )

            if ok:
                QMessageBox.information(self, "Bilgi", f"KAYDEDİLDİ: {result_data}")
                self.komple_temizle()
            else:
                QMessageBox.critical(self, "Hata", result_data)

        except Exception as e:
            logging.error(f"Kayit Hatasi: {e}")
            QMessageBox.critical(self, "Kritik Hata", str(e))

    def sorgula(self):
        self.s_pencere = SorguSayfasi(self)
        self.s_pencere.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = BelgeKayitSistemi()
    win.show()
    sys.exit(app.exec())
