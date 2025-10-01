import json
import sys
import time
import uuid
from typing import List, Dict, Any
from urllib.parse import urlparse
import unicodedata

import requests


def load_tests(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Test dosyası bir liste olmalı")
    return data


def ensure_session_id(given: str | None) -> str:
    return given or str(uuid.uuid4())


def post_ask(base_url: str, question: str, session_id: str) -> Dict[str, Any]:
    payload = {
        "question": question,
        "model": "groq",
        "session_id": session_id,
    }
    t0 = time.time()
    r = requests.post(f"{base_url}/ask", json=payload, timeout=60)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json()
    # Güvenlik: response_time olmayabilir, biz ölçülen süreyi de ekleyelim
    data.setdefault("_measured_time", dt)
    return data


def score_one(result: Dict[str, Any], expected_keywords: List[str], expected_urls: List[str]) -> Dict[str, Any]:
    text = (result.get("answer") or "").lower()
    urls = [u.get("url", "") for u in result.get("source_links", [])]

    # Anahtar kelime kapsama
    hit_keywords = [k for k in expected_keywords if k.lower() in text]
    keyword_recall = len(hit_keywords) / max(1, len(expected_keywords))

    # URL isabeti (gevşetilmiş): domain + slug içerimi + diacritics-insensitive
    def norm_slug(s: str) -> str:
        s = s.strip().lower()
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch)[0] != 'M')
        return s.replace('_', '-').strip('-')

    def domain_and_slug(u: str) -> tuple[str, str]:
        try:
            p = urlparse(u)
            domain = (p.netloc or '').lower().replace('www.', '')
            parts = [seg for seg in (p.path or '').split('/') if seg]
            slug = norm_slug(parts[-1]) if parts else ''
            return domain, slug
        except Exception:
            return '', ''

    norm_urls = [(su, *domain_and_slug(su)) for su in urls if su]

    def relaxed_match(expected: str) -> bool:
        ed, es = domain_and_slug(expected)
        for raw, d, s in norm_urls:
            # Tam eşleşme (en güçlü)
            if expected in raw:
                return True
            # Domain eşleşmesi + slug kısmi eşleşmesi (geliştirilmiş)
            if ed and d and ed == d:
                if not es:  # Beklenen URL'de slug yoksa domain eşleşmesi yeterli
                    return True
                if es and s:  # Her iki tarafta da slug varsa
                    # Slug'ların ortak kısımlarını kontrol et
                    es_parts = es.split('-')
                    s_parts = s.split('-')
                    common_parts = set(es_parts) & set(s_parts)
                    if len(common_parts) >= 2:  # En az 2 ortak parça
                        return True
                    if es in s or s in es:  # Orijinal kontrol
                        return True
            # Sadece slug eşleşmesi (domain yoksa) – geliştirilmiş
            if es and s:
                # Slug'ların ortak kısımlarını kontrol et
                es_parts = es.split('-')
                s_parts = s.split('-')
                common_parts = set(es_parts) & set(s_parts)
                if len(common_parts) >= 2:  # En az 2 ortak parça
                    return True
                if es in s or s in es:  # Orijinal kontrol
                    return True
        return False

    hit_urls = [u for u in expected_urls if relaxed_match(u)]
    url_hit = len(hit_urls) / max(1, len(expected_urls))

    return {
        "keyword_recall": keyword_recall,
        "url_hit": url_hit,
        "hit_keywords": hit_keywords,
        "hit_urls": hit_urls,
    }


def run_suite(tests_path: str, base_url: str = "http://localhost:8000") -> None:
    tests = load_tests(tests_path)
    summary: Dict[str, Any] = {
        "count": 0,
        "avg_time_s": 0.0,
        "avg_keyword_recall": 0.0,
        "avg_url_hit": 0.0,
        "special_type_counts": {},
        "failures": []
    }

    times: List[float] = []
    recalls: List[float] = []
    hits: List[float] = []

    for idx, t in enumerate(tests, start=1):
        question = t.get("question", "").strip()
        if not question:
            continue
        session_id = ensure_session_id(t.get("session_id"))
        expected_keywords = t.get("expected_keywords", [])
        expected_urls = t.get("expected_urls", [])
        followups = t.get("followups", [])

        try:
            result = post_ask(base_url, question, session_id)

            # Takip soruları varsa aynı oturumda gönder
            for fu in followups:
                result = post_ask(base_url, fu, session_id)

            s = score_one(result, expected_keywords, expected_urls)

            times.append(float(result.get("_measured_time", 0.0)))
            recalls.append(s["keyword_recall"])
            hits.append(s["url_hit"])

            st = result.get("special_type") or "none"
            summary["special_type_counts"][st] = summary["special_type_counts"].get(st, 0) + 1

            summary["count"] += 1
            print(f"[{idx}] OK - time={result.get('_measured_time', 0.0):.2f}s kw_recall={s['keyword_recall']:.2f} url_hit={s['url_hit']:.2f}")
        except Exception as e:
            summary["failures"].append({"index": idx, "question": question, "error": str(e)})
            print(f"[{idx}] FAIL - {e}")

    if summary["count"]:
        summary["avg_time_s"] = sum(times) / len(times)
        summary["avg_keyword_recall"] = sum(recalls) / len(recalls)
        summary["avg_url_hit"] = sum(hits) / len(hits)

    print("\n=== SONUÇ ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tests/test_set.json"
    run_suite(path)


