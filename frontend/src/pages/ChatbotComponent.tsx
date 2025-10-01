import React, { useState, useRef, useEffect } from 'react';
import { askApi } from '../services/api';
import type { SourceLink } from '../services/api';

interface ActionButton {
  text: string;
  url?: string;
  type?: string;
}

// ChatbotResponse artık askApi tipinden türetildiği için ayrı bir arayüz gerekmiyor

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  sources?: SourceLink[];
}

const ChatbotComponent: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Merhaba! Ben Oktay Özdemir Danışmanlık Bürosu AI asistanıyım. Size nasıl yardımcı olabilirim?',
      isUser: false,
      timestamp: new Date()
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [showTopics, setShowTopics] = useState(true);
  const [activeTab, setActiveTab] = useState<'home' | 'chat'>('home');
  const [topicsMode, setTopicsMode] = useState<'generic' | 'iltica'>('generic');
  const [actionButtons, setActionButtons] = useState<ActionButton[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [consultOnly, setConsultOnly] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sekme bazlı kalıcı oturum kimliği (kısa süreli hafıza için)
  const getSessionId = () => {
    const key = 'chat_session_id';
    let id = localStorage.getItem(key);
    if (!id) {
      try {
        // Tarayıcı destekliyse gerçek UUID kullan
        // @ts-ignore
        if (crypto && typeof crypto.randomUUID === 'function') {
          // @ts-ignore
          id = crypto.randomUUID();
        } else {
          id = Math.random().toString(36).slice(2) + Date.now().toString(36);
        }
      } catch (_) {
        id = Math.random().toString(36).slice(2) + Date.now().toString(36);
      }
      localStorage.setItem(key, id);
    }
    return id;
  };
  const sessionId = getSessionId();

  // Bağlantı adresleri (opsiyonel .env üzerinden yönetilebilir)
  const CRM_URL = (import.meta as any).env?.VITE_CRM_URL || 'https://www.alternatifcrm.com';

  // Sekme durum yardımcıları
  const isHome = activeTab === 'home';
  const isChat = activeTab === 'chat';

  // Header stili: her iki sekmede de aynı (gradient)
  const headerStyle: React.CSSProperties = {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: '1px solid rgba(255,255,255,0.25)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), 0 8px 24px rgba(0,0,0,0.18)'
  };

  // Yeni ana başlıklar
  const topics = [
    { id: 1, title: "🏛️ HUKUK VE GÖÇ HUKUKU", keywords: ["hukuk", "göç", "vize", "ikamet", "iltica"] },
    { id: 2, title: "👨‍💼 MESLEKİ EĞİTİM VE NİTELİKLER", keywords: ["meslek", "eğitim", "denklik", "kalfalık", "ustalık"] },
    { id: 3, title: "💼 İŞ VE ÇALIŞMA HAYATI", keywords: ["iş", "çalışma", "sözleşme", "meslek"] },
    { id: 4, title: "🏠 YERLEŞİM VE YAŞAM", keywords: ["anmeldung", "adres", "dil", "sosyal güvenlik"] },
    { id: 5, title: "💰 MALİ KONULAR", keywords: ["maaş", "harç", "ücret", "masraf", "euro"] },
    { id: 6, title: "🌍 ÜLKE BAZLI BİLGİLER", keywords: ["almanya", "ingiltere", "ab", "scale-up"] },
    { id: 7, title: "📋 SÜREÇ VE PROSEDÜRLER", keywords: ["başvuru", "evrak", "onay", "süre"] },
    { id: 8, title: "🎯 ÖZEL DURUMLAR", keywords: ["yaş", "dil seviyesi", "özel", "durum"] }
  ];

  // Kategoriye göre kısa bilgilendirme mesajları
  const topicIntros: Record<string, string> = {
    "🏛️ HUKUK VE GÖÇ HUKUKU":
      "AB Mavi Kart, 81a hızlandırılmış ön onay ve Fırsat Kartı gibi vizelerde; ayrıca çalışma izni ve yerleşim izninde mevzuata uygun başvuru dosyaları hazırlıyoruz. Blog içeriklerimizde derlenen güncel eşik değerler ve ilgili §18a/§18b/§19c/§20a/§81a maddeleri ışığında, dosyanız için en doğru stratejiyi birlikte belirliyoruz. İltica ve sığınma başvurularında da hak ve yükümlülükleri netleştiriyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "👨‍💼 MESLEKİ EĞİTİM VE NİTELİKLER":
      "Ön lisans ve meslek lisesi diplomaları ile ustalık–kalfalık belgelerinizi inceleyerek IHK/HWK/Bezirksregierung süreçlerinde doğru denklik yolunu belirliyoruz. Kaynaklarımızdaki örnek vakalar ve resmi gerekliliklere dayanarak tam/kısmi denklik ya da denklik tamamlama adımlarını, süre ve belge planlamasıyla birlikte yönetiyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "💼 İŞ VE ÇALIŞMA HAYATI":
      "Tır şoförlüğü, inşaat ustalığı, kasaplık, aşçılık ve elektrikçilik gibi aranan mesleklerde iş teklifi edinme, sözleşme kontrolü ve maaş eşiği uygunluğunu birlikte kontrol ediyoruz. Agentur für Arbeit onayları, çalışma vizesi ve oturum izinlerinde blog verilerimizden derlenen şartlara göre net bir yol haritası sunuyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "🏠 YERLEŞİM VE YAŞAM":
      "Anmeldung (adres kaydı) ve Wohnungsgeberbestätigung’dan dil gereksinimleri ve sosyal güvenlik kayıtlarına kadar yerleşim adımlarını pratik kontrol listeleriyle yönetiyoruz. Kalıcı ikamet için 36 ay ve B1 gibi eşikleri, kaynaklarımızdaki güncel örneklerle birlikte değerlendiriyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "💰 MALİ KONULAR":
      "Maaş şartlarının (ör. 48.300€ ve bottleneck alanlarında 43.759,80€) profilinize etkisini açıklıyor; 81a ön onay, vize ve oturum kartı harçlarıyla denklik–tercüme maliyetlerini netleştiriyoruz. Tüm rakamları blog yazılarımızdaki güncel bilgilerle karşılaştırıp gerçekçi bir bütçe–takvim çıkarıyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "🌍 ÜLKE BAZLI BİLGİLER":
      "Ana odağımız Almanya olmakla birlikte, içeriklerimizden derlenen bilgilerle İngiltere’nin Scale-up vizesi ve AB ülkelerinin temel koşullarını karşılaştırıyoruz. Profilinize göre artı–eksi yönleri sade bir dille aktararak en uygun yolu birlikte seçiyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "📋 SÜREÇ VE PROSEDÜRLER":
      "Vize ve denklik başvurularında belge hazırlığı, tercüme, randevu ve kurum yazışmalarını adım adım planlıyoruz. Kaynaklarımızda yer alan ortalama süreler ve beklenen kontrolleri dikkate alarak Yabancılar Dairesi ile İş Ajansı süreçlerini daha öngörülebilir hale getiriyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
    "🎯 ÖZEL DURUMLAR":
      "45 yaş üstü maaş eşiği, dil seviyesi gereksinimleri veya niteliksiz iş deneyimi gibi özel durumlarda, içeriklerimizdeki örnekler ve güncel uygulamalar doğrultusunda izleyebileceğiniz alternatifleri sade bir dille anlatıyoruz. Profesyonel sürücüler gibi meslek odaklı profiller için uygulanabilir bir eylem planı oluşturuyoruz. Devam etmek isterseniz, bu konuyla ilgili sorunuzu yazabilirsiniz.",
  };

  // (Kaldırıldı) topicSubQuestions kullanılmıyordu

  // İltica özel konu başlıkları
  const ilticaTopics = [
    { id: 101, title: "İltica Başvuru Süreci", keywords: [] },
    { id: 102, title: "İltica Başvuru Belgeleri", keywords: [] },
    { id: 103, title: "Mülakat ve Değerlendirme", keywords: [] },
    { id: 104, title: "Geçici Koruma ve Haklar", keywords: [] },
    { id: 105, title: "Ret Sonrası İtiraz Yolları", keywords: [] }
  ];

  // API çağrılarını services/api.ts üzerinden yapıyoruz (VITE_API_BASE_URL kullanır)

  // Mesajlar değiştiğinde scroll'u en alta kaydır
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const askChatbot = async (overrideQuestion?: string) => {
    const effectiveQuestion = (overrideQuestion ?? question).trim();
    if (!effectiveQuestion) return;

    // Konu başlıklarını gizle ve chat sekmesine geç
    setShowTopics(false);
    setActiveTab('chat');

    // Kullanıcı mesajını ekle
    const userMessage: Message = {
      id: Date.now().toString(),
      text: effectiveQuestion,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    const currentQuestion = effectiveQuestion;
    if (!overrideQuestion) setQuestion('');

    try {
      // Müşteri hizmetlerine bağlanma niyeti algılama (yerel)
      const consultKeywords = [
        'müşteri hizmetleri', 'müsteri hizmetleri', 'müşteri hizmetlerine', 'danışman', 'danisman',
        'görüşmek istiyorum', 'iletişim', 'iletisim', 'whatsapp', 'wp', 'telefon', 'biri beni arasın', 'danışmana bağlan'
      ];
      const consultIntent = consultKeywords.some(k => effectiveQuestion.toLocaleLowerCase('tr').includes(k));
      if (consultIntent) {
        // Tek WhatsApp butonu göster, başlıkları kapat
        setConsultOnly(true);
        setShowTopics(false);
        setActionButtons([
          { text: 'Başvuru Danışmanı', type: 'whatsapp', url: 'https://wa.me/4920393318883' }
        ]);
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: 'Sizi hemen danışmanımıza yönlendiriyorum.<br/><br/>' +
                '<a href="https://wa.me/4920393318883" target="_blank" rel="noopener noreferrer" ' +
                'style="display:inline-flex;align-items:center;gap:8px;padding:8px 12px;background:transparent;color:#25D366;' +
                'border-radius:999px;text-decoration:none;font-weight:700;font-size:13px;border:1px solid #25D366">' +
                '<span style="font-size:18px">💬</span> WhatsApp\'tan Yaz' +
                '</a>',
          isUser: false,
          timestamp: new Date(),
          sources: []
        };
        setMessages(prev => [...prev, botMessage]);
        setLoading(false);
        return;
      }

      // Süreç/durum sorgulama niyeti algılama (CRM yönlendirme)
      const crmKeywords = [
        'sürecim', 'sürecimin', 'durumum', 'durumumu', 'ne aşamada', 'hangi aşamada', 'başvuru durumu',
        'başvurum', 'dosyam', 'takip etmek istiyorum', 'takip', 'crm', 'panel', 'müşteri paneli'
      ];
      const crmIntent = crmKeywords.some(k => effectiveQuestion.toLocaleLowerCase('tr').includes(k));
      if (crmIntent) {
        setConsultOnly(false);
        setShowTopics(false);
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text:
            'Başvurunuzun güncel durumunu anlık görmek için müşteri bilgilendirme sistemimizi kullanabilirsiniz. ' +
            'Dilerseniz CRM üzerinden, dilerseniz müşteri hizmetlerimize bağlanarak ulaşabilirsiniz.<br/><br/>' +
            `<a href="${CRM_URL}" target="_blank" rel="noopener noreferrer" ` +
            'style="display:inline-flex;align-items:center;gap:8px;padding:8px 12px;background:transparent;color:#2563EB;' +
            'border-radius:999px;text-decoration:none;font-weight:700;font-size:13px;border:1px solid #2563EB;margin-right:8px;">' +
            '<span style="font-size:18px">📊</span> Durumumu Görüntüle</a>' +
            '<a href="https://wa.me/4920393318883" target="_blank" rel="noopener noreferrer" ' +
            'style="display:inline-flex;align-items:center;gap:8px;padding:8px 12px;background:transparent;color:#25D366;' +
            'border-radius:999px;text-decoration:none;font-weight:700;font-size:13px;border:1px solid #25D366">' +
            '<span style="font-size:18px">💬</span> WhatsApp\'tan Yaz</a>',
          isUser: false,
          timestamp: new Date(),
          sources: []
        };
        setMessages(prev => [...prev, botMessage]);
        setLoading(false);
        return;
      }

      const result = await askApi({
        question: currentQuestion,
        model: 'groq',
        session_id: sessionId
      });
      const qLower = currentQuestion.toLocaleLowerCase('tr');
      const ilticaKeywords = ['iltica', 'sığınma', 'mülteci', 'siginma'];
      const ilticaIntent = ilticaKeywords.some(k => qLower.includes(k));
      
      // special_type: consultant → sadece WhatsApp butonu
      if (result.special_type === 'consultant') {
        const consultantMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: result.answer,
          isUser: false,
          timestamp: new Date(),
          sources: []
        };
        setMessages(prev => [...prev, consultantMessage]);
        setActionButtons(result.action_buttons || []);
        setConsultOnly(true);
        setShowTopics(false);
        return;
      }

      // special_type: eligibility → form butonu
      if (result.special_type === 'eligibility') {
        const eligibilityMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: result.answer,
          isUser: false,
          timestamp: new Date(),
          sources: result.source_links || []
        };
        setMessages(prev => [...prev, eligibilityMessage]);
        setActionButtons(result.action_buttons || []);
        // İltica niyeti varsa ileride açılacak başlıkları iltica modunda tutalım
        if (ilticaIntent) {
          setTopicsMode('iltica');
          setSuggestedQuestions([]); // İltica moduna geçerken önerilen soruları temizle
        }
        setShowTopics(false);
        return;
      }

      // no_info veya benzeri → kısa mesaj + 5 sn sonra başlıklar
      if (result.special_type === 'no_info' ||
          result.special_response ||
          result.answer.includes("Bu konuda kaynaklarımda bilgi yok")) {
        
        const consultantMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: result.answer || "Şu anda bu konu hakkında size detaylı bir bilgi veremiyorum. Dilerseniz danışmanlarımız ile iletişime geçebilirsiniz.",
          isUser: false,
          timestamp: new Date(),
          sources: result.source_links || []
        };
        
        setMessages(prev => [...prev, consultantMessage]);
        setActionButtons(result.action_buttons || []);
        setConsultOnly(false);
        // Kullanıcının bot cevabını okuyabilmesi için 5 sn gecikmeli göster
        setShowTopics(false);
        setTimeout(() => {
          setTopicsMode(ilticaIntent ? 'iltica' : 'generic');
          setShowTopics(true);
        }, 5000);
      } else {
        // Normal bot cevabını ekle
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: result.answer,
          isUser: false,
          timestamp: new Date(),
          sources: result.source_links
        };
        setMessages(prev => [...prev, botMessage]);
        setConsultOnly(false);
      }
    } catch (error) {
      console.error('Chatbot API hatası:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Üzgünüm, şu anda chatbot'a erişilemiyor. Lütfen daha sonra tekrar deneyin.",
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // WhatsApp benzeri textarea auto-resize
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  // Danışmana yönlendirme
  const handleConsultantRedirect = () => {
    // WhatsApp numarasını buradan değiştirebilirsiniz
    // Almanya formatı: 49 + telefon numarası (başında 0 olmadan)
    // Örnek: 491701234567 (Almanya için)
    window.open('https://wa.me/4920393318883', '_blank');
  };

  // Özel aksiyon butonları
  const handleActionButtonClick = (btn: ActionButton) => {
    const t = (btn.type || '').toLowerCase();
    if (t === 'skip_categories') {
      setShowTopics(false);
      setSuggestedQuestions([]);
      textareaRef.current?.focus();
      return;
    }
    if (btn.url) {
      window.open(btn.url, '_blank');
    }
  };

  // Konu başlığına tıklama
  const handleTopicClick = (topicTitle: string) => {
    // Başlığa tıklanınca kısa bilgilendirme mesajını bot mesajı olarak göster,
    // konu menüsünü kapat ve kullanıcıya yazma alanını bırak
    setSuggestedQuestions([]);
    setShowTopics(false);
    setActiveTab('chat');

    const info = topicIntros[topicTitle] || `${topicTitle} hakkında sorularınızı yazabilirsiniz.`;
    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: `${topicTitle}\n\n${info}`,
      isUser: false,
      timestamp: new Date(),
      sources: []
    };
    setMessages(prev => [...prev, botMessage]);
    // Yazma alanına odaklan
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const hasWhatsappButton = actionButtons && actionButtons.some(btn => (btn.type || '').toLowerCase() === 'whatsapp');

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: isOpen ? '400px' : '60px',
      height: isOpen ? '650px' : '60px',
      background: 'white',
      borderRadius: isOpen ? '20px' : '50%',
      boxShadow: isOpen
        ? '0 24px 64px rgba(0,0,0,0.20), 0 10px 28px rgba(0,0,0,0.12)'
        : '0 10px 30px rgba(0,0,0,0.16)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255,255,255,0.2)'
    }}>
      {/* Header - Her zaman görünür */}
      <div 
        style={{
          ...headerStyle,
          padding: isOpen ? '20px' : '15px',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: isOpen ? 'space-between' : 'center',
          alignItems: 'center',
          height: isOpen ? 'auto' : '60px',
          borderRadius: isOpen ? '19px 19px 0 0' : '50%',
          position: 'relative',
          overflow: 'hidden',
          backdropFilter: 'saturate(180%) blur(14px)',
          WebkitBackdropFilter: 'saturate(180%) blur(14px)'
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? (
          <>
            {/* (taşındı) Geri butonu */}
            {false && isChat && (
              <button
                onClick={(e) => { e.stopPropagation(); setActiveTab('home'); }}
                style={{
                  position: 'absolute',
                  left: 12,
                  top: isOpen ? 0 : 6,
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  border: '1px solid rgba(255,255,255,0.35)',
                  background: 'rgba(255,255,255,0.18)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
                aria-label="Geri"
              >
                ←
              </button>
            )}
            <div>
              <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '600', letterSpacing: '-0.5px' }}>
                💬 OktayChat
              </h4>
              <small style={{ opacity: 0.9, fontSize: '13px', fontWeight: '400', display: 'block' }}>
                Hukuk ve Göç Uzmanı AI Asistanı
              </small>
            </div>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.20)',
              border: '1px solid rgba(255,255,255,0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
            }}>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>−</span>
            </div>
          </>
        ) : (
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: '100%'
          }}>
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ fontSize: '14px' }}>💬</span>
            </div>
          </div>
        )}
      </div>

      {/* Content - Sadece açık olduğunda görünür */}
      {isOpen && (
        <>
          {/* HOME TAB */}
          {activeTab === 'home' && (
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '20px',
              background: 'linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)'
            }}>
              <h2 style={{ margin: '0 0 12px 0', fontSize: '22px', fontWeight: 800, letterSpacing: '-0.5px' }}>Bizimle sohbet edin!</h2>
              <div style={{
                background: 'white',
                borderRadius: '16px',
                padding: '16px',
                boxShadow: '0 24px 64px rgba(0,0,0,0.10), 0 8px 20px rgba(0,0,0,0.06)',
                border: '1px solid rgba(0,0,0,0.06)',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                  <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#eef2ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>💬</div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '14px' }}>Metin Desteği</div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>AI asistanı</div>
                  </div>
                </div>
                <div style={{ fontSize: '13px', color: '#374151' }}>Size en uygun bilgiyi bulmanız veya fiyat/koşullar hakkında kısa sorularınız için yardımcı olabilirim.</div>
                <button
                  onClick={() => setActiveTab('chat')}
                  style={{
                    marginTop: 12,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: 'none',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    fontWeight: 700,
                    width: '100%',
                    boxShadow: '0 8px 20px rgba(102, 126, 234, 0.35)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 12px 28px rgba(118, 75, 162, 0.35)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 8px 20px rgba(102, 126, 234, 0.35)';
                  }}
                >
                  Sohbete başla →
                </button>
              </div>

              {/* Kategori listesi */}
              <div style={{ fontWeight: 700, color: '#374151', marginBottom: 8 }}>Yardımcı olabileceğim konular:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {topics.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => handleTopicClick((topic as any).title)}
                    style={{
                      background: 'white',
                      border: '1px solid rgba(0,0,0,0.08)',
                      borderRadius: 12,
                      padding: '12px 14px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                      transition: 'all 0.25s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 10px 24px rgba(0,0,0,0.10)';
                      e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.35)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)';
                      e.currentTarget.style.borderColor = 'rgba(0,0,0,0.08)';
                    }}
                  >
                    <span style={{ fontSize: 13, color: '#111827', fontWeight: 600 }}>{(topic as any).title}</span>
                    <span style={{ fontSize: 16, color: '#6b7280' }}>➜</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* CHAT TAB */}
          {activeTab === 'chat' && (
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            background: 'linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            {/* Geri butonu (chat başlığının altında) */}
            <div style={{ marginBottom: 8 }}>
              <button
                onClick={() => setActiveTab('home')}
                style={{
                  padding: '6px 10px',
                  borderRadius: 999,
                  border: '1px solid rgba(255,255,255,0.35)',
                  background: 'rgba(255,255,255,0.25)',
                  color: '#111827',
                  fontSize: 12,
                  fontWeight: 600,
                  boxShadow: '0 4px 14px rgba(0,0,0,0.12)',
                  backdropFilter: 'saturate(180%) blur(12px)',
                  WebkitBackdropFilter: 'saturate(180%) blur(12px)'
                }}
              >
                ← Geri
              </button>
            </div>
            {messages.map((message) => (
              <div key={message.id} style={{
                display: 'flex',
                justifyContent: message.isUser ? 'flex-end' : 'flex-start',
                marginBottom: '10px'
              }}>
                <div style={{
                  maxWidth: '80%',
                  padding: '14px 18px',
                  borderRadius: message.isUser ? '20px 20px 6px 20px' : '20px 20px 20px 6px',
                  background: message.isUser ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'white',
                  color: message.isUser ? 'white' : '#2d3748',
                  boxShadow: message.isUser ? '0 4px 12px rgba(102, 126, 234, 0.3)' : '0 2px 8px rgba(0,0,0,0.08)',
                  border: message.isUser ? 'none' : '1px solid rgba(0,0,0,0.05)',
                  backdropFilter: 'blur(10px)',
                  position: 'relative'
                }}>
                  <div style={{
                    fontSize: '14px',
                    lineHeight: '1.4',
                    wordWrap: 'break-word'
                  }}>
                    <div dangerouslySetInnerHTML={{ 
                      __html: message.text
                        .replace(/\n/g, '<br/>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">$1</a>')
                    }} />
                  </div>
                  
                  {/* Timestamp */}
                  <div style={{
                    fontSize: '10px',
                    opacity: 0.7,
                    marginTop: '5px',
                    textAlign: 'right'
                  }}>
                    {formatTime(message.timestamp)}
                  </div>

                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div style={{
                      marginTop: '10px',
                      paddingTop: '8px',
                      borderTop: `1px solid ${message.isUser ? 'rgba(255,255,255,0.3)' : '#eee'}`,
                      fontSize: '11px'
                    }}>
                      <div style={{ marginBottom: '5px', fontWeight: 'bold' }}>
                        📚 Kaynaklar:
                      </div>
                      {message.sources.map((link, index) => (
                        <div key={index} style={{ marginBottom: '3px' }}>
                          <a 
                            href={link.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ 
                              color: message.isUser ? '#fff' : '#007bff', 
                              textDecoration: 'none',
                              fontSize: '10px'
                            }}
                          >
                            {link.title}
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Loading indicator */}
            {loading && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-start',
                marginBottom: '10px'
              }}>
                <div style={{
                  padding: '12px 15px',
                  borderRadius: '18px 18px 18px 5px',
                  background: 'white',
                  boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <div style={{
                    display: 'flex',
                    gap: '3px'
                  }}>
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#007bff',
                      animation: 'bounce 1.4s infinite ease-in-out both'
                    }}></div>
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#007bff',
                      animation: 'bounce 1.4s infinite ease-in-out both',
                      animationDelay: '0.16s'
                    }}></div>
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#007bff',
                      animation: 'bounce 1.4s infinite ease-in-out both',
                      animationDelay: '0.32s'
                    }}></div>
                  </div>
                  <span style={{ fontSize: '12px', color: '#666' }}>Düşünüyor...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          )}

          {/* (Removed) Yalnızca WhatsApp yönlendirme modu ek bloğu */}

          {/* Konu Başlıkları - Home dışına taşındı; chat sekmesinde asla gösterme */}
          {false && activeTab === 'chat' && showTopics && (
            <div style={{
              padding: '15px',
              background: '#f0f8ff',
              borderTop: '1px solid #e0e0e0',
              maxHeight: '360px',
              overflowY: 'auto',
              WebkitOverflowScrolling: 'touch',
              position: 'relative'
            }}>
              {/* Sağ üstte çarpı butonu */}
              <button
                onClick={() => {
                  setShowTopics(false);
                  setSuggestedQuestions([]);
                  textareaRef.current?.focus();
                }}
                style={{
                  position: 'absolute',
                  top: '10px',
                  right: '10px',
                  width: '32px',
                  height: '32px',
                  padding: '0',
                  background: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '50%',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 2px 8px rgba(239, 68, 68, 0.3)',
                  zIndex: 10
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'scale(1.1)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scale(1)';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(239, 68, 68, 0.3)';
                }}
              >
                ✕
              </button>

              {/* Özel aksiyon butonları */}
              {actionButtons.length > 0 && (
                <div style={{
                  display: 'flex',
                  flexWrap: consultOnly ? 'nowrap' : 'wrap',
                  gap: '8px',
                  marginBottom: '12px',
                  justifyContent: consultOnly ? 'flex-start' : 'flex-start'
                }}>
                  {actionButtons.map((btn, idx) => {
                    const t = (btn.type || '').toLowerCase();
                    const isLink = !!btn.url && t !== 'skip_categories';
                    
                    // skip_categories ve whatsapp butonlarını burada göstermeyelim
                    if (t === 'skip_categories' || t === 'whatsapp') {
                      return null;
                    }
                    
                    // Modern WhatsApp butonu (tek buton modu)
                    if (consultOnly && t === 'whatsapp') {
                      return (
                        <a
                          key={idx}
                          href={btn.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '10px 14px',
                            background: '#25D366',
                            color: 'white',
                            borderRadius: '999px',
                            textDecoration: 'none',
                            fontWeight: 700,
                            fontSize: '13px',
                            boxShadow: '0 6px 20px rgba(37, 211, 102, 0.3)'
                          }}
                        >
                          <span style={{ fontSize: '16px' }}>🟢</span>
                          Başvuru Danışmanı ile WhatsApp'tan Görüş
                        </a>
                      );
                    }
                    
                    // Diğer butonlar (link vb.)
                    const commonStyle: React.CSSProperties = {
                      padding: '8px 12px',
                      background: '#007bff',
                      color: 'white',
                      textDecoration: 'none',
                      borderRadius: '8px',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    };
                    
                    return isLink ? (
                      <a key={idx} href={btn.url} target="_blank" rel="noopener noreferrer" style={commonStyle}>
                        {btn.text}
                      </a>
                    ) : (
                      <button key={idx} onClick={() => handleActionButtonClick(btn)} style={commonStyle}>
                        {btn.text}
                      </button>
                    );
                  })}
                </div>
              )}
              <div style={{ marginBottom: '12px', fontSize: '15px', fontWeight: '600', color: '#4a5568', letterSpacing: '-0.3px' }}>
                {topicsMode === 'iltica' ? '📋 İltica ile ilgili başlıklar:' : '📋 Yardımcı olabileceğim konular:'}
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '8px',
                marginBottom: '15px',
                maxHeight: '280px',
                overflowY: 'auto',
                WebkitOverflowScrolling: 'touch'
              }}>
                {(topicsMode === 'iltica' ? ilticaTopics : topics).map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => handleTopicClick((topic as any).title)}
                    style={{
                      padding: '10px 14px',
                      background: 'white',
                      border: '1px solid rgba(102, 126, 234, 0.2)',
                      borderRadius: '16px',
                      fontSize: '12px',
                      color: '#667eea',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                      textAlign: 'center',
                      fontWeight: '500',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                      backdropFilter: 'blur(10px)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                      e.currentTarget.style.color = 'white';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'white';
                      e.currentTarget.style.color = '#667eea';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
                    }}
                  >
                    {topic.title}
                  </button>
                ))}
              </div>

              {suggestedQuestions.length > 0 && (
                <div style={{ marginTop: '8px', marginBottom: '12px' }}>
                  <div style={{ fontWeight: 600, marginBottom: '6px', color: '#333' }}>Önerilen sorular:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {suggestedQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => askChatbot(q)}
                        style={{
                          padding: '6px 10px',
                          background: '#fff',
                          border: '1px solid #ddd',
                          borderRadius: '14px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {!hasWhatsappButton && (
                <button
                  onClick={handleConsultantRedirect}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: '#25d366',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    marginTop: '8px',
                    marginBottom: '8px'
                  }}
                >
                  💬 Danışmanımızla WhatsApp'tan Konuş
                </button>
              )}
            </div>
          )}

          {/* Input (yalnızca chat sekmesinde) */}
          {activeTab === 'chat' && (
          <div style={{
            padding: '20px',
            background: 'white',
            borderTop: '1px solid rgba(0,0,0,0.05)',
            display: 'flex',
            gap: '12px',
            alignItems: 'flex-end',
            borderRadius: '0 0 20px 20px'
          }}>
            <textarea
              ref={textareaRef}
              value={question}
              onChange={handleTextareaChange}
              placeholder="Mesajınızı yazın..."
              style={{
                flex: 1,
                padding: '14px 18px',
                border: '1px solid rgba(0,0,0,0.1)',
                borderRadius: '24px',
                fontSize: '14px',
                outline: 'none',
                background: '#f8fafc',
                resize: 'none',
                minHeight: '20px',
                maxHeight: '120px',
                fontFamily: 'inherit',
                lineHeight: '1.5',
                transition: 'all 0.2s ease',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!loading && question.trim()) {
                    askChatbot();
                  }
                }
              }}
              rows={1}
            />
            <button
              onClick={() => askChatbot()}
              disabled={loading || !question.trim()}
              style={{
                padding: '12px',
                background: loading || !question.trim() ? '#e2e8f0' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '50%',
                cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                fontSize: '16px',
                width: '48px',
                height: '48px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.3s ease',
                flexShrink: 0,
                boxShadow: loading || !question.trim() ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.3)',
                transform: loading || !question.trim() ? 'none' : 'scale(1)'
              }}
            >
              {loading ? '⏳' : '➤'}
            </button>
          </div>
          )}
        </>
      )}

      {/* CSS Animation */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
};

export default ChatbotComponent;
