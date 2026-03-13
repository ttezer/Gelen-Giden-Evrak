import os
import tempfile
import time
import logging

try:
    import win32com.client
    WIA_AVAILABLE = True
except ImportError:
    WIA_AVAILABLE = False
    logging.error("pywin32 kütüphanesi eksik! Tarama özelliği devre dışı.")

DEFAULT_WIA_GUID = "{B96B3CA3-0728-11D3-9D7B-0000F81EF32E}"

class ScannerManager:
    def __init__(self, wia_guid=None):
        # GÜNCELLEME: WIA format GUID config'den alınıyor, yoksa varsayılan kullanılır
        self.wia_guid = wia_guid or DEFAULT_WIA_GUID
        self.wia_dialog = None

    def scan_to_file(self):
        """Benzersiz dosya adıyla tarama yapar."""
        if not WIA_AVAILABLE:
            logging.error("Tarama denemesi başarısız: WIA kütüphanesi yüklü değil.")
            return None

        if self.wia_dialog is None:
            try:
                # WIA Dialog'u sadece tarama yapılacağı zaman yükle (ilk açılışta donmayı engeller)
                self.wia_dialog = win32com.client.Dispatch("WIA.CommonDialog")
            except Exception as e:
                logging.error(f"WIA Dialog Başlatılamadı: {e}")
                return None

        try:
            timestamp = int(time.time())
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, f"scan_{timestamp}.jpg")

            image = self.wia_dialog.ShowAcquireImage(
                DeviceType=1,
                Intent=1,
                Bias=128,
                FormatID=self.wia_guid,  # Config'den gelen GUID
                AlwaysSelectDevice=False
            )

            if image:
                if os.path.exists(target_path):
                    os.remove(target_path)
                image.SaveFile(target_path)
                return target_path

            return None

        except Exception as e:
            logging.error(f"Fiziksel Tarama Hatası: {e}")
            return None

    def is_scanner_connected(self):
        """Tarayıcı bağlantısını kontrol eder."""
        if not WIA_AVAILABLE:
            return False
        try:
            dev_mgr = win32com.client.Dispatch("WIA.DeviceManager")
            return dev_mgr.DeviceInfos.Count > 0
        except Exception as e:
            logging.error(f"Tarayıcı Bağlantı Sorgulama Hatası: {e}")
            return False
