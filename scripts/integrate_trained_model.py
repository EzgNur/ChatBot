"""
Eğitilmiş modeli chatbot sistemine entegre etme scripti
"""

import sys
import os
import json
import torch
from datetime import datetime
from typing import Dict, Any
import argparse

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from backend.core.chatbot.bot import FreeChatBot


class TrainedModelIntegrator:
    def __init__(self, model_path: str = "./trained_rag_lora_model"):
        self.model_path = model_path
        self.base_model = None
        self.tokenizer = None
        self.trained_model = None
        self.rag_chatbot = None
        
    def load_trained_model(self):
        """Eğitilmiş modeli yükle"""
        try:
            print("🔄 Eğitilmiş model yükleniyor...")
            
            # Base model ve tokenizer yükle
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/DialoGPT-medium",
                torch_dtype=torch.float32,
                device_map="cpu"
            )
            
            # LoRA modeli yükle
            self.trained_model = PeftModel.from_pretrained(
                self.base_model, 
                self.model_path
            )
            
            print("✅ Eğitilmiş model yüklendi")
            return True
            
        except Exception as e:
            print(f"❌ Model yüklenemedi: {e}")
            return False
    
    def load_rag_system(self):
        """RAG sistemini yükle"""
        try:
            print("🔄 RAG sistemi yükleniyor...")
            self.rag_chatbot = FreeChatBot()
            
            # Vectorstore'u yükle
            vs_path = os.path.join(PROJECT_ROOT, "data", "vectorstore")
            if self.rag_chatbot.load_vectorstore(vs_path):
                print("✅ RAG sistemi yüklendi")
                return True
            else:
                print("❌ RAG sistemi yüklenemedi")
                return False
                
        except Exception as e:
            print(f"❌ RAG sistemi yüklenemedi: {e}")
            return False
    
    def create_hybrid_chatbot(self):
        """Hibrit chatbot oluştur (RAG + Eğitilmiş Model)"""
        print("🔧 Hibrit chatbot oluşturuluyor...")
        
        class HybridChatBot(FreeChatBot):
            def __init__(self, trained_model, tokenizer):
                super().__init__()
                self.trained_model = trained_model
                self.tokenizer = tokenizer
                self.use_trained_model = True
                
            def ask_hybrid(self, question: str) -> Dict:
                """Hibrit yanıt üret (RAG + Eğitilmiş Model)"""
                try:
                    # 1. RAG sistemi ile bağlam al
                    rag_response = self.ask_groq(question)
                    rag_context = rag_response.get("answer", "")
                    
                    # 2. Eğitilmiş model ile yanıt üret
                    if self.use_trained_model:
                        # Eğitilmiş model için input hazırla
                        context_prompt = f"Bağlam: {rag_context}\nSoru: {question}\nYanıt:"
                        
                        inputs = self.tokenizer.encode(
                            f"<|endoftext|>{context_prompt}<|endoftext|>",
                            return_tensors="pt"
                        )
                        
                        with torch.no_grad():
                            outputs = self.trained_model.generate(
                                inputs,
                                max_length=inputs.shape[1] + 150,
                                num_return_sequences=1,
                                temperature=0.7,
                                do_sample=True,
                                pad_token_id=self.tokenizer.eos_token_id
                            )
                        
                        trained_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                        
                        # Eğitilmiş model yanıtını temizle
                        if "Yanıt:" in trained_response:
                            trained_response = trained_response.split("Yanıt:")[-1].strip()
                        
                        # Hibrit yanıt oluştur
                        hybrid_answer = f"{trained_response}\n\n---\n\n📚 Kaynak: {rag_response.get('sources', [])}"
                        
                        return {
                            "answer": hybrid_answer,
                            "sources": rag_response.get("sources", []),
                            "response_time": rag_response.get("response_time", "0s"),
                            "chunks_used": rag_response.get("chunks_used", 0),
                            "timestamp": datetime.now().isoformat(),
                            "model_type": "hybrid_rag_trained"
                        }
                    else:
                        # Sadece RAG kullan
                        return rag_response
                        
                except Exception as e:
                    print(f"⚠️ Hibrit yanıt hatası: {e}")
                    # Fallback: sadece RAG
                    return rag_response
        
        # Hibrit chatbot oluştur
        hybrid_bot = HybridChatBot(self.trained_model, self.tokenizer)
        
        # RAG sistemini kopyala
        hybrid_bot.groq_client = self.rag_chatbot.groq_client
        hybrid_bot.vectorstore = self.rag_chatbot.vectorstore
        hybrid_bot.embeddings = self.rag_chatbot.embeddings
        
        print("✅ Hibrit chatbot oluşturuldu")
        return hybrid_bot
    
    def test_hybrid_system(self, test_questions: list = None):
        """Hibrit sistemi test et"""
        if not test_questions:
            test_questions = [
                "AB Mavi Kart için 2025 maaş şartı nedir?",
                "81A ön onay vizesi nedir?",
                "Anmeldung nedir ve neden önemli?"
            ]
        
        print("🧪 Hibrit sistem testi başlıyor...")
        
        # Hibrit chatbot oluştur
        hybrid_bot = self.create_hybrid_chatbot()
        
        results = []
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(test_questions)}: {question}")
            
            try:
                response = hybrid_bot.ask_hybrid(question)
                print(f"✅ Hibrit yanıt: {response['answer'][:100]}...")
                results.append({
                    "question": question,
                    "response": response,
                    "success": True
                })
            except Exception as e:
                print(f"❌ Test hatası: {e}")
                results.append({
                    "question": question,
                    "response": {"error": str(e)},
                    "success": False
                })
        
        # Sonuçları kaydet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"hybrid_system_test_{timestamp}.json"
        output_path = os.path.join(PROJECT_ROOT, output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "test_info": {
                    "timestamp": timestamp,
                    "model_path": self.model_path,
                    "total_tests": len(test_questions)
                },
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Hibrit test sonuçları kaydedildi: {output_file}")
        
        # Özet
        successful_tests = sum(1 for r in results if r["success"])
        print(f"\n📊 Hibrit Test Özeti:")
        print(f"   Toplam test: {len(test_questions)}")
        print(f"   Başarılı test: {successful_tests}")
        print(f"   Başarı oranı: {successful_tests/len(test_questions)*100:.1f}%")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Eğitilmiş model entegrasyonu")
    parser.add_argument("--model-path", type=str, default="./trained_rag_lora_model",
                        help="Eğitilmiş model yolu")
    parser.add_argument("--test", action="store_true",
                        help="Hibrit sistemi test et")
    
    args = parser.parse_args()
    
    integrator = TrainedModelIntegrator(args.model_path)
    
    # Modelleri yükle
    if not integrator.load_trained_model():
        return
    
    if not integrator.load_rag_system():
        return
    
    # Hibrit sistemi test et
    if args.test:
        integrator.test_hybrid_system()
    
    print("\n🎯 Entegrasyon tamamlandı!")
    print("💡 Hibrit chatbot artık RAG + Eğitilmiş Model kullanıyor")


if __name__ == "__main__":
    main()
