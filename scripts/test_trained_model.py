"""
Eğitilmiş RAG + LoRA modelini test etme scripti
"""

import sys
import os
import json
import torch
from datetime import datetime
from typing import List, Dict, Any
import argparse

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from backend.core.chatbot.bot import FreeChatBot


class TrainedModelTester:
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
                torch_dtype=torch.float32,  # CPU için float32
                device_map="cpu"  # CPU kullan
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
    
    def test_single_question(self, question: str) -> Dict:
        """Tek bir soruyu test et"""
        print(f"\n🔍 Test sorusu: {question}")
        
        results = {
            "question": question,
            "trained_model_response": "",
            "rag_response": "",
            "comparison": {}
        }
        
        # 1. Eğitilmiş model testi
        try:
            print("🤖 Eğitilmiş model testi...")
            inputs = self.tokenizer.encode(
                f"<|endoftext|>{question}<|endoftext|>",
                return_tensors="pt"
            )
            
            with torch.no_grad():
                outputs = self.trained_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 100,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            trained_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            results["trained_model_response"] = trained_response
            print(f"✅ Eğitilmiş model yanıtı: {trained_response[:100]}...")
            
        except Exception as e:
            print(f"❌ Eğitilmiş model hatası: {e}")
            results["trained_model_response"] = f"Hata: {str(e)}"
        
        # 2. RAG sistemi testi
        try:
            print("🔍 RAG sistemi testi...")
            rag_response = self.rag_chatbot.ask_groq(question)
            results["rag_response"] = rag_response.get("answer", str(rag_response))
            print(f"✅ RAG yanıtı: {results['rag_response'][:100]}...")
            
        except Exception as e:
            print(f"❌ RAG sistemi hatası: {e}")
            results["rag_response"] = f"Hata: {str(e)}"
        
        # 3. Karşılaştırma
        results["comparison"] = {
            "trained_model_length": len(results["trained_model_response"]),
            "rag_length": len(results["rag_response"]),
            "both_working": "Hata" not in results["trained_model_response"] and "Hata" not in results["rag_response"]
        }
        
        return results
    
    def run_comprehensive_test(self, test_questions: List[str] = None):
        """Kapsamlı test çalıştır"""
        if not test_questions:
            test_questions = [
                "AB Mavi Kart için 2025 maaş şartı nedir?",
                "81A ön onay vizesi nedir?",
                "Anmeldung nedir ve neden önemli?",
                "Almanya'da çalışma izni nasıl alınır?",
                "Mavi Kart başvuru süreci nasıl işler?"
            ]
        
        print("🚀 Kapsamlı test başlıyor...")
        
        # Modelleri yükle
        if not self.load_trained_model():
            return
        
        if not self.load_rag_system():
            return
        
        # Testleri çalıştır
        results = []
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(test_questions)}")
            result = self.test_single_question(question)
            results.append(result)
        
        # Sonuçları kaydet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"trained_model_test_results_{timestamp}.json"
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
        
        print(f"\n💾 Test sonuçları kaydedildi: {output_file}")
        
        # Özet
        working_tests = sum(1 for r in results if r["comparison"]["both_working"])
        print(f"\n📊 Test Özeti:")
        print(f"   Toplam test: {len(test_questions)}")
        print(f"   Başarılı test: {working_tests}")
        print(f"   Başarı oranı: {working_tests/len(test_questions)*100:.1f}%")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Eğitilmiş model testi")
    parser.add_argument("--model-path", type=str, default="./trained_rag_lora_model",
                        help="Eğitilmiş model yolu")
    parser.add_argument("--questions", type=str, nargs="+", default=None,
                        help="Test soruları")
    
    args = parser.parse_args()
    
    tester = TrainedModelTester(args.model_path)
    tester.run_comprehensive_test(args.questions)


if __name__ == "__main__":
    main()
