# Chatbot AI Projesi

Hukuk ve göç odağında içeriklerinizden eğitilmiş; kategori menüsü, cam efektli arayüz ve mesaj içi aksiyon butonlarına sahip modern bir AI asistanı (FastAPI + React/Vite).

## Proje Yapısı

```
chatbot-project/
│── requirements.txt     # Gerekli Python paketleri
│── main.py             # FastAPI uygulaması
│── README.md           # Bu dosya
│
├── scraping/           # Web scraping modülü
│   │── __init__.py
│   │── web_scraper.py  # WebBaseLoader + BeautifulSoup ile scraping
│
├── data/               # Veri depolama
│   │── raw/           # Çekilen ham veriler (JSON/Metin)
│   │── processed/     # Split + temizlenmiş veriler
│   └── vectorstore/   # FAISS vector database
│
├── vectorstore/        # Embedding ve vector store modülü
│   │── __init__.py
│   │── build_store.py # Embedding + FAISS
│
├── frontend/                        # React + Vite widget
│   ├── package.json                 # npm komutları
│   └── src/pages/ChatbotComponent.tsx  # Home/Chat sekmeli arayüz, kategori menüsü, butonlar
│
└── backend/
    └── core/chatbot/bot.py          # Chat akışı (retrieval, reranker, prompt, token yönetimi)
```

## Kurulum

### 1. Sanal Ortam Oluşturma (Önerilen)

```bash
# Sanal ortam oluştur
python -m venv chatbot_env

# Sanal ortamı aktif et (macOS/Linux)
source chatbot_env/bin/activate

# Sanal ortamı aktif et (Windows)
chatbot_env\Scripts\activate
```

### 2. Bağımlılıkları Yükleme

```bash
pip install -r requirements.txt
```

### 3. Çevresel Değişkenler

```bash
# LLM için zorunlu
export GROQ_API_KEY="gsk_..."

# Frontend’in backend’e bağlanacağı adres (Vite için)
export VITE_API_BASE_URL="http://127.0.0.1:8000"

# Opsiyonel: CRM butonu linki
export VITE_CRM_URL="https://www.alternatifcrm.com"
```

## Kullanım

### 1. Web Scraping

```bash
cd scraping
python web_scraper.py
```

### 2. Vector Store Oluşturma

```bash
cd vectorstore
python build_store.py
```

### 3. Chatbot Test Etme

```bash
cd chatbot
python bot.py
```

### 4. Backend (FastAPI) Çalıştırma

```bash
GROQ_API_KEY="gsk_..." ./chatbot_env/bin/python -m uvicorn main:app \
  --host 127.0.0.1 --port 8000 --reload --access-log --log-level info
```

API şu adreste çalışacak: http://localhost:8000

### 5. Frontend (Vite) Çalıştırma

```bash
cd frontend
npm install
npm run dev
```
Varsayılan dev adresi: http://127.0.0.1:5173

## API Endpoints

- `GET /` - Ana sayfa
- `POST /chat` - Chatbot ile sohbet
- `GET /health` - Sistem durumu kontrolü

## Özellikler (Öne Çıkanlar)

- ✅ Web scraping ile veri toplama
- ✅ Türkçe destekli embedding modeli
- ✅ FAISS vector database
- ✅ LangChain RetrievalQA
- ✅ FastAPI REST API, sağlık ve metrikler
- ✅ LiveChat benzeri Home/Chat düzeni, cam efektli header ve geri butonu
- ✅ Mesaj içi aksiyon butonları (WhatsApp/CRM, şeffaf arka plan + renkli kenarlık)

## Geliştirme Notları

- Türkçe metinler için `paraphrase-multilingual-MiniLM-L12-v2` embedding modeli
- Vector store FAISS ile lokal olarak saklanıyor (`data/vectorstore/`)
- Cevaplarda Almanca terimler ilk geçtiğinde parantez içinde Türkçe karşılığı yazılır
