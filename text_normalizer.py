import re
import os
import yaml
import unicodedata
from typing import List, Dict

def load_rules(config_path: str) -> Dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def apply_strip_patterns(text: str, patterns: List[str]) -> str:
    t = text
    for p in patterns:
        t = re.sub(p, "", t, flags=re.IGNORECASE | re.MULTILINE)
    return t

def apply_replacements(text: str, replacements: List[Dict[str, str]]) -> str:
    t = text
    for item in replacements:
        pat = item.get('pattern')
        rep = item.get('replace', '')
        if pat:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t

def normalize_whitespace(text: str) -> str:
    t = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", " ", text)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()

def normalize_unicode(text: str) -> str:
    """
    Unicode normalizasyonu (NFKC) uygular, tipik karışıklıkları düzeltir ve
    kontrol karakterlerini temizler. Farklı tırnak/tire karakterlerini sadeleştirir.
    """
    if not text:
        return ""
    # NFKC ile normalize et
    t = unicodedata.normalize('NFKC', text)
    # Yaygın confusable karakterleri sadeleştir
    replacements = {
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "’": "'", "‘": "'", "‚": ",",
        "–": "-", "—": "-", "−": "-",
        "•": "- ", "·": "- ", "●": "- ", "*": "*",
        " ": " ",  # no-break space
    }
    for k, v in replacements.items():
        t = t.replace(k, v)

    # Kontrol karakterlerini sil
    t = "".join(ch for ch in t if unicodedata.category(ch)[0] != 'C')

    # Türkçe olmayan beklenmedik ideografik karakterleri (örn. Çince 的) temizle
    t = re.sub(r"[\u4E00-\u9FFF]", "", t)
    return t

def normalize_bullets(text: str) -> str:
    """
    Bozuk madde işaretlerini standart "- " biçimine çevirir ve aynı madde
    içinde satır kırılmalarını birleştirir.
    """
    if not text:
        return ""
    # Gövde içinde geçen "Şartlar:" etiketini kaldır (başlık olarak yeniden oluşturulacak)
    text = re.sub(r"(?mi)(?<!^)\bŞartlar:\s*", "", text, flags=re.IGNORECASE)

    # Başlıklardan sonra aynı satırda başlayan maddeleri aşağı satıra indir
    for head in ("Şartlar:", "İstisnalar:", "Adımlar:"):
        text = re.sub(rf"{head}\s*-\s+", head + "\n- ", text)
        # Başlık bloğu sonuna kadar, satır içinde bitişik maddeleri alt satıra böl
        def _split_inline_bullets(block: str) -> str:
            return re.sub(r"(?<!\n)\s*-\s*(?=\S)", "\n- ", block)
        text = re.sub(rf"({head}[\s\S]*?)(?=\n\n|$)", lambda m: _split_inline_bullets(m.group(1)), text)

    lines = text.splitlines()
    normalized: List[str] = []
    current_bullet = None
    for ln in lines:
        # Aynı satırda birden fazla madde varsa satır içi madde ayrıştırma
        if ln.count("- ") >= 2 or re.search(r"\S-\s*\S", ln):
            ln = re.sub(r"\s*-\s*(?=\S)", "\n- ", ln)

        # Başta gelen çeşitli madde işaretlerini normalize et
        m = re.match(r"^\s*([\-\*•])\s*(.*)$", ln)
        if m:
            # Yeni bir madde başlıyor
            if current_bullet is not None:
                normalized.append(current_bullet.strip())
            content = m.group(2).strip()
            # Yıldızla başlayan kalın/italic işaretlerini temizle
            content = re.sub(r"^\*+\s*", "", content)
            current_bullet = f"- {content}"
        else:
            # Mevcut maddenin devamıysa ekle, değilse normal satır
            if current_bullet is not None and ln.strip():
                tail = ln.strip()
                # Ortadaki çıplak yıldızları temizle
                tail = re.sub(r"^\*+\s*", "", tail)
                current_bullet += f" {tail}"
            else:
                if current_bullet is not None:
                    normalized.append(current_bullet.strip())
                    current_bullet = None
                if ln.strip():
                    normalized.append(ln.strip())
    if current_bullet is not None:
        normalized.append(current_bullet.strip())
    out = "\n".join(normalized)
    # Çift boşlukları sadeleştir
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"\s*\n\s*", "\n", out).strip()
    return out

def normalize_text_pipeline(text: str, config_path: str) -> str:
    if not text:
        return ""
    rules = load_rules(config_path)
    t = normalize_unicode(text)
    t = apply_strip_patterns(t, rules.get('strip_patterns', []))
    t = apply_replacements(t, rules.get('replacements', []))
    t = normalize_bullets(t)
    t = normalize_whitespace(t)
    return t


