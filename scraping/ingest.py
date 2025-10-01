"""
Birleşik ingest komutu

Kullanım örnekleri:
  - Tüm akış (temiz scraping + vectorstore'u baştan kur):
      python3 ingest.py --mode clean --rebuild

  - Yalnızca incremental ekleme (mevcut FAISS'e yeni temiz JSON'u ekle):
      python3 ingest.py --mode clean --incremental

  - Belirli bir temiz JSON dosyasını incremental ekle:
      python3 ingest.py --json data/raw/clean_blog_data_20250101_120000.json --incremental

Notlar:
  - Varsayılan kök: bu dosyanın bulunduğu proje dizini
  - Embedding modeli, mevcut yapıyla uyumlu: paraphrase-multilingual-MiniLM-L12-v2
"""

import argparse
import glob
import os
import sys
from typing import Optional

# Proje kökünü PYTHONPATH'e ekle (bu dosya artık scraping/ altında)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scraping.clean_content_scraper import (
    clean_scrape_and_save,
    clean_scrape_category_and_save,
    clean_scrape_list_and_save,
)  # type: ignore
from scraping.sitemap_scraper import sitemap_scrape_and_save  # type: ignore
from vectorstore.build_store import OptimizedVectorStoreBuilder, build_full_vectorstore  # type: ignore


def find_latest_clean_json(root: str) -> Optional[str]:
    raw_dir = os.path.join(root, "data", "raw")
    if not os.path.exists(raw_dir):
        return None
    files = sorted(glob.glob(os.path.join(raw_dir, "clean_blog_data_*.json")))
    return files[-1] if files else None


def run_clean_scrape(root: str) -> Optional[str]:
    """Temiz scraping çalıştırır ve oluşturulan dosya yolunu döner."""
    blogs = clean_scrape_and_save()
    if blogs is None:
        return None
    return find_latest_clean_json(root)


def run_sitemap_scrape(root: str) -> Optional[str]:
    """Sitemap scraping çalıştırır (ham veri üretir). Bu veri doğrudan builder ile uyumlu değildir."""
    docs = sitemap_scrape_and_save()
    if not docs:
        return None
    # Kullanıcıya temiz scraper'ı önermeye devam ediyoruz, ama yine de en güncel clean dosyayı döndürmeye çalışalım
    return find_latest_clean_json(root)

def run_list_scrape(root: str, list_url: str, base_url: Optional[str], max_pages: Optional[int]) -> Optional[str]:
    """Liste URL üzerinden scraping çalıştır ve oluşan temiz JSON yolunu döndür."""
    blogs = clean_scrape_list_and_save(list_url, base_url=base_url, max_pages=max_pages)
    if not blogs:
        return None
    return find_latest_clean_json(root)


def incremental_ingest(root: str, json_path: str) -> None:
    builder = OptimizedVectorStoreBuilder()

    # 1) Mevcut FAISS'i yükle (yoksa oluşturacağız)
    vs_path = os.path.join(root, "data", "vectorstore")
    vectorstore = builder.load_vectorstore(vs_path)

    # Eğer yoksa yeni oluşturmak için boş bir kurulum yapalım
    if vectorstore is None:
        # İlk kurulum: json'dan doğrudan process ederek oluştur
        print("⚠️ Mevcut FAISS bulunamadı. İlk kez oluşturulacak.")
        vectorstore = builder.process_clean_json_to_vectorstore(json_path)
        return

    # 2) Yeni veriyi yükle, chunk'la ve ekle
    documents = builder.load_clean_json_data(json_path)
    if not documents:
        print("❌ JSON verisi yüklenemedi veya boş")
        return

    split_docs = builder.split_documents(documents)
    vectorstore.add_documents(split_docs)

    # 3) Kaydet
    vectorstore.save_local(vs_path)
    print("✅ Incremental ingest tamamlandı ve mevcut FAISS kaydedildi.")


def main():
    parser = argparse.ArgumentParser(description="Birleşik ingest aracı")
    parser.add_argument("--mode", choices=["clean", "sitemap"], default="clean",
                        help="Veri çekme modu: clean (önerilen) veya sitemap")
    parser.add_argument("--rebuild", action="store_true", help="Vectorstore'u baştan kur")
    parser.add_argument("--incremental", action="store_true", help="Mevcut FAISS'e ekleme yap")
    parser.add_argument("--json", type=str, default=None, help="Belirli bir temiz JSON dosyası yolu")
    parser.add_argument("--category", type=str, default=None, help="Kategori URL'si (örn: https://oktayozdemir.com.tr/category/almanya-goc-ve-yasam/)")
    parser.add_argument("--review", action="store_true", help="İşlenecek veriyi FAISS'e eklemeden önce özet ve önizleme göster, onay iste")
    parser.add_argument("--show-full", action="store_true", help="Önizlemede içeriklerin tamamını göster (uzun olabilir)")
    parser.add_argument("--base-url", type=str, default=None, help="Scraper taban URL (örn: https://alternativkraft.com/)")
    parser.add_argument("--list-url", type=str, default=None, help="Blog liste URL'si (örn: https://alternativkraft.com/tr/blog-2/)")
    parser.add_argument("--scrape-only", action="store_true", help="Sadece scraping yap ve JSON'u üret, vectorstore işlemi yapma")
    parser.add_argument("--max-pages", type=int, default=None, help="Liste sayfası için maksimum sayfa sayısı")
    parser.add_argument("--per-article", action="store_true", help="İnceleme modunda her makale için tek tek onay iste")

    args = parser.parse_args()
    root = PROJECT_ROOT

    # 1) JSON kaynağını hazırla
    json_path: Optional[str] = args.json
    if json_path is None:
        if args.list_url:
            print(f"📚 Liste scraping: {args.list_url}")
            json_path = run_list_scrape(root, args.list_url, base_url=args.base_url, max_pages=args.max_pages)
        elif args.category:
            print(f"📚 Kategori scraping: {args.category}")
            blogs = clean_scrape_category_and_save(args.category, base_url=args.base_url)
            json_path = find_latest_clean_json(root)
        elif args.mode == "clean":
            # base_url desteği ile çalıştır
            blogs = clean_scrape_and_save(base_url=args.base_url)
            json_path = find_latest_clean_json(root)
        else:
            json_path = run_sitemap_scrape(root)

    if not json_path or not os.path.exists(json_path):
        print("❌ Temiz JSON dosyası bulunamadı. --json ile yol verebilir veya --mode clean kullanabilirsiniz.")
        sys.exit(1)

    print(f"📄 Kullanılacak JSON: {os.path.relpath(json_path, root)}")

    if args.scrape_only:
        print("⏹️  --scrape-only seçildi. Sadece scraping yapıldı, vectorstore işlemi yapılmayacak.")
        return

    # 1.5) İnceleme modu: Kullanıcı onayı almadan FAISS'e ekleme
    if args.review:
        try:
            import json as _json
            from textwrap import fill as _fill
            with open(json_path, 'r', encoding='utf-8') as f:
                data = _json.load(f)
        except Exception as e:
            print(f"❌ JSON okunamadı: {e}")
            sys.exit(1)

        n = len(data) if isinstance(data, list) else 0
        total_words = sum(int(x.get('word_count', 0) or 0) for x in data) if n else 0
        print("\n=== İNCELEME ÖZETİ ===")
        print(f"Toplam kayıt: {n}")
        print(f"Toplam kelime: {total_words:,}")

        if not args.per_article:
            preview_limit = n if args.show_full else min(10, n)
            if n:
                print("\n--- ÖNİZLEME ---")
                for i, x in enumerate(data[:preview_limit], 1):
                    title = x.get('title', '')
                    url = x.get('url', '')
                    content = x.get('content', '') or ''
                    snippet = content if args.show_full else content[:600]
                    snippet = snippet.replace('\n', ' ')
                    print(f"\n[{i}] {title}\nURL: {url}")
                    print(_fill(snippet, width=100))
                if not args.show_full and n > preview_limit:
                    print(f"\n(Toplam {n} kayıttan ilk {preview_limit} gösterildi. Tamamı için --show-full ekleyin.)")

            try:
                decision = input("\nBu verileri FAISS'e eklemek istiyor musunuz? [y/N]: ").strip().lower()
            except EOFError:
                decision = 'n'
            if decision not in ('y', 'yes'):
                print("⏹️  İşlem iptal edildi (FAISS'e ekleme yapılmadı).")
                return
        else:
            # Per-article review: kullanıcı her makale için onay verir
            print("\n--- PER-ARTİCLE İNCELEME ---")
            approved: list[dict] = []
            for idx, x in enumerate(data, 1):
                title = x.get('title', '')
                url = x.get('url', '')
                content = x.get('content', '') or ''
                snippet = content if args.show_full else content[:600]
                snippet = snippet.replace('\n', ' ')
                print(f"\n[{idx}/{n}] {title}\nURL: {url}")
                print(_fill(snippet, width=100))
                try:
                    decision = input("Ekle? [y/N]: ").strip().lower()
                except EOFError:
                    decision = 'n'
                if decision in ('y', 'yes'):
                    approved.append(x)
            if not approved:
                print("⏹️  Hiç bir makale onaylanmadı. İşlem durduruldu.")
                return
            # Onaylananları yeni geçici JSON'a yaz
            import tempfile, json as _json
            fd, tmp_path = tempfile.mkstemp(prefix="approved_", suffix=".json")
            os.close(fd)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                _json.dump(approved, f, ensure_ascii=False, indent=2)
            print(f"✅ Onaylanan {len(approved)} makale geçici dosyaya yazıldı: {tmp_path}")
            json_path = tmp_path

    # 2) Vectorstore işlemi
    if args.rebuild:
        print("🚀 Rebuild modu: vectorstore baştan oluşturuluyor...")
        builder = OptimizedVectorStoreBuilder()
        builder.process_clean_json_to_vectorstore(json_path)
        print("✅ Rebuild tamamlandı.")
        return

    if args.incremental:
        print("➕ Incremental ingest başlıyor...")
        incremental_ingest(root, json_path)
        return

    # Varsayılan davranış: rebuild
    print("ℹ️  Ne --rebuild ne de --incremental seçildi. Varsayılan olarak rebuild yapılıyor...")
    builder = OptimizedVectorStoreBuilder()
    builder.process_clean_json_to_vectorstore(json_path)
    print("✅ Tam işlem tamamlandı.")


if __name__ == "__main__":
    main()


