"""
Model eğitimi için veri hazırlama scripti
Mevcut verilerden eğitim verisi oluşturur
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import argparse

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vectorstore.build_store import OptimizedVectorStoreBuilder
from backend.core.chatbot.bot import FreeChatBot


class TrainingDataPreparer:
    def __init__(self):
        self.chatbot = None
        self.training_data = []
        
    def initialize_chatbot(self):
        """Chatbot'u başlat"""
        try:
            print("🤖 GROQ Chatbot başlatılıyor...")
            self.chatbot = FreeChatBot()
            
            # Vectorstore'u yükle
            print("🔄 Vectorstore yükleniyor...")
            vs_path = os.path.join(PROJECT_ROOT, "data", "vectorstore")
            if self.chatbot.load_vectorstore(vs_path):
                print("✅ GROQ Chatbot başlatıldı ve vectorstore yüklendi")
                return True
            else:
                print("❌ Vectorstore yüklenemedi")
                return False
        except Exception as e:
            print(f"❌ Chatbot başlatılamadı: {e}")
            return False
    
    def generate_training_examples(self, num_examples: int = 100) -> List[Dict]:
        """Eğitim örnekleri oluştur"""
        print(f"📚 {num_examples} eğitim örneği oluşturuluyor...")
        
        # Örnek sorular ve kategoriler
        question_templates = [
            # Mavi Kart
            "AB Mavi Kart için {year} maaş şartı nedir?",
            "Mavi Kart başvuru süreci nasıl işler?",
            "Mavi Kart için hangi belgeler gerekli?",
            "Mavi Kart süresi ne kadar?",
            
            # 81A Vizesi
            "81A ön onay vizesi nedir?",
            "81A vizesi için gereken belgeler nelerdir?",
            "81A vizesi başvuru süreci nasıl?",
            "81A vizesi süresi ne kadar?",
            
            # Adres Kaydı
            "Anmeldung nedir ve neden önemli?",
            "Anmeldung için hangi belgeler gerekli?",
            "Anmeldung ne kadar sürede yapılmalı?",
            "Anmeldung yapmazsam ne olur?",
            
            # Genel Göç
            "Almanya'ya göç etmek için ne yapmalıyım?",
            "Almanya'da çalışma izni nasıl alınır?",
            "Almanya'da oturum izni türleri nelerdir?",
            "Almanya'da aile birleşimi nasıl yapılır?"
        ]
        
        training_examples = []
        
        for i in range(num_examples):
            # Rastgele soru seç
            import random
            template = random.choice(question_templates)
            
            # Yıl değişkeni için
            if "{year}" in template:
                year = random.choice(["2024", "2025", "2026"])
                question = template.format(year=year)
            else:
                question = template
            
            # Chatbot'a sor
            try:
                response = self.chatbot.ask_groq(question)
                answer = response.get("answer", "")
                sources = response.get("sources", [])
                
                if answer and len(answer) > 50:  # Yeterli uzunlukta yanıt
                    training_examples.append({
                        "question": question,
                        "answer": answer,
                        "sources": sources,
                        "category": self._infer_category(question),
                        "difficulty": self._infer_difficulty(question),
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"⚠️ Soru işlenemedi: {question} - {e}")
                continue
        
        print(f"✅ {len(training_examples)} eğitim örneği oluşturuldu")
        return training_examples
    
    def _infer_category(self, question: str) -> str:
        """Sorudan kategori çıkar"""
        qlower = question.lower()
        if "mavi kart" in qlower:
            return "Mavi Kart"
        elif "81a" in qlower or "ön onay" in qlower:
            return "81A Vizesi"
        elif "anmeldung" in qlower or "adres" in qlower:
            return "Adres Kaydı"
        elif "göç" in qlower or "çalışma" in qlower:
            return "Genel Göç"
        else:
            return "Diğer"
    
    def _infer_difficulty(self, question: str) -> str:
        """Sorudan zorluk seviyesi çıkar"""
        qlower = question.lower()
        if any(word in qlower for word in ["nasıl", "neden", "hangi", "ne zaman"]):
            return "medium"
        elif any(word in qlower for word in ["detay", "açıkla", "süreç"]):
            return "hard"
        else:
            return "easy"
    
    def save_training_data(self, examples: List[Dict], filename: str = None):
        """Eğitim verisini kaydet"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_data_{timestamp}.json"
        
        output_path = os.path.join(PROJECT_ROOT, "data", "training", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(examples, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Eğitim verisi kaydedildi: {filename}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Model eğitimi için veri hazırlama")
    parser.add_argument("--num-examples", type=int, default=100,
                        help="Oluşturulacak eğitim örneği sayısı")
    parser.add_argument("--output", type=str, default=None,
                        help="Çıktı dosyası adı")
    
    args = parser.parse_args()
    
    preparer = TrainingDataPreparer()
    
    if not preparer.initialize_chatbot():
        print("❌ Chatbot başlatılamadı")
        return
    
    # Eğitim verisi oluştur
    examples = preparer.generate_training_examples(args.num_examples)
    
    if examples:
        # Kaydet
        output_path = preparer.save_training_data(examples, args.output)
        
        # İstatistikler
        categories = {}
        difficulties = {}
        
        for ex in examples:
            cat = ex["category"]
            diff = ex["difficulty"]
            
            categories[cat] = categories.get(cat, 0) + 1
            difficulties[diff] = difficulties.get(diff, 0) + 1
        
        print("\n📊 Eğitim Verisi İstatistikleri:")
        print(f"   Toplam örnek: {len(examples)}")
        print(f"   Kategoriler: {categories}")
        print(f"   Zorluk seviyeleri: {difficulties}")
        print(f"   Dosya: {output_path}")
    else:
        print("❌ Hiç eğitim örneği oluşturulamadı")


if __name__ == "__main__":
    main()
