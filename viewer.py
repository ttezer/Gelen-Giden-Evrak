import io, fitz, pytesseract, logging
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter
from PIL import Image, ImageOps, ImageEnhance

# Loglama ayarları main.py ile senkronize çalışır
logger = logging.getLogger(__name__)

class DocumentViewer(QGraphicsView):
    request_menu = Signal(str, QPointF)
    page_changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pdf_doc = None
        self.current_image = None
        self.current_page_idx = 0
        self.total_pages = 0
        self.selection_rect = None
        self.start_pos = None
        self.current_file_path = None
        
        # Görünüm Ayarları
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def load_file(self, path):
        try:
            self.clear_view()
            self.current_file_path = path
            if path.lower().endswith(".pdf"):
                self.pdf_doc = fitz.open(path)
                self.total_pages = len(self.pdf_doc)
                self.current_page_idx = 0
                self.render_pdf_page()
            else:
                self.current_image = Image.open(path)
                self.current_image = ImageOps.exif_transpose(self.current_image)
                self.total_pages = 1
                self.update_view()
            self.page_changed.emit(self.current_page_idx + 1, self.total_pages)
            self.reset_zoom()
        except Exception as e:
            logging.error(f"Dosya Yükleme Hatası ({path}): {e}")

    def render_pdf_page(self):
        if self.pdf_doc:
            try:
                page = self.pdf_doc[self.current_page_idx]
                pix = page.get_pixmap(dpi=300)
                self.current_image = Image.open(io.BytesIO(pix.tobytes("png")))
                self.update_view()
            except Exception as e:
                logging.error(f"PDF Render Hatası: {e}")

    def update_view(self):
        if self.current_image:
            buf = io.BytesIO()
            self.current_image.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())
            self.scene.clear()
            self.scene.addPixmap(pix)
            self.setSceneRect(QRectF(pix.rect()))

    def zoom_in(self): self.scale(1.2, 1.2)
    def zoom_out(self): self.scale(0.8, 0.8)
    
    def reset_zoom(self):
        self.resetTransform()
        if self.current_image:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def rotate_img(self, angle):
        if self.current_image:
            self.current_image = self.current_image.rotate(angle, expand=True)
            self.update_view()
            # Döndürülmüş görüntüyü geçici dosyaya kaydet (PDF dahil)
            import tempfile, os
            ext = ".jpg"
            if self.current_file_path and self.current_file_path.lower().endswith(".pdf"):
                ext = ".png"
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            tmp.close()
            try:
                self.current_image.save(tmp.name, quality=95)
                self.current_file_path = tmp.name
            except Exception as e:
                logging.error(f"Döndürme Geçici Kayıt Hatası: {e}")

    def next_page(self):
        if self.pdf_doc and self.current_page_idx < self.total_pages - 1:
            self.current_page_idx += 1
            self.render_pdf_page()
            self.page_changed.emit(self.current_page_idx + 1, self.total_pages)

    def prev_page(self):
        if self.pdf_doc and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.render_pdf_page()
            self.page_changed.emit(self.current_page_idx + 1, self.total_pages)

    def clear_view(self):
        self.scene.clear()
        self.current_image = None
        if self.pdf_doc:
            try:
                self.pdf_doc.close()
            except Exception as e:
                logging.error(f"PDF Kapatma Hatası: {e}")
        self.pdf_doc = None
        self.current_file_path = None
        self.resetTransform()
        self.setSceneRect(0, 0, 0, 0)
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            f = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale(f, f)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = self.mapToScene(event.position().toPoint())
            if self.selection_rect: self.scene.removeItem(self.selection_rect)
            self.selection_rect = QGraphicsRectItem()
            self.selection_rect.setPen(QPen(QColor(255, 0, 0), 2))
            self.scene.addItem(self.selection_rect)
        elif event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos and self.selection_rect:
            rect = QRectF(self.start_pos, self.mapToScene(event.position().toPoint())).normalized()
            self.selection_rect.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selection_rect:
            r = self.selection_rect.rect()
            if r.width() > 5:
                try:
                    crop = self.current_image.crop((int(r.left()), int(r.top()), int(r.right()), int(r.bottom())))
                    
                    # HİBRİT OCR STRATEJİSİ: PDF -> Tesseract, Fotoğraf -> EasyOCR
                    is_pdf = self.current_file_path and self.current_file_path.lower().endswith(".pdf")
                    
                    if is_pdf:
                        # PDF için hafif ve hızlı Tesseract
                        crop = ImageOps.grayscale(crop)
                        crop = ImageEnhance.Contrast(crop).enhance(2.0)
                        crop = crop.resize((crop.width*2, crop.height*2), Image.Resampling.LANCZOS)
                        text = pytesseract.image_to_string(crop, lang='tur').strip()
                    else:
                        # Fotoğraflar için derin öğrenme tabanlı EasyOCR
                        try:
                            import easyocr
                            import numpy as np
                            import torch
                            import warnings
                            
                            # Torch ve Dataloader uyarılarını temizle
                            warnings.filterwarnings("ignore", category=UserWarning)
                            
                            # CPU Performans Optimizasyonu
                            if torch.get_num_threads() > 4:
                                torch.set_num_threads(4) # Aşırı threading yükünü engelle
                            
                            # Reader'ı sadece ilk ihtiyaçta yükle (bellek tasarrufu)
                            if not hasattr(self, 'easy_reader') or self.easy_reader is None:
                                self.easy_reader = easyocr.Reader(['tr'], gpu=False, verbose=False) 
                            
                            # PIL görüntüsünü numpy dizisine çevir (EasyOCR formatı)
                            img_np = np.array(crop)
                            
                            # Okuma işlemi (Hız için worker sayısını kısıtlayabiliriz)
                            results = self.easy_reader.readtext(img_np, detail=0, paragraph=True)
                            text = " ".join(results).strip()
                        except ImportError:
                            text = "[Hata: EasyOCR kütüphanesi eksik!]"
                        except Exception as e:
                            logging.error(f"EasyOCR Hatası: {e}")
                            text = "[Okuma Hatası]"

                    self.request_menu.emit(text, event.globalPosition())
                except Exception as e:
                    logging.error(f"OCR İşleme Hatası: {e}")
            
            if self.selection_rect in self.scene.items():
                self.scene.removeItem(self.selection_rect)
            self.selection_rect = None
            self.start_pos = None
            
        self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)