import sqlite3
import os
import logging
from utils import get_file_hash, stamp_pdf, stamp_image

class DatabaseManager:
    def __init__(self, db_name="evraklar.db", arsiv_dir="Arsiv"):
        self.db_name = db_name
        self.arsiv_dir = arsiv_dir  # Config'den gelen arşiv klasörü
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        # Arşiv dizinlerini oluştur
        os.makedirs(os.path.join(self.arsiv_dir, "gelen"), exist_ok=True)
        os.makedirs(os.path.join(self.arsiv_dir, "giden"), exist_ok=True)
        
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evraklar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kod TEXT UNIQUE, tip TEXT, kategori TEXT, tarih TEXT, 
                    ad1 TEXT, ad2 TEXT, konu TEXT, plaka TEXT, bus_id TEXT, 
                    aciklama1 TEXT, aciklama2 TEXT, path TEXT, hash TEXT, kayit_zamani TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kategoriler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad TEXT UNIQUE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alan_tanimlari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alan_adi TEXT NOT NULL,
                    alan_key TEXT UNIQUE NOT NULL,
                    sira INTEGER DEFAULT 0,
                    aktif INTEGER DEFAULT 1
                )
            """)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM kategoriler")
            if cursor.fetchone()[0] == 0:
                conn.execute("INSERT INTO kategoriler (ad) VALUES ('Genel')")
            
            # Varsayılan alan tanımlarını seed et
            cursor.execute("SELECT COUNT(*) FROM alan_tanimlari")
            if cursor.fetchone()[0] == 0:
                varsayilan_alanlar = [
                    ("Ad/Ünvan 1", "ad1", 1),
                    ("Ad/Ünvan 2", "ad2", 2),
                    ("Konu", "konu", 3),
                    ("Plaka", "plaka", 4),
                    ("Bus ID", "bus_id", 5),
                    ("Açıklama 1", "aciklama1", 6),
                    ("Açıklama 2", "aciklama2", 7),
                ]
                conn.executemany(
                    "INSERT INTO alan_tanimlari (alan_adi, alan_key, sira) VALUES (?, ?, ?)",
                    varsayilan_alanlar
                )

    def secure_insert_evrak(self, data_dict, is_pdf, current_image, source_path):
        """
        Tek transaction içinde: kod üretimi + damgalama + DB kaydı.
        Hata durumunda fiziksel dosya rollback edilir.
        """
        os.makedirs(self.arsiv_dir, exist_ok=True)
        final_path = ""

        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()

                # 1. Kod Üretimi (transaction içinde race-free)
                tip = data_dict['tip']
                kat = data_dict['kategori']
                
                t_pref = "GEL" if tip.lower() == "gelen" else "GID"
                k_pref = kat[:3].upper()
                full_pref = f"{t_pref}-{k_pref}-"
                
                cursor.execute("""
                    SELECT COALESCE(MAX(CAST(SUBSTR(kod, -4) AS INTEGER)), 0) + 1 
                    FROM evraklar WHERE kod LIKE ?
                """, (f"{full_pref}%",))
                next_num = cursor.fetchone()[0]

                final_kod = f"{full_pref}{next_num:04d}"

                # 2. Dosya Hazırlığı ve Damgalama
                ext = ".pdf" if is_pdf else ".jpg"
                final_path = os.path.abspath(os.path.join(self.arsiv_dir, f"{final_kod}{ext}"))
                damga = f"SISTEM NO: {final_kod}\nKAYIT: {data_dict['kayit_zamani']}"

                success = (stamp_pdf(source_path, final_path, damga) if is_pdf 
                           else stamp_image(current_image, final_path, damga))

                if not success:
                    return False, "Dosya damgalanırken fiziksel hata oluştu."

                # 3. Hash kontrolü (mükerrer kayıt engeli)
                f_hash = get_file_hash(final_path)
                cursor.execute("SELECT kod FROM evraklar WHERE hash=?", (f_hash,))
                if cursor.fetchone():
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    return False, "Bu dosya zaten sistemde kayıtlı!"

                # 4. Veritabanına kayıt
                data_dict['kod'] = final_kod
                data_dict['path'] = final_path
                data_dict['hash'] = f_hash

                cols = ', '.join(data_dict.keys())
                placeholders = ', '.join(['?'] * len(data_dict))
                cursor.execute(
                    f"INSERT INTO evraklar ({cols}) VALUES ({placeholders})",
                    list(data_dict.values())
                )

                return True, final_kod

        except Exception as e:
            # DB hatası: diske yazılan dosyayı geri al
            if final_path and os.path.exists(final_path):
                os.remove(final_path)
            logging.error(f"DB Kayıt Hatası: {e}")
            return False, f"Kritik Sistem Hatası: {str(e)}"
        finally:
            conn.close()

    def search_evrak(self, query_text=""):
        """Açık sütun listesi ile güvenli arama (SELECT * yerine)."""
        search = f"%{query_text}%"
        query = """
            SELECT kod, tip, kategori, tarih, ad1, ad2, konu, plaka, bus_id,
                   aciklama1, aciklama2, path, hash, kayit_zamani
            FROM evraklar
            WHERE plaka LIKE ? OR kod LIKE ? OR konu LIKE ? OR ad1 LIKE ? OR bus_id LIKE ?
            ORDER BY id DESC
        """
        with self.get_connection() as conn:
            return conn.execute(query, (search, search, search, search, search)).fetchall()

    def get_kategoriler(self):
        with self.get_connection() as conn:
            rows = conn.execute("SELECT ad FROM kategoriler ORDER BY ad").fetchall()
            return [row['ad'] for row in rows]

    def add_kategori(self, ad):
        try:
            with self.get_connection() as conn:
                conn.execute("INSERT INTO kategoriler (ad) VALUES (?)", (ad,))
                return True
        except sqlite3.IntegrityError:
            return False # Zaten var
        except Exception as e:
            logging.error(f"Kategori Ekleme Hatası: {e}")
            return False

    def update_kategori(self, eski_ad, yeni_ad):
        try:
            with self.get_connection() as conn:
                conn.execute("UPDATE kategoriler SET ad=? WHERE ad=?", (yeni_ad, eski_ad))
                # İsteğe bağlı: Evraklar tablosundaki eski kategorileri de güncellemek için:
                conn.execute("UPDATE evraklar SET kategori=? WHERE kategori=?", (yeni_ad, eski_ad))
                return True
        except sqlite3.IntegrityError:
            return False # Yeni ad zaten var olabilir
        except Exception as e:
            logging.error(f"Kategori Güncelleme Hatası: {e}")
            return False

    def remove_kategori(self, ad):
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM kategoriler WHERE ad=?", (ad,))
                return True
        except Exception as e:
            logging.error(f"Kategori Silme Hatası: {e}")
            return False

    # ============ ALAN TANIMLARI YÖNETİMİ ============
    def get_alan_tanimlari(self, sadece_aktif=True):
        """Aktif alan tanımlarını sırayla getirir."""
        with self.get_connection() as conn:
            if sadece_aktif:
                rows = conn.execute(
                    "SELECT alan_adi, alan_key FROM alan_tanimlari WHERE aktif=1 ORDER BY sira"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT alan_adi, alan_key, aktif FROM alan_tanimlari ORDER BY sira"
                ).fetchall()
            return [dict(row) for row in rows]

    def add_alan(self, alan_adi):
        """Yeni alan ekler. DB sütun adı otomatik üretilir ve evraklar tablosuna eklenir."""
        try:
            # Türkçe karakterlerden arındırılmış bir key üret
            import re
            tr_map = str.maketrans("çğıöşü ÇĞİÖŞÜ", "cgiosu_CGIOSU")
            base_key = alan_adi.lower().translate(tr_map)
            base_key = re.sub(r'[^a-z0-9_]', '', base_key)
            if not base_key:
                base_key = "alan"
            alan_key = f"ozel_{base_key}"
            
            with self.get_connection() as conn:
                # Sıra numarasını al
                cursor = conn.cursor()
                cursor.execute("SELECT COALESCE(MAX(sira), 0) + 1 FROM alan_tanimlari")
                yeni_sira = cursor.fetchone()[0]
                
                conn.execute(
                    "INSERT INTO alan_tanimlari (alan_adi, alan_key, sira) VALUES (?, ?, ?)",
                    (alan_adi, alan_key, yeni_sira)
                )
                
                # evraklar tablosuna yeni sütun ekle
                try:
                    conn.execute(f"ALTER TABLE evraklar ADD COLUMN {alan_key} TEXT")
                except Exception:
                    pass  # Sütun zaten var olabilir
                
                return True, alan_key
        except sqlite3.IntegrityError:
            return False, "Bu alan zaten mevcut."
        except Exception as e:
            logging.error(f"Alan Ekleme Hatası: {e}")
            return False, str(e)

    def update_alan(self, alan_key, yeni_adi):
        """Alanın görünen adını (etiketini) günceller."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE alan_tanimlari SET alan_adi=? WHERE alan_key=?",
                    (yeni_adi, alan_key)
                )
                return True
        except Exception as e:
            logging.error(f"Alan Güncelleme Hatası: {e}")
            return False

    def remove_alan(self, alan_key):
        """Alanı pasife alır (veri kaybolmaz, sütun silinmez)."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE alan_tanimlari SET aktif=0 WHERE alan_key=?",
                    (alan_key,)
                )
                return True
        except Exception as e:
            logging.error(f"Alan Silme Hatası: {e}")
            return False

    def delete_evrak(self, kod):
        """Dosya silinemezse DB kaydı korunur (tutarlılık garantisi)."""
        conn = self.get_connection()
        try:
            with conn:
                row = conn.execute("SELECT path FROM evraklar WHERE kod=?", (kod,)).fetchone()
                if row and row['path'] and os.path.exists(row['path']):
                    try:
                        os.remove(row['path'])
                    except Exception as e:
                        logging.error(f"Dosya silinemedi ({row['path']}): {e}")
                        return False

                conn.execute("DELETE FROM evraklar WHERE kod=?", (kod,))
                return True
        except Exception as e:
            logging.error(f"Silme Hatası: {e}")
            return False
        finally:
            conn.close()
