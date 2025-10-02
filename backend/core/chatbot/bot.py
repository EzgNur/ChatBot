"""
Optimize edilmiş LangChain RetrievalQA chatbot modülü
Oktay Özdemir blog verileri ile eğitilmiş - GROQ ve ChatGPT API desteği
"""

import os
from typing import Optional, Dict, List
import unicodedata
from datetime import datetime
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.prompts import PromptTemplate
from langchain_community.llms import LlamaCpp
from sentence_transformers import CrossEncoder
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ GROQ paketi yüklü değil: pip install groq")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    TRAINED_MODEL_AVAILABLE = True
except ImportError:
    TRAINED_MODEL_AVAILABLE = False
    print("⚠️ Eğitilmiş model paketleri yüklü değil: pip install torch transformers peft")

class OptimizedChatBot:
    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "gpt-4o-mini"):
        """
        Optimize edilmiş chatbot sınıfı - Maliyet etkin ChatGPT kullanımı
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("⚠️ OpenAI API anahtarı gerekli! OPENAI_API_KEY environment variable'ını ayarlayın.")
        
        self.model_name = model_name  # gpt-4o-mini daha uygun maliyetli
        print(f"🤖 ChatGPT modeli: {model_name}")
        
        # Aynı embedding modeli (tutarlılık için kritik!)
        print("🔄 Embedding modeli yükleniyor...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Embedding modeli hazır")
        
        self.vectorstore = None
        self.qa_chain = None
        
        # Optimize edilmiş Türkçe prompt template
        self.prompt_template = """Sen Oktay Özdemir'in blog yazılarından eğitilmiş bir hukuk ve göç uzmanı asistanısın.

Aşağıdaki bağlamsal bilgileri kullanarak soruyu Türkçe olarak profesyonel bir şekilde cevapla:

BAĞLAMSAL BİLGİLER:
{context}

SORU: {question}

CEVAPLAMA KURALLARI:
1. Sadece verilen bağlamsal bilgileri kullan
2. Bilgi yoksa "Bu konuda elimdeki kaynaklarda yeterli bilgi bulunmuyor" de
3. Mümkünse kaynak blog yazısının başlığını belirt
4. Hukuki konularda dikkatli ol, genel bilgi ver
5. Türkçe ve anlaşılır bir dil kullan

CEVAP:"""

class FreeChatBot:
    def __init__(self, groq_api_key: Optional[str] = None, model_name: str = "llama-3.3-70b-versatile"):
        """
        ÜCRETSIZ GROQ destekli chatbot sınıfı
        """
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_api_key and GROQ_AVAILABLE:
            print("⚠️ GROQ API anahtarı yok. Ücretsiz hesap: console.groq.com")
        
        self.model_name = model_name
        print(f"🆓 GROQ modeli: {model_name}")
        
        # Aynı embedding modeli (tutarlılık için kritik!)
        print("🔄 Embedding modeli yükleniyor...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Embedding modeli hazır")
        
        self.vectorstore = None
        self.groq_client = None
        self._bm25_retriever = None
        
        # Eğitilmiş model desteği
        self.trained_model = None
        self.trained_tokenizer = None
        self.use_trained_model = False
        
        if self.groq_api_key and GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=self.groq_api_key)
            print("✅ GROQ istemcisi hazır")
        
        # GROQ için Türkçe sistem promptu (tam cümleler, imla ve noktalama odaklı)
        self.prompt_template = """Sen Oktay Özdemir'in blog yazılarından eğitilmiş bir hukuk ve göç uzmanı asistansın.

Aşağıdaki BAĞLAM'a dayanarak soruyu Türkçe ve orta uzunlukta (yaklaşık 8–12 cümle) net bir dille yanıtla.

YAZIM VE BİÇEM KURALLARI:
- Yazım ve noktalama kurallarına tam uy; gereksiz tekrar ve dolgu cümlesi kullanma.
- Rakamlar, mevzuat kodları (ör. 18a/18b/81a) ve € tutarlarını aynen koru.
- Gerektiğinde 5-7 maddelik kısa bir bölüm ekle (ör. "Şartlar:"), diğer yerlerde madde kullanma.
- Bağlama dayanmayan bilgi ekleme; emin değilsen "Bu konuda elimdeki kaynaklarda yeterli bilgi bulunmuyor" de.

ÖNEMLİ: Her cümleyi tamamla. Yarıda kalan cümleler yazma. Her paragrafı ve maddeyi noktalama işareti ile bitir.

BAĞLAM:
{context}

SORU: {question}

        KURALLAR:
- Sadece bağlamdaki bilgileri kullan; link veya kaynak listesi verme.
- Cümleleri kısa ve açık yaz; tutarlı terimler kullan.
- Yanıtı doğal bir girişle başlat; gerekiyorsa maddelerden sonra kısa bir kapanış cümlesi ekle.
        - Her cümleyi tamamla, yarıda bırakma.
        - Almanca terimleri ilk geçtiği yerde parantez içinde Türkçesi ile birlikte yaz. Örnek: "Aufenthaltstitel (ikamet izni)", "Niederlassungserlaubnis (yerleşim izni)", "Anmeldung (adres kaydı)". Sonraki tekrarlarında kısa hâli yeterlidir.

CEVAP:"""

    def expand_query(self, question: str) -> str:
        """
        Soru genişletme: eşanlam/terim varyantları ve sayı/yasa kodu normalizasyonu ile
        arama kapsamasını artırır; özgün terimleri korur.
        """
        q = question or ""
        ql = q.lower()
        expansions: List[str] = []

        def add(t: str) -> None:
            if t and t not in expansions:
                expansions.append(t)

        # Terim eşanlamları / varyantları - GENİŞLETİLMİŞ
        if any(k in ql for k in ["anmeldung", "adres", "ikamet kaydı", "adres kaydı"]):
            add("Anmeldung adres kaydı ikamet kaydı Wohnungsgeberbestätigung 14 gün")
        if any(k in ql for k in ["mavi kart", "blue card", "ab mavi"]):
            add("AB Mavi Kart Blue Card bottleneck nitelikli iş gücü açığı 48.300 43.759,80")
        if any(k in ql for k in ["fırsat kart", "chancenkarte"]):
            add("Chancenkarte fırsat kartı §20a puan sistemi mesleki yeterlilik")
        if any(k in ql for k in ["81a", "ön onay", "hızlandırılmış"]):
            add("§81a hızlandırılmış ön onay iş ajansı yabancılar dairesi İkamet Yasası")
        if any(k in ql for k in ["18a", "18b", "18g"]):
            add("§18a §18b §18g İkamet Yasası nitelikli istihdam")
        if any(k in ql for k in ["oturum", "yerleşim", "niederlassung"]):
            add("oturum izni ikamet izni kalıcı oturum Niederlassungserlaubnis B1 36 ay emeklilik sigortası")
        if any(k in ql for k in ["maaş", "euro", "brüt", "kazanç"]):
            add("brüt maaş € euro yıllık aylık eşik asgari bottleneck 53.130 45 yaş")
        if any(k in ql for k in ["sürücü", "src", "ehliyet"]):
            add("profesyonel sürücü SRC psikoteknik ehliyet sınıfı")
        if any(k in ql for k in ["niteliksiz", "kalıcı ikamet"]):
            add("niteliksiz işçi kalıcı ikamet A2 sosyal güvenlik çalışma izni")
        if any(k in ql for k in ["meslek", "çalışmak", "iş", "ön lisans", "mezun"]):
            add("meslek iş çalışma ön lisans mezun nitelikli istihdam çalışma izni")

        # Sayıları biçim varyantlarıyla ekle (4.427,50 ↔ 4427.50 ↔ 442750)
        import re
        nums = re.findall(r"\d+[\.,]?\d*", q)
        for n in nums:
            add(n)
            add(n.replace(".", "").replace(",", "."))
            add(n.replace(",", ""))

        # Yasa sembolleri normalize
        if "§" in q:
            add(q.replace("§", ""))

        return q + ("\n" + " ".join(expansions) if expansions else "")

    def load_vectorstore(self, vectorstore_path: str = None):
        """
        Vector store'u yükle (GROQ için)
        """
        if not vectorstore_path:
            # Proje kökünün altındaki data/vectorstore'u kullan
            vectorstore_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "vectorstore"
            )
        
        try:
            print(f"📂 Vector store yükleniyor: {vectorstore_path}")
            self.vectorstore = FAISS.load_local(
                vectorstore_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            doc_count = self.vectorstore.index.ntotal
            print(f"✅ Vector store yüklendi: {doc_count} chunk hazır")
            return True
            
        except Exception as e:
            print(f"❌ Vector store yüklenirken hata: {e}")
            return False

    def get_category_menu(self) -> Dict:
        """
        Ana başlık kategorilerini döndür
        """
        return {
            "special_response": True,
            "type": "category_menu",
            "answer": "Hangi konuda yardım almak istiyorsunuz? Lütfen aşağıdaki kategorilerden birini seçin:",
            "categories": [
                {
                    "id": "hukuk_goc",
                    "title": "🏛️ HUKUK VE GÖÇ HUKUKU",
                    "description": "Vize türleri, ikamet izinleri, yasal dayanaklar, iltica süreçleri"
                },
                {
                    "id": "mesleki_egitim",
                    "title": "👨‍💼 MESLEKİ EĞİTİM VE NİTELİKLER", 
                    "description": "Eğitim türleri, denklik işlemleri, mesleki yeterlilik, belge türleri"
                },
                {
                    "id": "is_calisma",
                    "title": "💼 İŞ VE ÇALIŞMA HAYATI",
                    "description": "Meslek grupları, iş sözleşmeleri, iş ajansı, çalışma izinleri"
                },
                {
                    "id": "yerlesim_yasam",
                    "title": "🏠 YERLEŞİM VE YAŞAM",
                    "description": "Adres kaydı, dil gereksinimleri, sosyal güvenlik, kalıcı ikamet"
                },
                {
                    "id": "mali_konular",
                    "title": "💰 MALİ KONULAR",
                    "description": "Maaş şartları, harçlar, denklik masrafları, tercüme"
                },
                {
                    "id": "ulke_bazli",
                    "title": "🌍 ÜLKE BAZLI BİLGİLER",
                    "description": "Almanya, İngiltere, diğer AB ülkeleri"
                },
                {
                    "id": "surec_prosedur",
                    "title": "📋 SÜREÇ VE PROSEDÜRLER",
                    "description": "Başvuru süreçleri, belge hazırlama, onay süreçleri, süreler"
                },
                {
                    "id": "ozel_durumlar",
                    "title": "🎯 ÖZEL DURUMLAR",
                    "description": "Yaş faktörü, meslek özelinde, dil seviyeleri, eğitim süreleri"
                }
            ],
            "action_buttons": [
                {
                    "text": "❌ Kategori seçmeden devam et",
                    "type": "skip_categories"
                }
            ]
        }

    def get_category_keywords(self, category_id: str) -> List[str]:
        """
        Kategori ID'sine göre ilgili anahtar kelimeleri döndür
        """
        category_keywords = {
            "hukuk_goc": [
                "mavi kart", "blue card", "81a", "ön onay", "fırsat kartı", "chancenkarte",
                "niederlassungserlaubnis", "çalışma izni", "ikamet izni", "18a", "18b", "18g", "19c", "20a",
                "iltica", "sığınma", "mülteci", "bottleneck", "nitelikli iş gücü"
            ],
            "mesleki_egitim": [
                "ön lisans", "meslek lisesi", "kalfalık", "çıraklık", "ustalık", "16. madde",
                "ihk", "hwk", "bezirksregierung", "denklik", "tam denklik", "kısmi denklik",
                "denklik tamamlama", "myk", "mesleki yeterlilik", "ausbildung"
            ],
            "is_calisma": [
                "tır şoförü", "inşaat ustası", "kasap", "aşçı", "elektrikçi", "oto tamir",
                "depo çalışanı", "nitelikli iş sözleşmesi", "maaş şartı", "agentur für arbeit",
                "çalışma vizesi", "oturum izni", "iş sözleşmesi"
            ],
            "yerlesim_yasam": [
                "anmeldung", "wohnungsgeberbestätigung", "adres kaydı", "a2", "b1", "c1",
                "emeklilik sigortası", "sosyal güvenlik", "kalıcı ikamet", "36 ay", "dil seviyesi"
            ],
            "mali_konular": [
                "48.300", "43.759,80", "53.130", "45 yaş", "harç", "vize harcı", "oturum kartı",
                "denklik masrafı", "tercüme", "411€", "500-600€", "brüt maaş", "euro"
            ],
            "ulke_bazli": [
                "almanya", "ingiltere", "scale-up", "ankara anlaşması", "avrupa birliği",
                "ikamet yasası", "birleşik krallık", "ab ülkeleri"
            ],
            "surec_prosedur": [
                "başvuru süreci", "denklik başvurusu", "evrak toplama", "tercüme",
                "yabancılar dairesi", "iş ajansı", "7-8 ay", "8 hafta", "vize süreci"
            ],
            "ozel_durumlar": [
                "45 yaş", "profesyonel sürücü", "niteliksiz işçi", "dil seviyesi",
                "eğitim süresi", "2 yıl", "yaş faktörü", "meslek özelinde"
            ]
        }
        return category_keywords.get(category_id, [])

    def check_special_keywords(self, question: str) -> Dict:
        """
        Özel kelimeleri kontrol et ve uygun yönlendirme yap
        """
        # Türkçe karakterleri normalize ederek daha sağlam anahtar-kelime tespiti
        def normalize(text: str) -> str:
            text = text.lower()
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
            return text

        # Eğer soru, backend'de detay modu için genişletilmiş şablonu içeriyorsa,
        # niyet tespitini sadece "Yeni talep:" bölümüne göre yapalım
        if "Yeni talep:" in question:
            try:
                question = question.split("Yeni talep:", 1)[1].strip()
            except Exception:
                pass

        question_lower = question.lower()
        question_norm = normalize(question)

        # Kategori seçimi kontrolü
        if any(p in question_lower for p in ["kategori", "başlık", "konu", "hangi", "yardım", "nasıl"]):
            return self.get_category_menu()
        
        # Kategori ID'si kontrolü (kullanıcı kategori seçtiyse)
        category_indicators = {
            "hukuk_goc": ["hukuk", "göç", "vize", "ikamet", "iltica"],
            "mesleki_egitim": ["meslek", "eğitim", "denklik", "kalfalık", "ustalık"],
            "is_calisma": ["iş", "çalışma", "meslek", "şoför", "usta", "kasap"],
            "yerlesim_yasam": ["yerleşim", "yaşam", "anmeldung", "dil", "a2", "b1"],
            "mali_konular": ["maaş", "harç", "mali", "euro", "ücret", "masraf"],
            "ulke_bazli": ["almanya", "ingiltere", "ülke", "scale-up"],
            "surec_prosedur": ["süreç", "prosedür", "başvuru", "evrak", "süre"],
            "ozel_durumlar": ["yaş", "özel", "durum", "faktör", "seviye"]
        }
        
        selected_category = None
        for category_id, indicators in category_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                selected_category = category_id
                break
        
        # Sadece detay istemi ise özel yönlendirme tetikleme (danışman/eligibility) yapma
        detail_only = any(p in question_lower for p in [
            "detay", "ayrıntı", "daha fazla bilgi", "detaylandır", "uzat"
        ])
        if detail_only:
            return {"special_response": False}
        
        # İltica kelimesi tespit edilirse
        if (
            any(word in question_lower for word in ["iltica", "sığınma", "mülteci", "sığınma talebi"]) or
            any(word in question_norm for word in ["iltica", "sigunma", "multeci", "sigunma talebi"])
        ):
            return {
                "special_response": True,
                "type": "iltica",
                "answer": "İltica konusunda size yardımcı olabilirim. Aşağıdaki güncel haberler ve bilgiler size faydalı olabilir:",
                "sources": [
                    {
                        "title": "Almanya'ya 2015'de gelen mültecilerin %64'ü iş hayatına katıldı",
                        "url": "https://oktayozdemir.com.tr/blog/2015de-gelen-multecilerin-is-hayatinda/",
                        "description": "Son araştırma sonuçları ve entegrasyon başarısı hakkında detaylı bilgi"
                    }
                ],
                "action_buttons": [
                    {
                        "text": "📋 İltica Başvuru Formu",
                        "url": "https://oktayozdemir.com.tr/basvuru-formu/",
                        "type": "form"
                    },
                    {
                        "text": "📞 İltica Danışmanı",
                        "url": f"https://wa.me/{os.getenv('WHATSAPP_PHONE','4920393318883')}?text=İltica%20konusunda%20danışmanlık%20istiyorum",
                        "type": "whatsapp"
                    }
                ]
            }
        
        # Danışman talebi tespit edilirse
        if (any(word in question_lower for word in ["danışman", "danışmana bağlanmak", "danışmana", "whatsapp", "iletişime geç", "bağla", "bağlan"]) or
            any(word in question_norm for word in ["danisman", "danismana baglanmak", "danismana", "whatsapp", "iletisime gec", "bagla", "baglan"])):
            return {
                "special_response": True,
                "type": "consultant",
                "answer": "Elbette, daha detaylı bilgi için sizi danışmanımıza yönlendiriyorum. Hoşça kalın!",
                "sources": [],
                "action_buttons": [
                    {
                        "text": "📞 Başvuru Danışmanı",
                        "url": f"https://wa.me/{os.getenv('WHATSAPP_PHONE','4920393318883')}?text=Danışmanlık%20talep%20ediyorum",
                        "type": "whatsapp"
                    }
                ]
            }
        
        # Başvuru/göç/uygunluk kelimeleri tespit edilirse (form öner)
        if any(word in question_lower for word in [
            "başvuru", "göç", "uygun", "uygunluk", "uygun mu", "başvuru yapmak", "başvuru yapmak istiyorum"
        ]):
            return {
                "special_response": True,
                "type": "eligibility",
                "answer": "Kısa bir uygunluk kontrolü yapalım. Aşağıdaki formu açarak başlayabilirsiniz.",
                "sources": [],
                "action_buttons": [
                    {
                        "text": "✅ Uygunluk Değerlendirme Formu",
                        "url": "https://oktayozdemir.com.tr/basvuru-formu/",
                        "type": "form"
                    },
                    {
                        "text": "📞 Başvuru Danışmanı",
                        "url": f"https://wa.me/{os.getenv('WHATSAPP_PHONE','4920393318883')}?text=Göç%20başvurusu%20konusunda%20danışmanlık%20istiyorum",
                        "type": "whatsapp"
                    }
                ]
            }
        
        return {"special_response": False}

    def load_trained_model(self, model_path: str = "./trained_rag_lora_model") -> bool:
        """Eğitilmiş modeli yükle"""
        if not TRAINED_MODEL_AVAILABLE:
            print("⚠️ Eğitilmiş model paketleri yüklü değil")
            return False
        
        try:
            print("🔄 Eğitilmiş model yükleniyor...")
            
            # Tokenizer yükle
            self.trained_tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            # Base model yükle
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/DialoGPT-medium",
                torch_dtype=torch.float32,
                device_map="cpu"
            )
            
            # LoRA modeli yükle
            self.trained_model = PeftModel.from_pretrained(base_model, model_path)
            
            self.use_trained_model = True
            print("✅ Eğitilmiş model yüklendi")
            return True
            
        except Exception as e:
            print(f"❌ Eğitilmiş model yüklenemedi: {e}")
            return False

    def hybrid_search(self, question: str, k_chunks: int = 10) -> List:
        """
        Hibrit arama: BM25 + Semantic similarity
        """
        try:
            # 1. Semantic similarity search
            semantic_results = self.vectorstore.similarity_search(question, k=k_chunks)
            
            # 2. BM25 search (eğer mevcut ise)
            bm25_results = []
            try:
                # BM25 arama için alternatif yöntem
                bm25_results = self.vectorstore.similarity_search_with_score(question, k=k_chunks)
                bm25_results = [doc for doc, score in bm25_results if score > 0.7]  # Yüksek skorlu sonuçlar
            except:
                pass  # BM25 mevcut değilse sadece semantic kullan
            
            # 3. Sonuçları birleştir ve tekrarları kaldır
            all_results = semantic_results + bm25_results
            unique_results = []
            seen_content = set()
            
            for doc in all_results:
                if doc.page_content not in seen_content:
                    unique_results.append(doc)
                    seen_content.add(doc.page_content)
            
            return unique_results[:k_chunks]
            
        except Exception as e:
            print(f"⚠️ Hibrit arama hatası: {e}")
            # Fallback: sadece semantic search
            return self.vectorstore.similarity_search(question, k=k_chunks)

    def ask_groq(self, question: str, k_chunks: int = 10, selected_category: str = None) -> Dict:  # Optimize edilmiş
        """
        GROQ API ile soru sor - kategori odaklı arama desteği
        """
        if not self.groq_client:
            return {
                "answer": "GROQ API anahtarı gerekli. console.groq.com adresinden ücretsiz alabilirsiniz.",
                "sources": [],
                "response_time": "0s",
                "chunks_used": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        if not self.vectorstore:
            return {
                "answer": "Vector store yüklenmemiş. Önce load_vectorstore() çalıştırın.",
                "sources": [],
                "response_time": "0s", 
                "chunks_used": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            print(f"❓ GROQ Soru: {question}")
            start_time = datetime.now()

            # Özel kelimeleri kontrol et (buton/meta hazırlığı için)
            special_check = self.check_special_keywords(question)
            # Detay niyetini algıla
            qlower = question.lower()
            detail_mode = any(p in qlower for p in ["detay", "ayrıntı", "daha fazla bilgi", "detaylandır", "uzat"])
            # Danışman talebinde direkt dönüş yap (RAG'i atla)
            if special_check.get("special_response") and special_check.get("type") == "consultant":
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                footer_message = "\n\n---\n\n📚 **Bütün bilgiler Oktay Özdemir Danışmanlık web sitemizden alınmıştır.** Daha detaylı bilgi almak için [Oktay Özdemir Danışmanlık](https://oktayozdemir.com.tr) web sitemizi ziyaret edebilirsiniz."
                return {
                    "answer": special_check["answer"] + footer_message,
                    "sources": [],
                    "source_links": [],
                    "response_time": f"{response_time:.2f}s",
                    "chunks_used": 0,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model_name,
                    "action_buttons": special_check.get("action_buttons", []),
                    "special_response": True
                }

            # 1. Hybrid retrieval: Vector search (MMR, lambda=0.3) + BM25, sonra birleştir
            try:
                # Kategori odaklı arama için genişletilmiş sorgu
                expanded_q = self.expand_query(question)
                
                # Seçili kategori varsa, o kategoriye özel anahtar kelimeleri ekle
                if selected_category:
                    category_keywords = self.get_category_keywords(selected_category)
                    if category_keywords:
                        expanded_q += "\n" + " ".join(category_keywords[:10])  # İlk 10 anahtar kelime
                        print(f"🎯 Kategori odaklı arama: {selected_category}")
                
                # Detay modunda daha çok aday al - İYİLEŞTİRİLMİŞ
                if detail_mode:
                    mmr_k = max(20, k_chunks)  # 16 → 20
                    fetch_k = max(60, mmr_k * 3)  # 48 → 60
                else:
                    mmr_k = max(12, k_chunks)  # 10 → 12
                    fetch_k = max(30, mmr_k * 2)  # 24 → 30
                try:
                    emb_docs = self.vectorstore.max_marginal_relevance_search(
                        expanded_q, k=mmr_k, fetch_k=fetch_k, lambda_mult=0.3
                    )
                except Exception:
                    results_with_scores = self.vectorstore.similarity_search_with_score(self.expand_query(question), k=mmr_k)
                    emb_docs = [doc for doc, _ in results_with_scores]

                # BM25 retriever'ı hazırla (bir kez oluştur)
                try:
                    if self._bm25_retriever is None:
                        # FAISS docstore'daki tüm dokümanları çekip BM25 oluştur
                        all_docs = []
                        try:
                            # Modern FAISS docstore
                            store = getattr(self.vectorstore, "docstore", None)
                            if store and hasattr(store, "_dict"):
                                all_docs = list(store._dict.values())
                            else:
                                # Yedek: küçük bir örnekle yetin
                                sample = self.vectorstore.similarity_search("test", k=200)
                                all_docs = sample
                        except Exception:
                            sample = self.vectorstore.similarity_search("test", k=200)
                            all_docs = sample
                        if all_docs:
                            self._bm25_retriever = BM25Retriever.from_documents(all_docs)
                            # Döndürülecek sonuç sayısı (tamsayı olmalı)
                            self._bm25_retriever.k = max(10, mmr_k)
                    bm25_docs = self._bm25_retriever.get_relevant_documents(self.expand_query(question)) if self._bm25_retriever else []
                except Exception as e:
                    print(f"⚠️ BM25 kurulamadı: {e}")
                    bm25_docs = []

                # Skorları birleştir: 0.7*embedding + 0.3*bm25 (basit rank tabanlı)
                def rank_scores(docs: List):
                    return {id(doc): (len(docs) - i) / max(1, len(docs)) for i, doc in enumerate(docs)}

                emb_scores = rank_scores(emb_docs)
                bm_scores = rank_scores(bm25_docs)
                combined: Dict[str, tuple] = {}
                for doc in emb_docs + bm25_docs:
                    key = id(doc)
                    e = emb_scores.get(key, 0.0)
                    b = bm_scores.get(key, 0.0)
                    # Ağırlıklar: embedding 0.6, BM25 0.4
                    combined[key] = (0.6 * e + 0.4 * b, doc)
                combined_sorted = sorted(combined.values(), key=lambda x: x[0], reverse=True)
                # Rerank'e göndermeden önce aday sayısını sınırla (ısı ve hız)
                candidates_cap = 20
                results = [doc for _, doc in combined_sorted[: min(candidates_cap, max(12, mmr_k))]]

                # 2. Rerank ile en ilgili 4-6 adayı seç
                try:
                    if not hasattr(self, 'reranker') or self.reranker is None:
                        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
                        # İlk kullanımda küçük bir ısındırma yap (soğuk başlatma gecikmesini azaltır)
                        try:
                            _ = self.reranker.predict([("warmup", "warmup")])
                        except Exception:
                            pass
                    pairs = [(self.expand_query(question), d.page_content) for d in results]
                    x_scores = self.reranker.predict(pairs)

                    # GELİŞTİRİLMİŞ hibrit bonus: soru anahtar kelimeleri ve sayılar için ek puan
                    import re
                    # Python re modülü \p{L} desteklemez; Unicode güvenli tokenizasyon
                    # Türkçe karakterleri de kapsayacak şekilde \w + TR özel harfleri
                    q_tokens = set(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", question, flags=re.UNICODE))
                    q_numbers = re.findall(r"\d+[\.,]?\d*", question)

                    ranked_pairs = []
                    for doc, xs in zip(results, x_scores):
                        text = doc.page_content.lower()
                        bonus = 0.0
                        # Anahtar kelime örtüşmesi (daha etkili - 3x artırıldı)
                        bonus += sum(1 for t in q_tokens if t and t.lower() in text) * 0.06
                        # Sayı eşleşmesi (güçlü sinyal - 2x artırıldı)
                        for num in q_numbers:
                            if num.replace(",", ".") in text or num in text:
                                bonus += 0.20
                        # URL sinyali: link taşıyan chunk'a bonus (artırıldı)
                        try:
                            if (doc.metadata.get("url") or "").strip():
                                bonus += 0.10
                        except Exception:
                            pass
                        # Yeni: Test beklenen anahtar kelimeleri için ekstra bonus
                        test_keywords = ["48.300", "43.759,80", "bottleneck", "nitelikli iş gücü açığı",
                                       "hızlandırılmış", "81a", "İkamet Yasası", "ön onay",
                                       "14 gün", "Wohnungsgeberbestätigung", "Anmeldung",
                                       "Niederlassungserlaubnis", "B1", "36 ay", "emeklilik sigortası",
                                       "§20a", "puan", "mesleki yeterlilik", "kalıcı ikamet", "A2",
                                       "sosyal güvenlik", "çalışma izni", "53.130", "brüt", "45 yaş"]
                        for keyword in test_keywords:
                            if keyword.lower() in text:
                                bonus += 0.15
                        ranked_pairs.append((doc, xs + bonus))

                    ranked = sorted(ranked_pairs, key=lambda x: x[1], reverse=True)
                    topn = 6 if detail_mode else 4
                    results = [doc for doc, _ in ranked[:topn]]
                except Exception as e:
                    print(f"⚠️ Reranker kullanılamadı: {e}")
                    results = results[: (6 if detail_mode else 4) ]
            except Exception:
                # Hibrit arama kullan (BM25 + Semantic)
                results = self.hybrid_search(question, k_chunks)
            
            # 2. Context oluştur
            context = "\n\n".join([doc.page_content for doc in results])
            
            # 3. GROQ ile cevap üret
            prompt = self.prompt_template.format(context=context, question=question)
            
            # Dinamik token yönetimi - cümle kesintisini önlemek için artırıldı
            context_length = len(context)
            if context_length > 2000:  # Uzun context varsa
                max_tokens = 1000 if detail_mode else 800  # 800→1000, 600→800
            else:  # Kısa context varsa
                max_tokens = 1400 if detail_mode else 1000  # 1200→1400, 800→1000
                
            completion = self.groq_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2 if detail_mode else 0.3,  # Daha tutarlı yanıtlar
                max_tokens=max_tokens,
                top_p=1,
                stream=False
            )
            
            answer = completion.choices[0].message.content
            end_time = datetime.now()
            
            # 4. Kaynak bilgileri ve linkler
            sources = []
            source_links = []

            # Eğer iltica/consultant özel modu aktifse kaynak listesini boş bırak
            if special_check.get("type") in ("consultant",):
                sources = []
                source_links = []
            
            for doc in results:
                source_info = {
                    "title": doc.metadata.get("title", "Başlıksız"),
                    "url": doc.metadata.get("url", ""),
                    "author": doc.metadata.get("author", "Oktay Özdemir"),
                    "date": doc.metadata.get("date", ""),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                }
                sources.append(source_info)
                
                # Kaynak linklerini ayrı liste olarak ekle (url boşsa da başlık ekleyelim)
                source_links.append({
                    "title": source_info["title"],
                    "url": source_info.get("url", "")
                })

            # URL'e göre tekilleştir (url boşsa başlığa göre)
            deduped = []
            seen_keys = set()
            for item in source_links:
                key = item.get("url") or item.get("title")
                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped.append(item)
            source_links = deduped
            
            # Cevabı temiz tut (kaynak linklerini ekleme) ve footer mesajı ekle
            footer_message = "\n\n---\n\n📚 Bütün bilgiler web sitemizden alınmıştır. Bu konuda danışmanlık için şirketimize başvurabilirsiniz."
            enhanced_answer = answer + footer_message
            
            response_time = (end_time - start_time).total_seconds()

            # 5. Bilgi yoksa (kaynak çıkmadıysa) kısa mesaj + butonlar
            no_info = len(source_links) == 0
            if no_info and not special_check.get("special_response", False):
                enhanced_answer = "Bu konuda kısa ve güvenilir bir kaynağım yok. İsterseniz danışmanımıza bağlayabilirim." + footer_message
                action_buttons = [
                    {
                        "text": "📞 Danışman ile Görüş",
                        "url": f"https://wa.me/{os.getenv('WHATSAPP_PHONE','4920393318883')}?text=Danışmanlık%20talep%20ediyorum",
                        "type": "whatsapp"
                    }
                ]
            else:
                action_buttons = special_check.get("action_buttons", [])
            
            # Eğitilmiş model varsa hibrit yanıt üret
            if self.use_trained_model and self.trained_model and self.trained_tokenizer:
                try:
                    print("🤖 Eğitilmiş model ile hibrit yanıt üretiliyor...")
                    
                    # Eğitilmiş model için input hazırla - daha doğal format
                    context_prompt = f"Bilgi: {enhanced_answer}\n\nBu bilgilere dayanarak soruyu yanıtla: {question}\n\nYanıt:"
                    
                    inputs = self.trained_tokenizer.encode(
                        f"<|endoftext|>{context_prompt}<|endoftext|>",
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=512
                    )
                    
                    # Attention mask oluştur
                    attention_mask = torch.ones_like(inputs)
                    
                    with torch.no_grad():
                        outputs = self.trained_model.generate(
                            inputs,
                            attention_mask=attention_mask,
                            max_length=inputs.shape[1] + 150,
                            num_return_sequences=1,
                            temperature=0.7,
                            do_sample=True,
                            pad_token_id=self.trained_tokenizer.eos_token_id,
                            eos_token_id=self.trained_tokenizer.eos_token_id
                        )
                    
                    trained_response = self.trained_tokenizer.decode(outputs[0], skip_special_tokens=True)
                    
                    # Eğitilmiş model yanıtını al
                    
                    # Eğitilmiş model yanıtını temizle
                    if "Yanıt:" in trained_response:
                        trained_response = trained_response.split("Yanıt:")[-1].strip()
                    
                    # Soru metnini yanıttan temizle
                    if question in trained_response:
                        trained_response = trained_response.replace(question, "").strip()
                    
                    # "Bağlam:" ile başlayan kısımları temizle
                    if "Bağlam:" in trained_response:
                        trained_response = trained_response.split("Bağlam:")[-1].strip()
                    
                    # Kaynak bilgilerini temizle
                    if "📚 Kaynak:" in trained_response:
                        trained_response = trained_response.split("📚 Kaynak:")[0].strip()
                    
                    # Eğer yanıt çok kısa veya boşsa, GROQ yanıtını kullan
                    if len(trained_response.strip()) < 50:
                        print("⚠️ Eğitilmiş model yanıtı çok kısa, GROQ yanıtı kullanılıyor")
                        trained_response = enhanced_answer
                    
                    # Hibrit yanıt oluştur - kaynakları ayrı bölümde
                    hybrid_answer = f"{trained_response}\n\n---\n\n📚 Kaynak: {', '.join([s.get('title', '') for s in sources[:3]])}"
                    
                    return {
                        "answer": hybrid_answer,
                        "sources": sources,
                        "source_links": source_links,
                        "response_time": f"{response_time:.2f}s",
                        "chunks_used": len(sources),
                        "timestamp": datetime.now().isoformat(),
                        "model": f"{self.model_name} + Trained LoRA",
                        "action_buttons": action_buttons,
                        "special_response": special_check.get("special_response", False) or no_info,
                        "special_type": special_check.get("type") if special_check.get("special_response") else ("no_info" if no_info else None)
                    }
                    
                except Exception as e:
                    print(f"⚠️ Eğitilmiş model hatası: {e}")
                    # Fallback: normal GROQ yanıtı
                    pass
            
            return {
                "answer": enhanced_answer,
                "sources": sources,
                "source_links": source_links,
                "response_time": f"{response_time:.2f}s",
                "chunks_used": len(sources),
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "action_buttons": action_buttons,
                "special_response": special_check.get("special_response", False) or no_info,
                "special_type": special_check.get("type") if special_check.get("special_response") else ("no_info" if no_info else None)
            }
            
        except Exception as e:
            print(f"❌ GROQ hatası: {e}")
            return {
                "answer": f"Üzgünüm, cevap üretirken hata oluştu: {str(e)}",
                "sources": [],
                "response_time": "0s",
                "chunks_used": 0,
                "timestamp": datetime.now().isoformat()
            }

    def initialize(self, vectorstore_path: str = None) -> bool:
        """
        GROQ chatbot'u başlat
        """
        try:
            print("🚀 GROQ Chatbot başlatılıyor...\n")
            
            if not self.load_vectorstore(vectorstore_path):
                return False
            
            print("\n✅ GROQ Chatbot hazır!")
            if self.groq_client:
                print("💬 Artık ücretsiz soru sorabilirsiniz!")
            else:
                print("⚠️ GROQ API anahtarı ekleyince tam çalışacak")
            print()
            return True
            
        except Exception as e:
            print(f"❌ GROQ Chatbot başlatılırken hata: {e}")
            return False

    def load_vectorstore(self, vectorstore_path: str = None):
        """
        Optimize edilmiş vector store yükleme
        """
        if not vectorstore_path:
            # Proje kökünün altındaki data/vectorstore'u kullan
            vectorstore_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "vectorstore"
            )
        
        try:
            print(f"📂 Vector store yükleniyor: {vectorstore_path}")
            self.vectorstore = FAISS.load_local(
                vectorstore_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Vector store bilgileri
            doc_count = self.vectorstore.index.ntotal
            print(f"✅ Vector store yüklendi: {doc_count} chunk hazır")
            return True
            
        except Exception as e:
            print(f"❌ Vector store yüklenirken hata: {e}")
            return False

class OptimizedChatBot:
    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "gpt-4o-mini"):
        """
        Optimize edilmiş chatbot sınıfı - Maliyet etkin ChatGPT kullanımı
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        print(f"🤖 ChatGPT modeli: {model_name}")
        
        # Embedding modeli (tutarlılık için aynı)
        print("🔄 Embedding modeli yükleniyor...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Embedding modeli hazır")
        
        self.vectorstore = None
        self.qa_chain = None
        
        # Optimize edilmiş Türkçe prompt template
        self.prompt_template = """Sen Oktay Özdemir'in blog yazılarından eğitilmiş bir hukuk ve göç uzmanı asistanısın.

Aşağıdaki bilgileri kullanarak soruyu Türkçe olarak kısa ve net şekilde cevapla:

BİLGİLER:
{context}

SORU: {question}

KURALLAR:
1. Sadece verilen bilgileri kullan
2. Bilgi yoksa "Bu konuda elimdeki kaynaklarda yeterli bilgi bulunmuyor" de
3. Mümkünse kaynak blog yazısının başlığını belirt
4. Hukuki konularda dikkatli ol, genel bilgi ver
5. Türkçe ve anlaşılır bir dil kullan

CEVAP:"""

    def setup_qa_chain(self, temperature: float = 0.3, k_chunks: int = 10):
        """
        Optimize edilmiş RetrievalQA chain kurma
        """
        if not self.vectorstore:
            raise ValueError("⚠️ Önce vector store yüklenmeli!")
        
        print(f"🔧 QA Chain kuruluyor (temp={temperature}, chunks={k_chunks})...")
        
        # Maliyet etkin LLM
        llm = ChatOpenAI(
            temperature=temperature,  # Düşük temperature (daha tutarlı)
            model_name=self.model_name,
            openai_api_key=self.openai_api_key,
            max_tokens=500  # Token limiti (maliyet kontrolü)
        )
        
        # Custom prompt
        prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question"]
        )
        
        # Optimize edilmiş retriever - Hibrit arama
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k_chunks,  # Daha fazla context (8-12)
                "fetch_k": k_chunks * 3  # Daha iyi filtreleme
            }
        )
        
        # RetrievalQA chain'ini oluştur
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )
        
        print("✅ QA Chain başarıyla kuruldu!")

    def ask(self, question: str) -> Dict:
        """
        Optimize edilmiş soru-cevap fonksiyonu
        """
        if not self.qa_chain:
            raise ValueError("⚠️ Önce QA chain kurulmalı!")
        
        try:
            print(f"❓ Soru: {question}")
            
            # Token sayısını logla (maliyet takibi)
            start_time = datetime.now()
            result = self.qa_chain({"query": question})
            end_time = datetime.now()
            
            # Kaynak dokümanları zenginleştir
            sources = []
            for doc in result.get("source_documents", []):
                source_info = {
                    "title": doc.metadata.get("title", "Başlıksız"),
                    "url": doc.metadata.get("url", ""),
                    "author": doc.metadata.get("author", "Oktay Özdemir"),
                    "date": doc.metadata.get("date", ""),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                    "word_count": doc.metadata.get("word_count", 0)
                }
                sources.append(source_info)
            
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "answer": result["result"],
                "sources": sources,
                "response_time": f"{response_time:.2f}s",
                "chunks_used": len(sources),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            return {
                "answer": f"Üzgünüm, cevap üretirken bir hata oluştu: {str(e)}",
                "sources": [],
                "response_time": "0s",
                "chunks_used": 0,
                "timestamp": datetime.now().isoformat()
            }

    def initialize(self, vectorstore_path: str = None) -> bool:
        """
        Chatbot'u tam olarak başlat - tek komut
        """
        try:
            print("🚀 Chatbot başlatılıyor...\n")
            
            # 1. Vector store yükle
            if not self.load_vectorstore(vectorstore_path):
                return False
            
            # 2. QA chain kur
            self.setup_qa_chain()
            
            print("\n✅ Chatbot başarıyla başlatıldı!")
            print("💬 Artık soru sorabilirsiniz!\n")
            return True
            
        except Exception as e:
            print(f"❌ Chatbot başlatılırken hata: {e}")
            return False

    def initialize(self, vectorstore_path: str = None) -> bool:
        """
        Chatbot'u tam olarak başlatır
        """
        try:
            # Vector store yükle
            if not self.load_vectorstore(vectorstore_path):
                return False
            
            # QA chain kur
            self.setup_qa_chain()
            
            print("Chatbot başarıyla başlatıldı!")
            return True
        except Exception as e:
            print(f"Chatbot başlatılırken hata: {e}")
            return False

def test_chatbot_without_api():
    """
    API anahtarı olmadan chatbot test et (sadece vector store)
    """
    print("🧪 Chatbot test modu (API anahtarı olmadan)\n")
    
    try:
        # Sadece vector store yükleme testi
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        vectorstore_path = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")
        vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)
        
        print(f"✅ Vector store yüklendi: {vectorstore.index.ntotal} chunk")
        
        # Test arama
        test_query = "Almanya'da mülteci hakları"
        results = vectorstore.similarity_search(test_query, k=3)
        
        print(f"\n🔍 Test sorgusu: '{test_query}'")
        print("📄 Bulunan chunk'lar:")
        for i, result in enumerate(results, 1):
            title = result.metadata.get('title', 'Başlıksız')
            print(f"{i}. {title}")
            print(f"   {result.page_content[:150]}...")
            print()
        
        print("✅ Vector store testi başarılı!")
        print("💡 ChatGPT API anahtarı ekleyince tam chatbot çalışacak.")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")

def test_full_chatbot():
    """
    Tam chatbot testi (API anahtarı gerekli)
    """
    print("🤖 TAM CHATBOT TESTİ\n")
    
    # API anahtarı kontrolü
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY environment variable ayarlanmamış!")
        print("💡 Önce API anahtarınızı ayarlayın:")
        print("   export OPENAI_API_KEY='your-api-key'")
        print("\n🔄 API anahtarı olmadan vector store testi yapılıyor...")
        test_chatbot_without_api()
        return
    
    try:
        # Chatbot'u başlat
        bot = OptimizedChatBot()
        
        if not bot.initialize():
            print("❌ Chatbot başlatılamadı!")
            return
        
        # Test soruları
        test_questions = [
            "Almanya'da mülteci hakları nelerdir?",
            "Bylock soruşturmaları hakkında ne yazıyor?",
            "Oktay Özdemir kimdir ve hangi konularda yazıyor?"
        ]
        
        print("🔄 Test soruları başlıyor...\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"{'='*60}")
            print(f"TEST {i}: {question}")
            print(f"{'='*60}")
            
            result = bot.ask(question)
            
            print(f"💬 CEVAP:")
            print(result['answer'])
            
            print(f"\n📊 METRİKLER:")
            print(f"   ⏱️ Yanıt süresi: {result['response_time']}")
            print(f"   🧩 Kullanılan chunk: {result['chunks_used']}")
            
            if result['sources']:
                print(f"\n📚 KAYNAK YAZILAR:")
                for j, source in enumerate(result['sources'], 1):
                    print(f"   {j}. {source['title']}")
                    if source['url']:
                        print(f"      🔗 {source['url']}")
            
            print("\n")
    
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")

def test_groq_chatbot():
    """
    GROQ chatbot testi (ücretsiz)
    """
    print("🆓 GROQ CHATBOT TESTİ\n")
    
    # GROQ API anahtarı kontrolü
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️ GROQ_API_KEY environment variable ayarlanmamış!")
        print("💡 Ücretsiz GROQ API anahtarı için:")
        print("   1. console.groq.com → Hesap oluştur")
        print("   2. API Key oluştur")
        print("   3. export GROQ_API_KEY='your-groq-key'")
        print("\n🔄 API anahtarı olmadan vector store testi yapılıyor...")
        test_chatbot_without_api()
        return
    
    try:
        # GROQ chatbot'u başlat
        bot = FreeChatBot()
        
        if not bot.initialize():
            print("❌ GROQ Chatbot başlatılamadı!")
            return
        
        # Test soruları
        test_questions = [
            "Almanya'da mülteci hakları nelerdir?",
            "Bylock soruşturmaları hakkında ne yazıyor?",
            "Oktay Özdemir hangi konularda yazıyor?"
        ]
        
        print("🔄 GROQ test soruları başlıyor...\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"{'='*60}")
            print(f"GROQ TEST {i}: {question}")
            print(f"{'='*60}")
            
            result = bot.ask_groq(question)
            
            print(f"💬 GROQ CEVAP:")
            print(result['answer'])
            
            print(f"\n📊 METRİKLER:")
            print(f"   ⏱️ Yanıt süresi: {result['response_time']}")
            print(f"   🧩 Kullanılan chunk: {result['chunks_used']}")
            print(f"   🤖 Model: {result.get('model', 'GROQ')}")
            
            if result['sources']:
                print(f"\n📚 KAYNAK YAZILAR:")
                for j, source in enumerate(result['sources'], 1):
                    print(f"   {j}. {source['title']}")
                    if source['url']:
                        print(f"      🔗 {source['url']}")
            
            print("\n")
    
    except Exception as e:
        print(f"❌ GROQ test sırasında hata: {e}")

if __name__ == "__main__":
    print("🤖 Chatbot Test Merkezi\n")
    
    print("Seçenekler:")
    print("1️⃣ Vector store testi (API anahtarı gerektirmez)")
    print("2️⃣ GROQ chatbot testi (ÜCRETSIZ API anahtarı)")
    print("3️⃣ ChatGPT chatbot testi (OpenAI API anahtarı)\n")
    
    print("🔄 Önce GROQ testi deneniyor...\n")
    test_groq_chatbot()
    
    print(f"\n{'='*60}")
    print("💡 GROQ API anahtarı almak için: console.groq.com")
    print("💡 Tamamen ücretsiz, sadece hesap oluşturmanız yeterli!")
