"""
Web scraping modülü - WebBaseLoader ve BeautifulSoup kullanarak
oktayozdemir.com.tr sitesinden veri çekme
"""

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader
import json
import os
from datetime import datetime
from typing import List, Dict

BASE_URL = "https://oktayozdemir.com.tr/"

def get_blog_links() -> List[str]:
    """
    Blog sayfasından tüm blog yazısı linklerini çeker
    Sayfalandırma (pagination) desteği ile
    """
    try:
        all_links = []
        page = 1
        
        while True:
            # Blog sayfası veya sayfalandırma
            if page == 1:
                url = BASE_URL + "blog/"
            else:
                url = f"{BASE_URL}blog/page/{page}/"
            
            print(f"📄 Sayfa {page} kontrol ediliyor: {url}")
            response = requests.get(url)
            
            # Sayfa bulunamadıysa dur
            if response.status_code == 404:
                print(f"❌ Sayfa {page} bulunamadı, tarama tamamlandı.")
                break
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Bu sayfadaki blog linklerini bul
            page_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Daha spesifik filtreleme
                if "/blog/" in href and href not in ["/blog/", "/category/blog/"]:
                    full_url = href if href.startswith("http") else BASE_URL + href.lstrip('/')
                    if full_url not in all_links and full_url not in page_links:
                        page_links.append(full_url)
            
            print(f"✅ Sayfa {page}'da {len(page_links)} yeni link bulundu")
            
            # Bu sayfada yeni link yoksa dur
            if not page_links:
                print(f"🔄 Sayfa {page}'da yeni link bulunamadı, tarama tamamlandı.")
                break
                
            all_links.extend(page_links)
            
            # Debug: İlk birkaç linki göster
            if page == 1 and page_links:
                print("🔍 Bulunan linkler örneği:")
                for i, link in enumerate(page_links[:3]):
                    print(f"  {i+1}. {link}")
            
            page += 1
            
            # Güvenlik: Çok fazla sayfa kontrolü
            if page > 20:  # Maximum 20 sayfa
                print("⚠️  Maksimum sayfa sayısına ulaşıldı.")
                break
        
        print(f"🎯 Toplam {len(all_links)} blog linki bulundu")
        return all_links
    
    except requests.RequestException as e:
        print(f"❌ Blog linkleri çekilirken hata oluştu: {e}")
        return []

def load_website_docs():
    """
    WebBaseLoader kullanarak ana sayfa ve blog yazılarını yükler
    """
    try:
        urls = [BASE_URL] + get_blog_links()
        print(f"Toplam {len(urls)} URL yükleniyor...")
        
        loader = WebBaseLoader(urls)
        docs = loader.load()
        
        print(f"Toplam {len(docs)} doküman yüklendi")
        return docs
    
    except Exception as e:
        print(f"Dokümanlar yüklenirken hata oluştu: {e}")
        return []

def save_raw_data(docs, filename: str = None):
    """
    Çekilen ham verileri JSON formatında kaydeder
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraped_data_{timestamp}.json"
    
    # data/raw klasörünü oluştur
    raw_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(raw_data_dir, exist_ok=True)
    
    filepath = os.path.join(raw_data_dir, filename)
    
    # Dokümanları JSON formatına dönüştür
    data_to_save = []
    for doc in docs:
        data_to_save.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "scraped_at": datetime.now().isoformat()
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    
    print(f"Ham veriler kaydedildi: {filepath}")
    return filepath

def scrape_and_save():
    """
    Ana scraping fonksiyonu - verileri çeker ve kaydeder
    """
    print("Web scraping başlıyor...")
    docs = load_website_docs()
    
    if docs:
        filepath = save_raw_data(docs)
        print(f"Scraping tamamlandı! {len(docs)} doküman {filepath} dosyasına kaydedildi.")
        return docs
    else:
        print("Scraping başarısız oldu!")
        return []

def test_scraping():
    """
    Scraping'i test etmek için basit önizleme fonksiyonu
    """
    print("🔍 Scraping testi başlıyor...\n")
    
    try:
        docs = load_website_docs()
        print(f"✅ Toplam {len(docs)} sayfa bulundu.\n")

        for i, doc in enumerate(docs[:5]):  # ilk 5 sayfayı gösterelim
            print(f"📄 ({i+1}) Kaynak URL: {doc.metadata.get('source', 'Bilinmiyor')}")
            
            # İçerik önizleme - Türkçe karakterlere dikkat
            content_preview = doc.page_content[:300].replace('\n', ' ').strip()
            print(f"📝 İçerik önizleme: {content_preview}...")
            
            # Metadata bilgileri
            if 'title' in doc.metadata:
                print(f"📋 Başlık: {doc.metadata['title']}")
            
            print("-" * 80)
            
        return docs
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        return []

if __name__ == "__main__":
    # Önce test yap
    print("🚀 Scraping modülü çalıştırılıyor...\n")
    print("1️⃣ Test modu için test_scraping() çalıştırın")
    print("2️⃣ Tam scraping için scrape_and_save() çalıştırın\n")
    
    # Test modunu çalıştır
    docs = test_scraping()
    
    if docs:
        print(f"\n✨ Test başarılı! {len(docs)} doküman bulundu.")
        print("💾 Verileri kaydetmek için scrape_and_save() fonksiyonunu çalıştırın.")
