import os, hashlib, logging
from PIL import Image, ImageDraw, ImageFont
import fitz

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def stamp_pdf(source_path, target_path, text):
    """
    HATA DÜZELTİLDİ: Tab/space karışıklığı giderildi (IndentationError).
    Dinamik x koordinatı ile dar sayfalarda taşma önlendi.
    """
    try:
        doc = fitz.open(source_path)
        page = doc[0]
        fontsize = 9
        # fitz.get_text_length ile metin genişliğini ölç, sağdan pay bırak
        text_width = fitz.get_text_length(text, fontsize=fontsize)
        x_coord = max(10, page.rect.width - text_width - 30)
        page.insert_text((x_coord, 50), text, fontsize=fontsize, color=(1, 0, 0))
        doc.save(target_path)
        doc.close()
        return True
    except Exception as e:
        logging.error(f"PDF Stamp Hatası: {e}")
        return False

def stamp_image(image_obj, target_path, text):
    """Küçük resimlerde dinamik x koordinatı ile güvenli damga."""
    try:
        temp_img = image_obj.copy()
        draw = ImageDraw.Draw(temp_img)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max(10, temp_img.width - tw - 40)
        draw.text((x, 50), text, fill=(255, 0, 0), font=font)

        temp_img.save(target_path, quality=95)
        return True
    except Exception as e:
        logging.error(f"Resim Stamp Hatası: {e}")
        return False
