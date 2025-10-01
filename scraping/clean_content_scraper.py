"""
Temiz içerik scraper - Yapay zeka eğitimi için optimize edilmiş
HTML'den gereksiz kısımları temizler, sadece blog yazısı içeriğini alır
"""

import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime
from typing import List, Dict
from bs4 import BeautifulSoup, Tag
from langchain.schema import Document

DEFAULT_BASE_URL = "https://oktayozdemir.com.tr/"

class CleanContentScraper:
    def __init__(self, base_url: str | None = None):
        """
        Temiz içerik scraper sınıfı
        """
        self.blog_urls = []
        # Taban URL'i dışarıdan verilebilir; verilmezse env veya varsayılan kullanılır
        env_base = os.getenv("SCRAPER_BASE_URL")
        self.base_url = (base_url or env_base or DEFAULT_BASE_URL).rstrip('/') + '/'
        
    def get_category_blog_urls(self, category_url: str) -> List[str]:
        """
        Belirli bir kategori sayfasından (ve sayfalandırmasından) blog yazısı URL'lerini topla
        Örn: https://oktayozdemir.com.tr/category/almanya-goc-ve-yasam/
        """
        try:
            all_links: List[str] = []
            page = 1
            base = category_url.rstrip('/') + '/'
            
            while True:
                url = base if page == 1 else f"{base}page/{page}/"
                print(f"📂 Kategori sayfası {page} taranıyor: {url}")
                resp = requests.get(url, timeout=20)
                if resp.status_code == 404:
                    print("❌ Kategori sayfası bitti (404)")
                    break
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                page_links: List[str] = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/blog/' in href and href not in ['/blog/', '/category/blog/']:
                        full = href if href.startswith('http') else self.base_url + href.lstrip('/')
                        if full not in all_links and full not in page_links:
                            page_links.append(full)
                
                print(f"✅ {len(page_links)} link bulundu")
                if not page_links:
                    break
                all_links.extend(page_links)
                page += 1
                if page > 50:
                    print("⚠️  Güvenlik için 50 sayfa sınırı")
                    break
            
            print(f"🎯 Kategoride toplam {len(all_links)} blog linki bulundu")
            return list(set(all_links))
        except Exception as e:
            print(f"❌ Kategori linkleri çekilirken hata: {e}")
            return []
        
    def get_sitemap_urls(self) -> List[str]:
        """
        Sitemap'ten blog URL'lerini al (önceki kodla aynı)
        """
        try:
            print("🔍 Sitemap index kontrol ediliyor...")
            response = requests.get(self.base_url + "sitemap_index.xml")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespaces = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            sitemap_urls = []
            for sitemap_elem in root.findall('.//sitemap:sitemap', namespaces):
                loc = sitemap_elem.find('sitemap:loc', namespaces)
                if loc is not None:
                    sitemap_urls.append(loc.text)
            
            return sitemap_urls
            
        except Exception as e:
            print(f"❌ Sitemap index hatası: {e}")
            return []
    
    def extract_blog_urls_from_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Sitemap'ten blog URL'lerini çıkar
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
            print(f"❌ Sitemap işleme hatası: {e}")
            return []
    
    def get_all_blog_urls(self) -> List[str]:
        """
        Tüm blog URL'lerini topla
        """
        print("📄 Blog URL'leri sitemap'lerden çekiliyor...")
        
        sitemap_urls = self.get_sitemap_urls()
        if not sitemap_urls:
            return []
        
        all_blog_urls = []
        for sitemap_url in sitemap_urls:
            blog_urls = self.extract_blog_urls_from_sitemap(sitemap_url)
            if blog_urls:
                all_blog_urls.extend(blog_urls)
        
        unique_urls = list(set(all_blog_urls))
        print(f"✅ {len(unique_urls)} blog yazısı bulundu")
        return unique_urls

    def get_list_blog_urls(self, list_url: str, max_pages: int | None = None) -> List[str]:
        """
        Blog liste sayfasından (ve sayfalandırmadan) makale URL'lerini topla.
        Alternativkraft gibi '/tr/blog-2/' yapıları için uygundur.
        """
        try:
            all_links: List[str] = []
            page = 1
            base_list = list_url.rstrip('/') + '/'
            while True:
                url = base_list if page == 1 else f"{base_list}page/{page}/"
                print(f"📄 Liste sayfası {page} taranıyor: {url}")
                resp = requests.get(url, timeout=20)
                if resp.status_code == 404:
                    print("❌ Liste sayfası bitti (404)")
                    break
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')

                page_links: List[str] = []
                # 'View More' veya başlık linkleri
                for a in soup.find_all('a', href=True):
                    text = (a.get_text() or '').strip().lower()
                    href = a['href']
                    if any(key in text for key in ['view more', 'weiterlesen', 'devamı', 'devami']):
                        full = href if href.startswith('http') else self.base_url + href.lstrip('/')
                        if full.startswith(self.base_url) and full not in page_links and 'blog-2' not in full and 'category' not in full:
                            page_links.append(full.split('#')[0])

                for heading in soup.find_all(['h2', 'h3']):
                    a = heading.find('a', href=True)
                    if a:
                        href = a['href']
                        full = href if href.startswith('http') else self.base_url + href.lstrip('/')
                        if full.startswith(self.base_url) and full not in page_links and 'blog-2' not in full and 'category' not in full:
                            page_links.append(full.split('#')[0])

                print(f"✅ {len(page_links)} link bulundu")
                if not page_links:
                    break
                # benzersiz ekle
                for l in page_links:
                    if l not in all_links:
                        all_links.append(l)
                page += 1
                # Sınır kontrolü (kullanıcı isteği)
                if max_pages is not None and page > max_pages:
                    print(f"⏹️  Sayfa sınırına ulaşıldı: max_pages={max_pages}")
                    break
                if page > 100:
                    print("⚠️  Güvenlik için 100 sayfa sınırı")
                    break

            print(f"🎯 Listeden toplam {len(all_links)} makale linki bulundu")
            return all_links
        except Exception as e:
            print(f"❌ Liste linkleri çekilirken hata: {e}")
            return []
    
    def clean_html_content(self, html_content: str) -> Dict[str, str]:
        """
        HTML'den temiz blog içeriğini çıkar
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Başlık çıkar
        title = ""
        title_selectors = [
            'h1.entry-title',
            '.post-title h1',
            'h1',
            '.entry-header h1',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                # Site adını temizle
                title = title.replace(' - Oktay Özdemir Danışmanlık', '')
                break
        
        # Ana içerik çıkar
        content = ""
        content_selectors = [
            '.entry-content',
            '.post-content', 
            'article .content',
            '.blog-post-content',
            'main article',
            '.single-post-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Gereksiz elementleri kaldır
                for unwanted in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                    unwanted.decompose()
                
                # Reklam ve sosyal medya butonlarını kaldır
                for unwanted_class in ['.social-share', '.advertisement', '.ads', '.sidebar', '.related-posts']:
                    for elem in content_elem.select(unwanted_class):
                        elem.decompose()
                
                content = content_elem.get_text()
                break
        
        # İçerik temizleme
        if content:
            # Fazla boşlukları temizle
            content = re.sub(r'\n\s*\n', '\n\n', content)  # Çoklu satır sonlarını düzenle
            content = re.sub(r' +', ' ', content)  # Çoklu boşlukları tek boşluğa çevir
            content = content.strip()
            
            # Çok kısa içeriği filtrele
            if len(content) < 200:
                content = ""
        
        # Tarih çıkar
        date = ""
        date_selectors = [
            '.entry-date',
            '.post-date',
            'time[datetime]',
            '.published'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date = date_elem.get_text().strip() or date_elem.get('datetime', '')
                break
        
        # Yazar bilgisi
        author = "Oktay Özdemir"  # Varsayılan
        author_selectors = [
            '.author-name',
            '.post-author',
            '.entry-author'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                break
        
        return {
            'title': title,
            'content': content,
            'author': author,
            'date': date,
            'word_count': len(content.split()) if content else 0
        }
    
    def scrape_single_blog(self, url: str) -> Dict[str, str]:
        """
        Tek bir blog yazısını temiz formatta çek
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            cleaned_data = self.clean_html_content(response.text)
            cleaned_data['url'] = url
            
            return cleaned_data
            
        except Exception as e:
            print(f"❌ Blog çekme hatası ({url}): {e}")
            return {'url': url, 'title': '', 'content': '', 'author': '', 'date': '', 'word_count': 0}
    
    def scrape_all_blogs(self) -> List[Dict[str, str]]:
        """
        Tüm blog yazılarını temiz formatta çek
        """
        print("🚀 Temiz içerik scraping başlıyor...")
        
        blog_urls = self.get_all_blog_urls()
        if not blog_urls:
            print("❌ Blog URL'si bulunamadı!")
            return []
        
        print(f"📥 {len(blog_urls)} blog yazısı işlenecek...")
        
        all_blogs = []
        successful_count = 0
        
        for i, url in enumerate(blog_urls, 1):
            print(f"⏳ ({i}/{len(blog_urls)}) İşleniyor: {url.split('/')[-1]}")
            
            blog_data = self.scrape_single_blog(url)
            
            if blog_data['content'] and len(blog_data['content']) > 200:
                all_blogs.append(blog_data)
                successful_count += 1
                print(f"   ✅ Başarılı - {blog_data['word_count']} kelime")
            else:
                print(f"   ⚠️  İçerik çok kısa veya bulunamadı")
        
        print(f"\n🎯 Toplam {successful_count}/{len(blog_urls)} blog yazısı başarıyla işlendi!")
        return all_blogs

    def scrape_list_blogs(self, list_url: str, max_pages: int | None = None) -> List[Dict[str, str]]:
        """
        Liste sayfasındaki tüm makaleleri temiz formatta çek.
        """
        print("🚀 Liste bazlı temiz içerik scraping başlıyor...")
        urls = self.get_list_blog_urls(list_url, max_pages=max_pages)
        if not urls:
            print("❌ Liste URL'sinden makale linki bulunamadı!")
            return []
        print(f"📥 {len(urls)} makale işlenecek...")
        results: List[Dict[str, str]] = []
        for i, url in enumerate(urls, 1):
            print(f"⏳ ({i}/{len(urls)}) {url}")
            data = self.scrape_single_blog(url)
            if data['content'] and len(data['content']) > 200:
                results.append(data)
                print(f"   ✅ {data['word_count']} kelime")
            else:
                print("   ⚠️  İçerik kısa/boş")
        print(f"\n🎯 Listeden {len(results)}/{len(urls)} yazı başarıyla işlendi!")
        return results

    def scrape_category_blogs(self, category_url: str) -> List[Dict[str, str]]:
        """
        Sadece verilen kategori altındaki blog yazılarını temiz formatta çek
        """
        print("🚀 Kategori bazlı temiz içerik scraping başlıyor...")
        cat_urls = self.get_category_blog_urls(category_url)
        if not cat_urls:
            print("❌ Kategori içinde blog URL'si bulunamadı!")
            return []
        print(f"📥 {len(cat_urls)} blog yazısı işlenecek...")
        results: List[Dict[str, str]] = []
        for i, url in enumerate(cat_urls, 1):
            print(f"⏳ ({i}/{len(cat_urls)}) {url}")
            data = self.scrape_single_blog(url)
            if data['content'] and len(data['content']) > 200:
                results.append(data)
                print(f"   ✅ {data['word_count']} kelime")
            else:
                print("   ⚠️  İçerik kısa/boş")
        print(f"\n🎯 Kategoride {len(results)}/{len(cat_urls)} yazı başarıyla işlendi!")
        return results
    
    def save_clean_data(self, blogs_data: List[Dict], filename: str = None):
        """
        Temiz verileri kaydet - Yapay zeka eğitimi için optimize edilmiş format
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clean_blog_data_{timestamp}.json"
        
        # data/raw klasörünü oluştur
        raw_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
        os.makedirs(raw_data_dir, exist_ok=True)
        
        filepath = os.path.join(raw_data_dir, filename)
        
        # Yapay zeka eğitimi için optimize edilmiş format
        ai_training_data = []
        
        for blog in blogs_data:
            if blog['content']:  # Sadece içeriği olan yazıları ekle
                ai_training_data.append({
                    "id": len(ai_training_data) + 1,
                    "title": blog['title'],
                    "content": blog['content'],
                    "author": blog['author'],
                    "date": blog['date'],
                    "url": blog['url'],
                    "word_count": blog['word_count'],
                    "scraped_at": datetime.now().isoformat(),
                    "scraper_type": "clean_content",
                    # Yapay zeka için ek metadata
                    "content_type": "blog_post",
                    "language": "tr",
                    "domain": "law_immigration_politics"
                })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(ai_training_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Temiz veriler kaydedildi: {filepath}")
        print(f"📊 Kaydedilen yazı sayısı: {len(ai_training_data)}")
        print(f"📝 Toplam kelime sayısı: {sum(blog['word_count'] for blog in ai_training_data):,}")
        
        return filepath

def test_clean_scraping():
    """
    Temiz scraping'i test et
    """
    print("🔍 Temiz içerik testi başlıyor...\n")
    
    scraper = CleanContentScraper()
    
    # Sadece 3 blog yazısını test et
    blog_urls = scraper.get_all_blog_urls()
    if not blog_urls:
        print("❌ Test için blog URL'si bulunamadı!")
        return
    
    test_urls = blog_urls[:3]
    print(f"📥 Test için {len(test_urls)} blog yazısı işlenecek...\n")
    
    for i, url in enumerate(test_urls, 1):
        print(f"🔄 Test {i}: {url.split('/')[-1]}")
        
        blog_data = scraper.scrape_single_blog(url)
        
        print(f"   📋 Başlık: {blog_data['title']}")
        print(f"   ✍️  Yazar: {blog_data['author']}")
        print(f"   📅 Tarih: {blog_data['date']}")
        print(f"   📝 Kelime sayısı: {blog_data['word_count']}")
        
        if blog_data['content']:
            preview = blog_data['content'][:300].replace('\n', ' ')
            print(f"   🔍 İçerik önizleme: {preview}...")
        else:
            print(f"   ⚠️  İçerik bulunamadı")
        
        print("-" * 80)
    
    print("✅ Temiz içerik testi tamamlandı!")

def clean_scrape_and_save(base_url: str | None = None):
    """
    Ana temiz scraping fonksiyonu
    """
    scraper = CleanContentScraper(base_url=base_url)
    blogs_data = scraper.scrape_all_blogs()
    
    if blogs_data:
        filepath = scraper.save_clean_data(blogs_data)
        print(f"🎉 Temiz scraping tamamlandı! Veriler {filepath} dosyasına kaydedildi.")
        return blogs_data
    else:
        print("❌ Temiz scraping başarısız!")
        return []

def clean_scrape_category_and_save(category_url: str, base_url: str | None = None):
    """
    Verilen kategori URL'sinden temiz içerik çek ve kaydet
    """
    scraper = CleanContentScraper(base_url=base_url)
    blogs = scraper.scrape_category_blogs(category_url)
    if blogs:
        filepath = scraper.save_clean_data(blogs)
        print(f"🎉 Kategori scraping tamamlandı! Veriler {filepath} dosyasına kaydedildi.")
        return blogs
    else:
        print("❌ Kategori scraping başarısız!")
        return []

def clean_scrape_list_and_save(list_url: str, base_url: str | None = None, max_pages: int | None = None):
    """
    Verilen liste URL'sinden (ör. https://alternativkraft.com/tr/blog-2/) temiz içerik çek ve kaydet
    """
    scraper = CleanContentScraper(base_url=base_url)
    blogs = scraper.scrape_list_blogs(list_url, max_pages=max_pages)
    if blogs:
        filepath = scraper.save_clean_data(blogs)
        print(f"🎉 Liste scraping tamamlandı! Veriler {filepath} dosyasına kaydedildi.")
        return blogs
    else:
        print("❌ Liste scraping başarısız!")
        return []

if __name__ == "__main__":
    print("🧹 Temiz İçerik Scraper - Yapay Zeka Eğitimi için Optimize Edilmiş\n")
    
    print("Seçenekler:")
    print("1️⃣ Test modu - 3 blog yazısının temiz formatını göster")
    print("2️⃣ Tam scraping - Tüm blog yazılarını temiz formatta çek ve kaydet\n")
    
    # Test modunu çalıştır
    print("🔄 Test modu çalıştırılıyor...\n")
    test_clean_scraping()
