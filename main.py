"""
FastAPI Web Servisi - GROQ Chatbot Entegrasyonu
Oktay Özdemir Blog Chatbot API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
from datetime import datetime
import uvicorn
import tempfile
import os
import glob
import math
from pydub import AudioSegment
import ffmpeg
FFMPEG_CMD = 'ffmpeg'
try:
    import imageio_ffmpeg  # ffmpeg ikilisi yoksa gömülü olanı kullanmak için
    FFMPEG_CMD = imageio_ffmpeg.get_ffmpeg_exe() or 'ffmpeg'
except Exception:
    # imageio-ffmpeg kurulu değilse sistemdeki ffmpeg kullanılacaktır
    FFMPEG_CMD = 'ffmpeg'

# Chatbot import
from backend.core.chatbot.bot import FreeChatBot
from vectorstore.build_store import OptimizedVectorStoreBuilder
from groq import Groq
import language_tool_python
from text_normalizer import normalize_text_pipeline
from langchain.text_splitter import RecursiveCharacterTextSplitter

# FastAPI app
app = FastAPI(
    title="Oktay Özdemir Blog Chatbot API",
    description="GROQ destekli hukuk ve göç uzmanı chatbot",
    version="1.0.0"
)

# CORS middleware (web arayüzü için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React/Vue geliştirme
        "http://localhost:8080",  # Vite/Nuxt
        "http://127.0.0.1:5500",  # Live Server
        "file://",                # Yerel HTML dosyaları
        "*"                       # Geliştirme için (production'da kaldırın)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global chatbot instance
chatbot = None
builder = OptimizedVectorStoreBuilder()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
try:
    tool_tr = language_tool_python.LanguageTool('tr-TR')
except Exception:
    # Java yoksa public API moduna düş
    try:
        tool_tr = language_tool_python.LanguageToolPublicAPI('tr-TR')
    except Exception:
        tool_tr = None

# Basit transkript temizleyici (heuristic)
def clean_transcript_text(text: str) -> str:
    if not text:
        return ""
    import re
    t = text
    # Yaygın giriş/çıkış ve CTA ifadeleri
    patterns = [
        r"^\s*(merhaba(lar)?|selam(lar)?).*$",
        r"abone ol(mayı)?|beğen(meyi)?|kanal(ı|ımıza)|takip etmeyi",
        r"(like|subscribe|yorumlarınızı)",
        r"flash\s*flash",
        r"(görüşürüz|teşekkürler|izlediğiniz için teşekkürler).*",
        r"sanal değil gerçek ofis",
        r"(çayını|kahveni) içersin",
        r"altyazı.*$",
    ]
    for p in patterns:
        t = re.sub(p, "", t, flags=re.IGNORECASE | re.MULTILINE)

    # Sık yazım düzeltmeleri (basit eşleştirme)
    replacements = {
        r"\bön\s*olay\b": "ön onay",
        r"\bön\s*anay\b": "ön onay",
        r"Agentür\s*F[üu]hrer\s*Arb[ae]yt": "Agentur für Arbeit",
        r"Agentür\s*F[üu]hrer\s*Arbeit": "Agentur für Arbeit",
        r"Agentur\s*f[üu]r\s*Arbayt": "Agentur für Arbeit",
        r"\b[İI]data\b": "İdata",
        # 'İdata' yaygın hataları
        r"\biy[ıi]\s*data\b": "İdata",
        r"\biy[ıi]\s*dataya\b": "İdata'ya",
        r"\biy[ıi]\s*dataya\b": "İdata'ya",
        r"\biy[ıi]\s*datadan\b": "İdata'dan",
        r"\biy[ıi]\s*datada\b": "İdata'da",
        r"\biy[ıi]\s*datayı\b": "İdata'yı",
    }
    for pat, rep in replacements.items():
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # Zaman damgaları ve gereksiz tekrar boşluklar
    t = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    t = t.strip()
    
    # LanguageTool ile ek yazım/dil kontrolü
    if tool_tr is not None:
        try:
            matches = tool_tr.check(t)
            t = language_tool_python.utils.correct(t, matches)
        except Exception:
            pass
    return t

# Cevap parlatma: Özet → Detaylar → Kaynaklar + footer ayrı blok
def polish_answer(answer_text: str, source_links: List[Dict]) -> str:
    import re
    text = answer_text or ""
    # Varsa önceki footer/ayırıcıyı kaldır
    text = re.sub(r"\n+—+\n+.*$", "", text, flags=re.DOTALL)
    text = re.sub(r"\n+📚.*$", "", text, flags=re.DOTALL)

    # Cümlelere ayır ve özet çıkar
    sentences = re.split(r"(?<=[\.!?])\s+", text.strip())
    summary = " ".join(sentences[:2]).strip()
    rest = " ".join(sentences[2:]).strip()

    details = []
    if rest:
        # Noktalı cümleleri maddeye çevir (çok uzun maddeleri kısalt)
        chunks = re.split(r"(?<=[\.!?])\s+", rest)
        for ch in chunks:
            c = ch.strip()
            # İçeride tekrar kaynak/footeri andıran cümleleri at
            if (
                len(c) > 0 and
                not c.lower().startswith("kaynak") and
                not c.startswith("—") and
                not c.startswith("---") and
                not c.startswith("📚") and
                "Bütün bilgiler" not in c
            ):
                # Bozuk madde başlarını normalize et
                c = re.sub(r"^([\-*•]+\s*)+", "", c)
                details.append(c)

    # Detayları bölümlere ayır: Şartlar / İstisnalar / Adımlar
    temel: List[str] = []
    istisna: List[str] = []
    adim: List[str] = []

    def looks_like_step(s: str) -> bool:
        return bool(re.match(r"^(adım|önce|ardından|sonra|1\.|2\.|3\.|[0-9]+\))", s.strip(), flags=re.IGNORECASE))

    for d in details:
        dl = d.lower()
        if any(k in dl for k in ["istisna", "hariç", "değilse", "olmadığı", "olmazsa"]):
            istisna.append(d)
        elif looks_like_step(dl):
            # Numerik adımları normalize et
            d_clean = re.sub(r"^(\d+\.|\d+\))\s*", "", d).strip()
            adim.append(d_clean)
        else:
            temel.append(d)

    parts: List[str] = []
    if summary:
        # Başta "Özet:" etiketi olmadan doğal bir ilk paragraf olarak kalsın
        parts.append(summary)
    if temel:
        parts.append("\nŞartlar:\n" + "\n".join([f"- {d}" for d in temel]))
    if istisna:
        parts.append("\nİstisnalar:\n" + "\n".join([f"- {d}" for d in istisna]))
    if adim:
        parts.append("\nAdımlar:\n" + "\n".join([f"- {d}" for d in adim]))

    # Footer'ı ayrı blok olarak ekle
    footer = "\n\n—\n\n📚 Bütün bilgiler Oktay Özdemir Danışmanlık web sitemizden alınmıştır. Daha detaylı bilgi almak için [Oktay Özdemir Danışmanlık](https://oktayozdemir.com.tr) web sitemizi ziyaret edebilirsiniz."

    # Kaynak linklerini istemci tarafında gösteriyoruz; mesaj içinde görünmesin
    return "\n\n".join([p for p in parts if p.strip()]) + footer

# Bilgilendirici önizleme (filler cümleleri çıkar, çekirdek bilgiyi öne al)
def generate_informative_preview(text: str, max_chars: int = 1400) -> str:
    import re
    if not text:
        return ""
    sentences = re.split(r"(?<=[\.!?])\s+", text.strip())

    filler_patterns = [
        r"bildirimleri açın|takip edin|abone ol|beğenin|paylaşın",
        r"sanal değil gerçek ofis",
        r"dostlarınıza tavsiye|arkadaş|eşinizi|dostunuzu",
        r"videonun|kanalın|yorumlarda|açıklama bölümünde",
        r"giriş|kapanış|merhaba|selam",
    ]
    def is_filler(s: str) -> bool:
        s_low = s.lower()
        return any(re.search(p, s_low) for p in filler_patterns) or len(s_low) < 25

    # Bilgi sinyali: rakam, yasa/kod, vize kodları, anahtar kelimeler
    signal_patterns = [
        r"\b(18a|18b|18g|19c|81a|anabin|zab|ezb|mavi kart|blue card)\b",
        r"\b\d{4}\b|%|€|euro|gün|hafta|ay|yıl",
        r"vize|başvuru|randevu|ikamet|çalışma|sözleşme|şart|gerekli|belge|ücret|denklik",
    ]
    def score_sentence(s: str) -> int:
        score = 0
        sl = s.lower()
        for p in signal_patterns:
            if re.search(p, sl):
                score += 1
        if len(s) > 80:
            score += 1
        return score

    informative = [s for s in sentences if not is_filler(s)]
    informative_sorted = sorted(informative, key=score_sentence, reverse=True)

    out: List[str] = []
    total = 0
    for s in informative_sorted:
        if total + len(s) + 1 > max_chars:
            break
        out.append(s)
        total += len(s) + 1
    return " ".join(out).strip()

# Request/Response modelleri
class ChatRequest(BaseModel):
    question: str
    model: Optional[str] = "groq"  # "groq" veya "openai"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict]
    source_links: List[Dict]
    response_time: str
    chunks_used: int
    model: str
    timestamp: str
    action_buttons: Optional[List[Dict]] = None  # Yeni eklendi
    special_response: Optional[bool] = False  # Yeni eklendi
    special_type: Optional[str] = None  # consultant | eligibility | category_menu | None
    categories: Optional[List[Dict]] = None  # Kategori menüsü için

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    vectorstore_loaded: bool
    api_keys_configured: Dict[str, bool]

@app.on_event("startup")
async def startup_event():
    """Uygulama başlatılırken chatbot'u initialize et"""
    global chatbot
    try:
        print("🚀 FastAPI Chatbot başlatılıyor...")
        
        # GROQ chatbot'u başlat
        chatbot = FreeChatBot()
        
        if chatbot.initialize():
            print("✅ GROQ Chatbot başarıyla yüklendi!")
            
            # Eğitilmiş modeli yükle
            model_path = "./trained_rag_lora_model"
            if os.path.exists(model_path):
                if chatbot.load_trained_model(model_path):
                    print("✅ Eğitilmiş model başarıyla yüklendi!")
                    print("🚀 Hibrit sistem aktif: RAG + Eğitilmiş Model")
                else:
                    print("⚠️ Eğitilmiş model yüklenemedi, sadece RAG kullanılacak")
            else:
                print("⚠️ Eğitilmiş model bulunamadı, sadece RAG kullanılacak")
        else:
            print("❌ GROQ Chatbot yüklenemedi!")
            
    except Exception as e:
        print(f"❌ Startup hatası: {e}")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Ana sayfa"""
    return {
        "message": "Oktay Özdemir Blog Chatbot API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Sistem durumu kontrolü"""
    vectorstore_loaded = chatbot is not None and chatbot.vectorstore is not None
    
    api_keys = {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }
    
    resp = HealthResponse(
        status="healthy" if vectorstore_loaded else "degraded",
        message="Chatbot hazır" if vectorstore_loaded else "Vector store yüklenemedi",
        timestamp=datetime.now().isoformat(),
        vectorstore_loaded=vectorstore_loaded,
        api_keys_configured=api_keys
    )
    try:
        print(f"🩺 /health -> status={resp.status} vectorstore_loaded={resp.vectorstore_loaded} api_keys={resp.api_keys_configured}")
    except Exception:
        pass
    return resp

@app.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """Chatbot'a soru sor"""
    try:
        print(f"🧾 Gelen soru: {request.question}")
    except Exception:
        pass
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot henüz yüklenmedi")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Soru boş olamaz")
    
    try:
        # Hafıza: kısa geçmişi al (varsa)
        session_id = request.session_id or "__default__"
        if not hasattr(app.state, "memory"):
            app.state.memory = {}
        memory: Dict[str, List[Dict[str, str]]] = app.state.memory
        turns = memory.get(session_id, [])

        # Niyet: detay
        qlower = request.question.lower()
        detail_intent = any(p in qlower for p in ["detay", "ayrıntı", "daha fazla bilgi", "detaylandır", "uzat"])

        expanded_question = request.question
        if detail_intent and turns:
            # Son kullanıcı sorusu ve asistan cevabını özellikle vurgula
            last_user = next((t.get("content", "") for t in reversed(turns) if t.get("role") == "user"), "")
            last_assistant = next((t.get("content", "") for t in reversed(turns) if t.get("role") == "assistant"), "")

            # Son 3 turu kısa bir izlek olarak ekle (1200 karakter sınırı)
            history_text = []
            for t in turns[-6:]:
                role = t.get("role")
                content = t.get("content", "")
                prefix = "Kullanıcı" if role == "user" else "Asistan"
                history_text.append(f"{prefix}: {content}")
            history_join = " \n".join(history_text)[-1200:]

            expanded_question = (
                "Bu bir takip isteğidir. Aşağıdaki önceki sorunun ayni KONUSUNU daha detaylı, derin ve düzenli olarak genişlet. Konu dışına çıkma.\n" \
                "Önceki kullanıcı sorusu: " + last_user + "\n" \
                "Önceki asistan cevabı (özetlenecek/geliştirilecek): " + last_assistant + "\n\n" \
                "Kısa geçmiş: " + history_join + "\n\n" \
                "Yeni talep: " + request.question
            )

        # Kategori seçimi kontrolü
        selected_category = None
        if "kategori" in request.question.lower() or "başlık" in request.question.lower() or "hangi" in request.question.lower():
            # Kategori menüsü döndür
            result = chatbot.get_category_menu()
        else:
            # Kategori tespiti
            category_indicators = {
                "hukuk_goc": ["hukuk", "göç", "vize", "ikamet", "iltica", "mavi kart", "81a"],
                "mesleki_egitim": ["meslek", "eğitim", "denklik", "kalfalık", "ustalık", "ön lisans"],
                "is_calisma": ["iş", "çalışma", "şoför", "usta", "kasap", "aşçı", "elektrikçi"],
                "yerlesim_yasam": ["yerleşim", "yaşam", "anmeldung", "dil", "a2", "b1"],
                "mali_konular": ["maaş", "harç", "mali", "euro", "ücret", "masraf"],
                "ulke_bazli": ["almanya", "ingiltere", "ülke", "scale-up"],
                "surec_prosedur": ["süreç", "prosedür", "başvuru", "evrak", "süre"],
                "ozel_durumlar": ["yaş", "özel", "durum", "faktör", "seviye"]
            }
            
            for category_id, indicators in category_indicators.items():
                if any(indicator in request.question.lower() for indicator in indicators):
                    selected_category = category_id
                    break
            
            # GROQ ile cevap üret (kategori odaklı)
            result = chatbot.ask_groq(expanded_question, selected_category=selected_category)

        # Kategori menüsü kontrolü
        if result.get("special_response") and result.get("type") == "category_menu":
            # Kategori menüsü için özel response
            resp = ChatResponse(
                answer=result["answer"],
                sources=result.get("sources", []),
                source_links=result.get("source_links", []),
                response_time="0s",
                chunks_used=0,
                model="category_menu",
                timestamp=datetime.now().isoformat(),
                action_buttons=result.get("action_buttons", []),
                special_response=True,
                special_type="category_menu"
            )
            # Kategori bilgilerini ekle
            resp.categories = result.get("categories", [])
        else:
            # Normal cevap işleme
            try:
                cfg = os.path.join(os.path.dirname(__file__), 'config', 'text_rules.yaml')
                stage1 = normalize_text_pipeline(result.get("answer", ""), cfg)
                cleaned_answer = clean_transcript_text(stage1)
                cleaned_answer = polish_answer(cleaned_answer, result.get("source_links", []))
            except Exception:
                cleaned_answer = result.get("answer", "")

            resp = ChatResponse(
                answer=cleaned_answer,
                sources=result.get("sources", []),
                source_links=result.get("source_links", []),
                response_time=result["response_time"],
                chunks_used=result["chunks_used"],
                model=result.get("model", "llama-3.3-70b-versatile"),
                timestamp=result["timestamp"],
                action_buttons=result.get("action_buttons"),
                special_response=result.get("special_response", False),
                special_type=result.get("special_type")
            )
        try:
            ans_preview = (resp.answer or "")[:180].replace("\n", " ") + ("..." if len(resp.answer or "") > 180 else "")
            print(
                f"💬 /ask -> time={resp.response_time} chunks={resp.chunks_used} model={resp.model} "
                f"sources={len(resp.sources)} preview=\"{ans_preview}\""
            )
        except Exception:
            pass
        return resp
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot hatası: {str(e)}")
    finally:
        # Hafızaya kaydet (son 3-5 turu tut)
        try:
            if 'result' in locals() and 'session_id' in locals() and hasattr(app.state, "memory"):
                memory = app.state.memory
                if session_id not in memory:
                    memory[session_id] = []
                memory[session_id].append({"role": "user", "content": request.question})
                # Temizlenmiş cevabı saklıyoruz; gerekirse orijinal cevabı da ekleyebilirsiniz
                memory[session_id].append({"role": "assistant", "content": cleaned_answer})
                # Son 6 kaydı tut (3 tur)
                memory[session_id] = memory[session_id][-6:]
        except Exception:
            pass

@app.post("/ingest/video")
async def ingest_video(
    file: UploadFile = File(...),
    language: str = Form("tr"),
    title: str = Form("Video Transcript"),
    url: str = Form(""),
    author: str = Form("Video"),
    clean: bool = Form(True),
    dry_run: bool = Form(False)
):
    """Video yükle → ses ayıkla → Whisper ile transcribe → FAISS'e ekle."""
    # 1) Temp kaydet
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_vid:
        tmp_vid.write(await file.read())
        video_path = tmp_vid.name

    audio_path = video_path + ".wav"
    try:
        # 2) Ses ayıkla (16k mono WAV)
        stream = (
            ffmpeg
            .input(video_path)
            .output(audio_path, ac=1, ar=16000, format='wav', loglevel="error")
            .overwrite_output()
        )
        ffmpeg.run(stream, cmd=FFMPEG_CMD)

        # 3) Ses uzunluğunu ölç (ffprobe yerine pydub kullan)
        try:
            duration_sec = float(AudioSegment.from_wav(audio_path).duration_seconds)
        except Exception:
            duration_sec = 0.0

        # 413 hatasını önlemek için ~9 dk'lık segmentlere böl (540 sn)
        segment_paths = []
        if duration_sec > 540:
            seg_dir = tempfile.mkdtemp(prefix="segments_")
            seg_pattern = os.path.join(seg_dir, "part_%03d.wav")
            seg_stream = (
                ffmpeg
                .input(audio_path)
                .output(
                    seg_pattern,
                    f='segment',
                    segment_time=540,
                    ac=1,
                    ar=16000,
                    loglevel="error"
                )
                .overwrite_output()
            )
            ffmpeg.run(seg_stream, cmd=FFMPEG_CMD)
            segment_paths = sorted(glob.glob(os.path.join(seg_dir, "part_*.wav")))
        else:
            segment_paths = [audio_path]

        # 4) Her segmenti ayrı ayrı transcribe et ve birleştir
        texts = []
        total_duration = 0.0
        for seg in segment_paths:
            with open(seg, "rb") as af:
                tr = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=af,
                    language=language,
                    response_format="verbose_json"
                )
            texts.append(tr.text.strip())
            try:
                total_duration += float(getattr(tr, "duration", 0) or 0)
            except Exception:
                pass

        text = "\n\n".join(t for t in texts if t)
        duration = total_duration or duration_sec

        # 4) Transkript dosyasını kaydet (görüntülemek için)
        transcripts_dir = os.path.join(os.path.dirname(__file__), "data", "raw", "transcripts")
        os.makedirs(transcripts_dir, exist_ok=True)
        ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_path = os.path.join(transcripts_dir, f"transcript_{ts_name}.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(text)

        # 4.1) Temizleme (opsiyonel) - YAML pipeline + dil denetimi
        if clean:
            cfg = os.path.join(os.path.dirname(__file__), 'config', 'text_rules.yaml')
            stage1 = normalize_text_pipeline(text, cfg)
            final_text = clean_transcript_text(stage1)
        else:
            final_text = text
        cleaned_path = os.path.join(transcripts_dir, f"transcript_cleaned_{ts_name}.txt")
        with open(cleaned_path, "w", encoding="utf-8") as f:
            f.write(final_text)

        if dry_run:
            # Sadece önizleme döndür; FAISS'e ekleme
            # Ayrıca chunk tahmini ve bilgilendirici önizleme ver
            splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
            chunks = splitter.split_text(final_text)
            informative_preview = generate_informative_preview(final_text, max_chars=1400)
            return {
                "ok": True,
                "dry_run": True,
                "chars": len(final_text),
                "title": title,
                "url": url,
                "transcript_file": os.path.relpath(transcript_path, os.path.dirname(__file__)),
                "cleaned_file": os.path.relpath(cleaned_path, os.path.dirname(__file__)),
                "preview": final_text[:1200],
                "informative_preview": informative_preview,
                "total_chunks_estimate": len(chunks),
                "first_chunks": chunks[:3]
            }
        else:
            # 5) FAISS'e ekle (temiz metin)
            meta = {"title": title, "url": url, "author": author, "source_type": "video_transcript", "duration": duration}
            chunks_added = builder.add_transcript_to_vectorstore(final_text, meta)

            # 6) API'nin anlık istatistiklerinde de görünsün diye chatbot'un vectorstore'unu yeniden yükle
            global chatbot
            try:
                if chatbot is not None:
                    vs_path = os.path.join(os.path.dirname(__file__), "data", "vectorstore")
                    chatbot.vectorstore = builder.load_vectorstore(vs_path)
            except Exception:
                pass

            return {
                "ok": True,
                "dry_run": False,
                "chars": len(final_text),
                "chunks_added": chunks_added,
                "title": title,
                "url": url,
                "transcript_file": os.path.relpath(transcript_path, os.path.dirname(__file__)),
                "cleaned_file": os.path.relpath(cleaned_path, os.path.dirname(__file__)),
                "preview": final_text[:500]
            }
    finally:
        for p in [video_path, audio_path]:
            try:
                os.remove(p)
            except Exception:
                pass

@app.post("/ingest/transcript")
async def ingest_transcript(
    text: str = Form(...),
    title: str = Form("Video Transcript"),
    url: str = Form(""),
    author: str = Form("Video"),
    clean: bool = Form(True)
):
    """Hazır metin transkripti (veya düzenlenmiş metni) vektör store'a ekler."""
    original = text
    if clean:
        cfg = os.path.join(os.path.dirname(__file__), 'config', 'text_rules.yaml')
        stage1 = normalize_text_pipeline(text, cfg)
        cleaned = clean_transcript_text(stage1)
    else:
        cleaned = text

    transcripts_dir = os.path.join(os.path.dirname(__file__), "data", "raw", "transcripts")
    os.makedirs(transcripts_dir, exist_ok=True)
    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join(transcripts_dir, f"manual_raw_{ts_name}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(original)

    cleaned_path = os.path.join(transcripts_dir, f"manual_cleaned_{ts_name}.txt")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    meta = {"title": title, "url": url, "author": author, "source_type": "video_transcript"}
    chunks_added = builder.add_transcript_to_vectorstore(cleaned, meta)

    # Vectorstore'u yeniden yükle ki /stats anında güncellensin
    global chatbot
    try:
        if chatbot is not None:
            vs_path = os.path.join(os.path.dirname(__file__), "data", "vectorstore")
            chatbot.vectorstore = builder.load_vectorstore(vs_path)
    except Exception:
        pass

    return {
        "ok": True,
        "chars_raw": len(original),
        "chars_cleaned": len(cleaned),
        "chunks_added": chunks_added,
        "raw_file": os.path.relpath(raw_path, os.path.dirname(__file__)),
        "cleaned_file": os.path.relpath(cleaned_path, os.path.dirname(__file__)),
        "clean_preview": cleaned[:500]
    }

@app.get("/models")
async def get_available_models():
    """Mevcut model listesi"""
    return {
        "groq": {
            "llama-3.3-70b-versatile": "Ana model (önerilen)",
            "llama-3.1-8b-instant": "Hızlı model",
            "gemma2-9b-it": "Google modeli"
        },
        "openai": {
            "gpt-4o-mini": "Maliyet etkin",
            "gpt-4o": "En iyi kalite"
        }
    }

@app.get("/stats")
async def get_stats():
    """Sistem istatistikleri"""
    if not chatbot or not chatbot.vectorstore:
        return {"error": "Vector store yüklenmemiş"}
    
    doc_count = chatbot.vectorstore.index.ntotal
    embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    return {
        "vectorstore": {
            "total_chunks": doc_count,
            "embedding_model": embedding_model,
            "status": "loaded"
        },
        "api_status": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY"))
        },
        "uptime": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🌐 FastAPI Chatbot başlatılıyor...")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("Chat Endpoint: POST http://localhost:8000/ask")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )