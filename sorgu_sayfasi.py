import os
import sys
import subprocess
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QWidget, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import webbrowser
from database import DatabaseManager

class SorguSayfasi(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("🔍 Arşiv Sorgulama v27.8")
        self.resize(1300, 850)
        
        self.setStyleSheet("""
            QDialog { background-color: #1A1F25; }
            QLabel { color: #ECEFF4; font-family: 'Segoe UI', sans-serif; }
            
            QLineEdit { 
                padding: 10px 15px; font-size: 15px; border-radius: 10px; 
                border: 1px solid #2C3E50;
                background-color: #242B33; color: #ECEFF4;
            }
            QLineEdit:focus {
                border: 2px solid #3498DB;
                background-color: #1E252B;
            }
            
            QTableWidget { 
                background-color: #242B33; 
                border: 1px solid #2C3E50;
                border-radius: 12px; 
                font-size: 14px;
                color: #ECEFF4;
                gridline-color: #1F252C;
                selection-background-color: #3498DB;
                outline: none;
            }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:alternate { background-color: #1E252B; }
            QTableWidget::item:selected { background-color: #3498DB; color: white; }
            
            QHeaderView::section { 
                background-color: #1F252C; color: #95A5A6; padding: 8px; 
                font-weight: bold; border: none; font-size: 13px;
                border-bottom: 2px solid #3498DB;
            }
            
            QScrollBar:vertical {
                border: none; background: #1A1F25; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical { background: #34495E; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #3498DB; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 20)

        # --- KURUMSAL LOGO ALANI ---
        logo_header = QHBoxLayout()
        self.lbl_logo = QLabel()
        self.lbl_logo.setObjectName("QueryLogo")
        self.lbl_logo.setStyleSheet("""
            QLabel#QueryLogo { 
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F0F4F8);
                border-radius: 15px; 
                padding: 10px; 
                border: 1px solid #D1D8E0;
            }
        """)
        logo_path = "logo.png"
        if self.parent() and hasattr(self.parent(), 'config'):
            logo_path = self.parent().config.get("logo_dosyasi", "logo.png")
            
        # Logo arama sırası: 1. Dış Dosya, 2. Gömülü Dosya (PyInstaller desteği için)
        from main import resource_path
        final_logo_path = logo_path if os.path.exists(logo_path) else resource_path(logo_path)
        
        if os.path.exists(final_logo_path):
            pix = QPixmap(final_logo_path)
            self.lbl_logo.setPixmap(pix.scaledToHeight(50, Qt.SmoothTransformation))
        else:
            self.lbl_logo.setText("ARŞİV SORGULAMA")
            self.lbl_logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #3498DB; background: white; border-radius: 15px; padding: 8px;")
        
        logo_header.addWidget(self.lbl_logo, 0, Qt.AlignCenter)
        layout.addLayout(logo_header)
        layout.addSpacing(15)
        
        # Arama Çubuğu
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("ARŞİVDE ARA:"))
        self.search_txt = QLineEdit()
        self.search_txt.setPlaceholderText("Kod, Plaka, Konu veya Tarih ile hızlıca bulun...")
        self.search_txt.textChanged.connect(self.ara)
        search_layout.addWidget(self.search_txt)
        layout.addLayout(search_layout)
        
        # Tablo (İsimli Sütun Erişimi İçin 7 Sütun)
        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(50) # Satır yüksekliğini artır
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels([
            "KOD", "EVRAK TARİHİ", "KAYIT ZAMANI", "PLAKA", "KONU", "DOSYA YOLU", "İŞLEMLER"
        ])
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive) # Manuel boyutlandırmaya izin ver
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 260)
        
        # Hücre tıklama sinyalini bağla
        self.table.cellClicked.connect(self.hucre_tiklandi)
        
        layout.addWidget(self.table)
        self.ara()

    def hucre_tiklandi(self, row, col):
        """Dosya yolu sütununa tıklandığında klasörü açar ve dosyayı seçer."""
        if col == 5: # DOSYA YOLU sütunu
            path = self.table.item(row, col).data(Qt.UserRole)
            if path and os.path.exists(path):
                subprocess.run(["explorer", "/select,", os.path.normpath(path)])

    def ara(self):
        """İsimli sütun erişimi (Row Factory) ile veri çekme."""
        results = self.db.search_evrak(self.search_txt.text())
        self.table.setRowCount(len(results))
        for i, row in enumerate(results):
            # database.py Row Factory sayesinde isimle erişim (Claude Standardı)
            mapping = [
                row['kod'], row['tarih'], row['kayit_zamani'], 
                row['plaka'], row['konu'], row['path']
            ]
            for j, val in enumerate(mapping):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                
                # Dosya yolu sütunu için link görünümü ve veri saklama
                if j == 5:
                    item.setForeground(Qt.cyan)
                    font = item.font()
                    font.setUnderline(True)
                    item.setFont(font)
                    item.setData(Qt.UserRole, val) # Tam yolu sakla
                    item.setToolTip("Klasörde Göster")
                
                self.table.setItem(i, j, item)
            
            # İşlem Butonları
            btn_container = QWidget()
            btn_l = QHBoxLayout(btn_container); btn_l.setContentsMargins(5,5,5,5)
            btn_l.setSpacing(10)
            
            btn_open = QPushButton("👁️ AÇ")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setMinimumHeight(35)
            btn_open.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #27AE60, stop:1 #219150);
                    color: white; font-weight: bold; 
                    padding: 5px 20px; border-radius: 18px; border: none; font-size: 13px;
                }
                QPushButton:hover { background: #2ECC71; margin-top: -1px; }
            """)
            btn_open.clicked.connect(lambda ch=False, p=row['path']: self.evrensel_dosya_ac(p))
            
            btn_del = QPushButton("🗑️ SİL")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setMinimumHeight(35)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #C0392B, stop:1 #A93226);
                    color: white; font-weight: bold; 
                    padding: 5px 20px; border-radius: 18px; border: none; font-size: 13px;
                }
                QPushButton:hover { background: #E74C3C; margin-top: -1px; }
            """)
            btn_del.clicked.connect(lambda ch=False, k=row['kod']: self.evrak_sil(k))
            
            # Paylaş Butonu
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction
            btn_share = QPushButton("📤 PAYLAŞ")
            btn_share.setCursor(Qt.PointingHandCursor)
            btn_share.setMinimumHeight(35)
            btn_share.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #3498DB, stop:1 #2980B9);
                    color: white; font-weight: bold; padding: 5px 15px; border-radius: 18px; border: none; font-size: 13px;
                }
                QPushButton:hover { background: #5DADE2; margin-top: -1px; }
                QPushButton::menu-indicator { image: none; }
            """)
            share_menu = QMenu(self)
            share_menu.setStyleSheet("QMenu { background-color: #2C3E50; color: white; border-radius: 8px; } QMenu::item:selected { background-color: #3498DB; }")
            
            email_act = QAction("📧 E-Posta Gönder", self)
            email_act.triggered.connect(lambda: self.e_posta_gonder(row['path'], row['kod']))
            
            wa_act = QAction("💬 WhatsApp'ta Paylaş", self)
            wa_act.triggered.connect(lambda: self.whatsapp_paylas(row['path']))
            
            share_menu.addAction(email_act)
            share_menu.addAction(wa_act)
            btn_share.setMenu(share_menu)
            
            btn_l.addWidget(btn_open)
            btn_l.addWidget(btn_share)
            btn_l.addWidget(btn_del)
            self.table.setCellWidget(i, 6, btn_container)

    def e_posta_gonder(self, path, kod):
        """Dosyayı e-posta taslağı olarak açar."""
        subject = f"Evrak Kaydı: {kod}"
        body = f"Sayın İlgili,\n\n{kod} kodlu evrak ekte sunulmuştur.\n\nİyi çalışmalar."
        # Not: mailto eki her istemcide çalışmayabilir, ekleme manuel gerekebilir
        url = f"mailto:?subject={subject}&body={body}"
        webbrowser.open(url)
        # Klasörü de açalım ki eki sürükleyip bıraksın
        if path and os.path.exists(path):
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])

    def whatsapp_paylas(self, path):
        """WhatsApp Web'i açar ve dosya için klasörü hazır eder."""
        webbrowser.open("https://web.whatsapp.com/")
        # WhatsApp Web eki otomatik alamaz, klasörü açıp kolaylık sağlıyoruz
        if path and os.path.exists(path):
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])
            QMessageBox.information(self, "WhatsApp Paylaşımı", 
                                  "WhatsApp Web açıldı.\n\nLütfen açılan klasördeki dosyayı WhatsApp mesaj alanına sürükleyip bırakın.")

    def evrensel_dosya_ac(self, path):
        """Claude Önerisi: Platform bağımsız dosya açma (Windows, Linux, Mac)."""
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Hata", "Dosya arşivde bulunamadı!")
            return

        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", path])
            else: # Linux
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı: {e}")

    def evrak_sil(self, kod):
        """Claude Önerisi: Tutarlı silme (Dosya silinemezse DB silinmez)."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Kayıt Silme")
        msg.setText(f"<b>{kod}</b> numaralı kaydı ve dosyasını silmek istiyor musunuz?")
        evet = msg.addButton("Evet, Sil", QMessageBox.YesRole)
        hayir = msg.addButton("Hayır, Vazgeç", QMessageBox.NoRole)
        msg.setIcon(QMessageBox.Warning)
        msg.exec()
        
        if msg.clickedButton() == evet:
            if self.db.delete_evrak(kod):
                self.ara()
                QMessageBox.information(self, "Bilgi", "Kayıt ve dosya başarıyla temizlendi.")
            else:
                QMessageBox.critical(self, "Hata", "Dosya kullanımda olduğu için silme işlemi iptal edildi!")