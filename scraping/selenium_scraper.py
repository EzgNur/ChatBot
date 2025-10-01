"""
Selenium tabanlı gelişmiş web scraper
Dinamik içerik ve AJAX yüklenen blog yazılarını çeker
"""

import time
import json
import os
from datetime import datetime
from typing import List, Set
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader

BASE_URL = "https://oktayozdemir.com.tr/"

class AdvancedScraper:
    def __init__(self, headless=True):
        """
        Gelişmiş scraper sınıfı
        """
        self.headless = headless
        self.driver = None
        self.blog_links = set()
        
    def setup_driver(self):
        """
        Chrome WebDriver'ı kur
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User agent ekle
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome WebDriver başlatıldı")
    
    def scroll_and_load_more(self, url: str, max_scrolls: int = 10) -> Set[str]:
        """
        Sayfayı aşağı kaydırarak dinamik içerik yükler
        """
        print(f"🔄 Dinamik içerik yükleniyor: {url}")
        self.driver.get(url)
        
        # Sayfa yüklenene kadar bekle
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        found_links = set()
        scroll_count = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while scroll_count < max_scrolls:
            # Mevcut linkleri topla
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_links = self.extract_blog_links(soup)
            
            new_links = page_links - found_links
            if new_links:
                found_links.update(new_links)
                print(f"📄 Scroll {scroll_count + 1}: {len(new_links)} yeni link bulundu (Toplam: {len(found_links)})")
            
            # Sayfayı aşağı kaydır
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # "Load More" butonu varsa tıkla
            try:
                load_more_btn = self.driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'Load More') or contains(text(), 'Daha Fazla') or contains(text(), 'Devamı')]")
                if load_more_btn.is_displayed():
                    load_more_btn.click()
                    print("🔄 'Load More' butonuna tıklandı")
                    time.sleep(2)
            except NoSuchElementException:
                pass
            
            # Yeni içerik yüklenene kadar bekle
            time.sleep(3)
            
            # Sayfa boyutu değişti mi kontrol et
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("🔄 Daha fazla içerik yüklenemedi")
                break
                
            last_height = new_height
            scroll_count += 1
        
        print(f"✅ Toplam {len(found_links)} benzersiz blog linki bulundu")
        return found_links
    
    def extract_blog_links(self, soup: BeautifulSoup) -> Set[str]:
        """
        BeautifulSoup ile blog linklerini çıkar
        """
        links = set()
        
        # Farklı selektörleri dene
        selectors = [
            'a[href*="/blog/"]',
            '.post-title a',
            '.entry-title a',
            'article a',
            '.blog-post a',
            'h1 a, h2 a, h3 a'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                if href and '/blog/' in href and href not in ['/blog/', '/category/blog/']:
                    full_url = href if href.startswith('http') else BASE_URL + href.lstrip('/')
                    # Gerçek blog yazısı linklerini filtrele
                    if self.is_valid_blog_link(full_url):
                        links.add(full_url)
        
        return links
    
    def is_valid_blog_link(self, url: str) -> bool:
        """
        Geçerli blog yazısı linki mi kontrol et
        """
        invalid_patterns = [
            '/blog/',
            '/category/',
            '/tag/',
            '/page/',
            '/author/',
            '#',
            'javascript:',
            'mailto:'
        ]
        
        # Geçersiz pattern'ları kontrol et
        for pattern in invalid_patterns:
            if url.endswith(pattern) or pattern in url.split('/')[-1]:
                return False
        
        # Blog yazısı gibi görünüyor mu?
        return len(url.split('/')) >= 5 and '/blog/' in url
    
    def get_all_blog_links(self) -> List[str]:
        """
        Tüm blog linklerini topla
        """
        try:
            self.setup_driver()
            
            # Ana blog sayfası
            blog_url = BASE_URL + "blog/"
            links_from_blog = self.scroll_and_load_more(blog_url)
            
            # Category sayfası
            category_url = BASE_URL + "category/blog/"
            links_from_category = self.scroll_and_load_more(category_url)
            
            # Tüm linkleri birleştir
            all_links = links_from_blog.union(links_from_category)
            
            print(f"🎯 Toplam {len(all_links)} benzersiz blog yazısı bulundu!")
            return list(all_links)
            
        except Exception as e:
            print(f"❌ Selenium scraping hatası: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 WebDriver kapatıldı")
    
    def load_website_docs_advanced(self) -> List:
        """
        Selenium ile bulunan tüm linkleri WebBaseLoader ile yükle
        """
        print("🚀 Gelişmiş scraping başlıyor...")
        
        # Tüm blog linklerini bul
        blog_links = self.get_all_blog_links()
        
        if not blog_links:
            print("❌ Blog linki bulunamadı!")
            return []
        
        # Ana sayfa + tüm blog yazıları
        all_urls = [BASE_URL] + blog_links
        
        print(f"📥 {len(all_urls)} URL yükleniyor...")
        
        try:
            loader = WebBaseLoader(all_urls)
            docs = loader.load()
            print(f"✅ {len(docs)} doküman başarıyla yüklendi!")
            return docs
            
        except Exception as e:
            print(f"❌ WebBaseLoader hatası: {e}")
            return []
    
    def save_advanced_data(self, docs, filename: str = None):
        """
        Gelişmiş scraping verilerini kaydet
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_scraped_data_{timestamp}.json"
        
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
                "scraper_type": "selenium_advanced"
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Gelişmiş scraping verileri kaydedildi: {filepath}")
        return filepath

def advanced_scrape_and_save():
    """
    Ana gelişmiş scraping fonksiyonu
    """
    scraper = AdvancedScraper(headless=True)
    docs = scraper.load_website_docs_advanced()
    
    if docs:
        filepath = scraper.save_advanced_data(docs)
        print(f"🎉 Gelişmiş scraping tamamlandı! {len(docs)} doküman kaydedildi.")
        return docs
    else:
        print("❌ Gelişmiş scraping başarısız!")
        return []

def test_selenium_scraping():
    """
    Selenium scraper'ı test etmek için önizleme fonksiyonu
    """
    print("🔍 Selenium scraping testi başlıyor...\n")
    
    try:
        scraper = AdvancedScraper(headless=True)
        
        # Sadece linkleri bul (dokümanları yükleme)
        print("📄 Blog linklerini tespit ediliyor...")
        blog_links = scraper.get_all_blog_links()
        
        if not blog_links:
            print("❌ Hiç blog linki bulunamadı!")
            return []
        
        print(f"✅ Toplam {len(blog_links)} blog yazısı bulundu!\n")
        
        # İlk 10 linki göster
        print("🔍 Bulunan blog yazıları (ilk 10):")
        for i, link in enumerate(blog_links[:10], 1):
            print(f"  {i}. {link}")
        
        if len(blog_links) > 10:
            print(f"  ... ve {len(blog_links) - 10} tane daha")
        
        # Kullanıcıya seçenek sun
        print(f"\n📊 Sonuç: {len(blog_links)} blog yazısı tespit edildi")
        print("💡 Bu sayı beklediğiniz 60'a yakın mı?")
        
        return blog_links
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        return []

def test_with_sample_content():
    """
    Birkaç blog yazısının içeriğini de test et
    """
    print("🔍 İçerik testi başlıyor...\n")
    
    try:
        scraper = AdvancedScraper(headless=True)
        
        # Önce linkleri bul
        blog_links = scraper.get_all_blog_links()
        
        if not blog_links:
            print("❌ Test için blog linki bulunamadı!")
            return
        
        # İlk 3 blog yazısının içeriğini yükle
        test_urls = [BASE_URL] + blog_links[:3]
        print(f"📥 Test için {len(test_urls)} URL yükleniyor...")
        
        from langchain_community.document_loaders import WebBaseLoader
        loader = WebBaseLoader(test_urls)
        docs = loader.load()
        
        print(f"✅ {len(docs)} doküman yüklendi\n")
        
        # İçerik önizlemesi
        for i, doc in enumerate(docs):
            print(f"📄 ({i+1}) Kaynak: {doc.metadata.get('source', 'Bilinmiyor')}")
            content_preview = doc.page_content[:200].replace('\n', ' ').strip()
            print(f"📝 İçerik: {content_preview}...")
            print("-" * 80)
        
        return docs
        
    except Exception as e:
        print(f"❌ İçerik testi sırasında hata: {e}")
        return []

if __name__ == "__main__":
    print("🚀 Selenium tabanlı gelişmiş scraper başlatılıyor...\n")
    print("Seçenekler:")
    print("1️⃣ Link testi - Sadece blog linklerini bul")
    print("2️⃣ İçerik testi - Birkaç yazının içeriğini de test et") 
    print("3️⃣ Tam scraping - Tüm verileri çek ve kaydet\n")
    
    # Varsayılan olarak link testini çalıştır
    print("🔄 Link testi çalıştırılıyor...\n")
    links = test_selenium_scraping()
    
    if links and len(links) >= 10:  # En az 10 link bulunmuşsa
        print(f"\n✨ Test başarılı! {len(links)} link bulundu.")
        print("💾 Tüm verileri kaydetmek için advanced_scrape_and_save() çalıştırın.")
    else:
        print(f"\n⚠️  Sadece {len(links) if links else 0} link bulundu.")
        print("🔧 Scraping stratejisini gözden geçirmek gerekebilir.")
