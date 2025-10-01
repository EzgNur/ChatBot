"""
Vector store oluşturma modülü - Temiz JSON veriler için optimize edilmiş
FAISS kullanarak embedding'leri saklama ve arama yapma
"""

import os
import json
from typing import List, Dict
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

class OptimizedVectorStoreBuilder:
    def __init__(self, embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Optimize edilmiş vector store builder sınıfı
        Temiz JSON veriler için tasarlandı
        """
        self.embedding_model = embedding_model
        print(f"🤖 Embedding modeli yükleniyor: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        
        # Optimize edilmiş chunking parametreleri
        # İstek: chunk_size 400–500, overlap 120–150; sayıları/başlıkları kırmayı azalt
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=450,
            chunk_overlap=120,
            length_function=len,
            separators=[
                "\n\n# ",  # başlık sınırları
                "\n\n## ",
                "\n\n",
                "\n",
                ". ",
                ": ",  # madde/başlık bağları
                ", ",
                " ",
                ""
            ]
        )
        print("✅ Text splitter hazırlandı")
    
    def load_clean_json_data(self, filepath: str) -> List[Document]:
        """
        Temiz JSON verisini yükler ve Document objelerine dönüştürür
        """
        print(f"📂 JSON verisi yükleniyor: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ {len(data)} blog yazısı yüklendi")
        
        documents = []
        total_words = 0
        
        for item in data:
            if item.get('content') and len(item['content'].strip()) > 50:  # Çok kısa içerikleri filtrele
                # Başlık + İçerik birleştir (daha iyi context için)
                full_content = f"Başlık: {item.get('title', '')}\n\n{item['content']}"
                
                doc = Document(
                    page_content=full_content,
                    metadata={
                        "title": item.get('title', ''),
                        "author": item.get('author', 'Oktay Özdemir'),
                        "date": item.get('date', ''),
                        "url": item.get('url', ''),
                        "word_count": item.get('word_count', 0),
                        "content_type": item.get('content_type', 'blog_post'),
                        "language": item.get('language', 'tr'),
                        "domain": item.get('domain', 'law_immigration_politics'),
                        "source_id": item.get('id', len(documents) + 1)
                    }
                )
                documents.append(doc)
                total_words += item.get('word_count', 0)
        
        print(f"📝 Toplam {total_words:,} kelime işlenecek")
        return documents

    def add_texts_with_metadata(self, texts: List[str], metadatas: List[Dict], save_path: str = None):
        """
        Var olan FAISS'e metinleri ekler; yoksa yeni bir FAISS oluşturur.
        """
        if not save_path:
            save_path = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")
        os.makedirs(save_path, exist_ok=True)

        try:
            vectorstore = FAISS.load_local(save_path, self.embeddings, allow_dangerous_deserialization=True)
        except Exception:
            vectorstore = None

        if vectorstore is None:
            documents = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
            vectorstore = FAISS.from_documents(documents, self.embeddings)
        else:
            vectorstore.add_texts(texts, metadatas=metadatas)

        vectorstore.save_local(save_path)
        return True

    def add_transcript_to_vectorstore(self, text: str, meta: Dict | None = None, save_path: str = None) -> int:
        """
        Video transkript metnini mevcut vectorstore'a ekler.
        Dönüş: eklenen chunk sayısı
        """
        if not text or not text.strip():
            return 0
        meta = meta or {}
        chunks = self.text_splitter.split_text(text)
        metadatas: List[Dict] = []
        for _ in chunks:
            metadatas.append({
                "title": meta.get("title", "Video Transcript"),
                "url": meta.get("url", ""),
                "author": meta.get("author", "Video"),
                "date": meta.get("date", datetime.now().strftime("%d/%m/%Y")),
                "source_type": meta.get("source_type", "video_transcript"),
                "video_id": meta.get("video_id"),
                "duration": meta.get("duration"),
            })

        self.add_texts_with_metadata(chunks, metadatas, save_path=save_path)
        return len(chunks)
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Dokümanları küçük parçalara böler
        """
        split_docs = self.text_splitter.split_documents(documents)
        print(f"{len(documents)} doküman {len(split_docs)} parçaya bölündü")
        return split_docs
    
    def build_vectorstore(self, documents: List[Document], save_path: str = None) -> FAISS:
        """
        FAISS vector store oluşturur
        """
        if not save_path:
            save_path = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")
        
        os.makedirs(save_path, exist_ok=True)
        
        print("Embedding'ler oluşturuluyor...")
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        
        # Vector store'u kaydet
        vectorstore.save_local(save_path)
        print(f"Vector store kaydedildi: {save_path}")
        
        return vectorstore
    
    def load_vectorstore(self, load_path: str = None) -> FAISS:
        """
        Kaydedilmiş vector store'u yükler
        """
        if not load_path:
            load_path = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")
        
        try:
            vectorstore = FAISS.load_local(load_path, self.embeddings, allow_dangerous_deserialization=True)
            print(f"Vector store yüklendi: {load_path}")
            return vectorstore
        except Exception as e:
            print(f"Vector store yüklenirken hata: {e}")
            return None
    
    def process_clean_json_to_vectorstore(self, clean_json_filepath: str):
        """
        Temiz JSON veriden vector store'a kadar tüm işlemi yapar
        """
        print("🚀 Vector Store oluşturma süreci başlıyor...\n")
        
        # 1. Temiz JSON verisini yükle
        print("1️⃣ JSON verisi yükleniyor...")
        documents = self.load_clean_json_data(clean_json_filepath)
        
        if not documents:
            print("❌ Hiç doküman yüklenemedi!")
            return None
        
        # 2. Dokümanları chunk'lara böl
        print("\n2️⃣ Dokümanlar chunk'lara bölünüyor...")
        split_docs = self.split_documents(documents)
        
        # 3. İşlenmiş verileri kaydet
        print("\n3️⃣ İşlenmiş veriler kaydediliyor...")
        processed_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
        os.makedirs(processed_dir, exist_ok=True)
        
        processed_data = []
        for i, doc in enumerate(split_docs):
            processed_data.append({
                "chunk_id": i + 1,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "chunk_length": len(doc.page_content),
                "processed_at": datetime.now().isoformat()
            })
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processed_filepath = os.path.join(processed_dir, f"processed_chunks_{timestamp}.json")
        with open(processed_filepath, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ İşlenmiş veriler kaydedildi: {processed_filepath}")
        
        # 4. Vector store oluştur
        print("\n4️⃣ Vector store oluşturuluyor...")
        vectorstore = self.build_vectorstore(split_docs)
        
        # 5. Özet rapor
        print(f"\n🎯 İŞLEM ÖZETİ:")
        print(f"   📄 Toplam doküman: {len(documents)}")
        print(f"   🧩 Toplam chunk: {len(split_docs)}")
        print(f"   📊 Ortalama chunk boyutu: {sum(len(doc.page_content) for doc in split_docs) // len(split_docs)} karakter")
        print(f"   🤖 Embedding modeli: {self.embedding_model}")
        
        return vectorstore

def test_chunking():
    """
    Chunking işlemini test et
    """
    print("🧪 Chunking testi başlıyor...\n")
    
    builder = OptimizedVectorStoreBuilder()
    
    # En son temiz JSON dosyasını bul
    raw_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    
    if not os.path.exists(raw_data_dir):
        print("❌ Ham veri klasörü bulunamadı!")
        return
    
    json_files = [f for f in os.listdir(raw_data_dir) if f.startswith('clean_blog_data_') and f.endswith('.json')]
    if not json_files:
        print("❌ Temiz blog verisi bulunamadı!")
        return
    
    # En son dosyayı al
    latest_file = sorted(json_files)[-1]
    filepath = os.path.join(raw_data_dir, latest_file)
    
    print(f"📂 Test dosyası: {latest_file}")
    
    # Sadece ilk 3 dokümanı test et
    documents = builder.load_clean_json_data(filepath)[:3]
    split_docs = builder.split_documents(documents)
    
    print(f"\n📊 CHUNKING TEST SONUÇLARI:")
    print(f"   📄 Test doküman sayısı: {len(documents)}")
    print(f"   🧩 Oluşan chunk sayısı: {len(split_docs)}")
    
    print(f"\n🔍 İLK 3 CHUNK ÖRNEĞİ:")
    for i, chunk in enumerate(split_docs[:3], 1):
        print(f"\n--- CHUNK {i} ---")
        print(f"Kaynak: {chunk.metadata.get('title', 'Bilinmiyor')}")
        print(f"Uzunluk: {len(chunk.page_content)} karakter")
        print(f"İçerik: {chunk.page_content[:200]}...")

def build_full_vectorstore():
    """
    Tam vector store oluştur
    """
    print("🚀 TAM VECTOR STORE OLUŞTURMA\n")
    
    builder = OptimizedVectorStoreBuilder()
    
    # En son temiz JSON dosyasını bul
    raw_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    json_files = [f for f in os.listdir(raw_data_dir) if f.startswith('clean_blog_data_') and f.endswith('.json')]
    
    if not json_files:
        print("❌ Temiz blog verisi bulunamadı!")
        return None
    
    latest_file = sorted(json_files)[-1]
    filepath = os.path.join(raw_data_dir, latest_file)
    
    print(f"📂 İşlenecek dosya: {latest_file}")
    vectorstore = builder.process_clean_json_to_vectorstore(filepath)
    
    if vectorstore:
        print("\n✅ Vector store başarıyla oluşturuldu!")
        
        # Test arama
        print("\n🔍 Test aramaları yapılıyor...")
        test_queries = [
            "Almanya'da mülteci hakları nelerdir?",
            "Bylock soruşturmaları hakkında ne yazıyor?",
            "Oktay Özdemir kimdir?"
        ]
        
        for query in test_queries:
            print(f"\n❓ Soru: {query}")
            results = vectorstore.similarity_search(query, k=2)
            for i, result in enumerate(results, 1):
                title = result.metadata.get('title', 'Başlık yok')
                print(f"   {i}. {title}")
                print(f"      {result.page_content[:150]}...")
        
        return vectorstore
    else:
        print("❌ Vector store oluşturulamadı!")
        return None

if __name__ == "__main__":
    print("🏗️  Vector Store Builder - Optimize Edilmiş\n")
    
    print("Seçenekler:")
    print("1️⃣ Test modu - Chunking işlemini test et")
    print("2️⃣ Tam işlem - Vector store oluştur\n")
    
    # Varsayılan olarak test modunu çalıştır
    print("🔄 Test modu çalıştırılıyor...\n")
    test_chunking()
    
    print(f"\n{'='*60}")
    print("✨ Test tamamlandı!")
    print("💾 Tam vector store oluşturmak için build_full_vectorstore() çalıştırın.")
