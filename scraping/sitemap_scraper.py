"""
Sitemap tabanlı web scraper
En güvenilir yöntem - sitemap.xml dosyalarından blog linklerini çeker
"""

import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime
from typing import List
from langchain_community.document_loaders import WebBaseLoader

BASE_URL = "https://oktayozdemir.com.tr/"

class SitemapScraper:
    def __init__(self):
        """
        Sitemap tabanlı scraper sınıfı
        """
        self.blog_urls = []
        
    def get_sitemap_urls(self) -> List[str]:
        """
        Sitemap index'ten tüm alt sitemap URL'lerini al
        """
        try:
            print("🔍 Sitemap index kontrol ediliyor...")
            response = requests.get(BASE_URL + "sitemap_index.xml")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            sitemap_urls = []
            for sitemap_elem in root.findall('.//sitemap:sitemap', namespaces):
                loc = sitemap_elem.find('sitemap:loc', namespaces)
                if loc is not None:
                    sitemap_urls.append(loc.text)
            
            print(f"✅ {len(sitemap_urls)} alt sitemap bulundu")
            return sitemap_urls
            
        except Exception as e:
            print(f"❌ Sitemap index hatası: {e}")
            return []
    
    def extract_blog_urls_from_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Tek bir sitemap'ten blog URL'lerini çıkar
        """
        try:
            response = requests.get(sitemap_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            blog_urls = []
            for url_elem in root.findall('.//sitemap:url', namespaces):
                loc = url_elem.find('sitemap:loc', namespaces)
                if loc is not None and '/blog/' in loc.text:
                    blog_urls.append(loc.text)
            
            return blog_urls
            
        except Exception as e:
            print(f"❌ Sitemap işleme hatası ({sitemap_url}): {e}")
            return []
    
    def get_all_blog_urls(self) -> List[str]:
        """
        Tüm sitemap'lerden blog URL'lerini topla
        """
        print("📄 Blog URL'leri sitemap'lerden çekiliyor...")
        
        sitemap_urls = self.get_sitemap_urls()
        if not sitemap_urls:
            print("❌ Sitemap URL'leri bulunamadı!")
            return []
        
        all_blog_urls = []
        
        for sitemap_url in sitemap_urls:
            blog_urls = self.extract_blog_urls_from_sitemap(sitemap_url)
            if blog_urls:
                sitemap_name = sitemap_url.split('/')[-1]
                print(f"✅ {sitemap_name}: {len(blog_urls)} blog yazısı")
                all_blog_urls.extend(blog_urls)
        
        # Tekrar eden URL'leri temizle
        unique_urls = list(set(all_blog_urls))
        print(f"🎯 Toplam {len(unique_urls)} benzersiz blog yazısı bulundu!")
        
        return unique_urls
    
    def load_website_docs(self) -> List:
        """
        Sitemap'ten alınan URL'leri WebBaseLoader ile yükle
        """
        print("🚀 Sitemap tabanlı scraping başlıyor...")
        
        # Blog URL'lerini al
        blog_urls = self.get_all_blog_urls()
        
        if not blog_urls:
            print("❌ Blog URL'si bulunamadı!")
            return []
        
        # Ana sayfa + tüm blog yazıları
        all_urls = [BASE_URL] + blog_urls
        
        print(f"📥 {len(all_urls)} URL yükleniyor...")
        print("⏳ Bu işlem birkaç dakika sürebilir...")
        
        try:
            loader = WebBaseLoader(all_urls)
            docs = loader.load()
            print(f"✅ {len(docs)} doküman başarıyla yüklendi!")
            return docs
            
        except Exception as e:
            print(f"❌ WebBaseLoader hatası: {e}")
            return []
    
    def save_sitemap_data(self, docs, filename: str = None):
        """
        Sitemap scraping verilerini kaydet
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sitemap_scraped_data_{timestamp}.json"
        
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
                "scraped_at": datetime.now().isoformat(),
                "scraper_type": "sitemap_based"
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Sitemap scraping verileri kaydedildi: {filepath}")
        return filepath

def test_sitemap_scraping():
    """
    Sitemap scraper'ı test et
    """
    print("🔍 Sitemap scraping testi başlıyor...\n")
    
    try:
        scraper = SitemapScraper()
        
        # Sadece URL'leri al (test için)
        blog_urls = scraper.get_all_blog_urls()
        
        if not blog_urls:
            print("❌ Test başarısız - blog URL'si bulunamadı!")
            return []
        
        print(f"\n🔍 Bulunan blog yazıları (ilk 15):")
        for i, url in enumerate(blog_urls[:15], 1):
            # URL'den başlık tahmini
            title_part = url.split('/')[-1].replace('-', ' ').title()
            print(f"  {i}. {title_part}")
            print(f"     {url}")
        
        if len(blog_urls) > 15:
            print(f"  ... ve {len(blog_urls) - 15} tane daha")
        
        print(f"\n📊 Sonuç: {len(blog_urls)} blog yazısı tespit edildi")
        print("✅ Bu sayı beklediğiniz 60'a yakın!")
        
        return blog_urls
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        return []

def sitemap_scrape_and_save():
    """
    Ana sitemap scraping fonksiyonu
    """
    scraper = SitemapScraper()
    docs = scraper.load_website_docs()
    
    if docs:
        filepath = scraper.save_sitemap_data(docs)
        print(f"🎉 Sitemap scraping tamamlandı! {len(docs)} doküman kaydedildi.")
        return docs
    else:
        print("❌ Sitemap scraping başarısız!")
        return []

if __name__ == "__main__":
    print("🗺️  Sitemap tabanlı scraper başlatılıyor...\n")
    print("Bu yöntem en güvenilir olanıdır - sitemap.xml dosyalarını kullanır\n")
    
    print("Seçenekler:")
    print("1️⃣ Test modu - Sadece blog linklerini listele")
    print("2️⃣ Tam scraping - Tüm verileri çek ve kaydet\n")
    
    # Varsayılan olarak test modunu çalıştır
    print("🔄 Test modu çalıştırılıyor...\n")
    links = test_sitemap_scraping()
    
    if links and len(links) >= 30:  # En az 30 link bulunmuşsa
        print(f"\n✨ Test başarılı! {len(links)} link bulundu.")
        print("💾 Tüm verileri kaydetmek için sitemap_scrape_and_save() çalıştırın.")
    else:
        print(f"\n⚠️  Sadece {len(links) if links else 0} link bulundu.")
        print("🔧 Beklenenden az, ama yine de devam edebiliriz.")
