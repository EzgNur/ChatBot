"""
Entegre edilmiş hibrit sistemi test etme scripti
"""

import sys
import os
from datetime import datetime
import json

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from backend.core.chatbot.bot import FreeChatBot


def test_integrated_system():
    """Entegre edilmiş sistemi test et"""
    print("🚀 Entegre edilmiş hibrit sistem testi başlıyor...")
    
    # Chatbot oluştur
    chatbot = FreeChatBot()
    
    # Vectorstore'u yükle
    vs_path = os.path.join(PROJECT_ROOT, "data", "vectorstore")
    if not chatbot.load_vectorstore(vs_path):
        print("❌ Vectorstore yüklenemedi")
        return
    
    # Eğitilmiş modeli yükle
    model_path = os.path.join(PROJECT_ROOT, "trained_rag_lora_model")
    if not chatbot.load_trained_model(model_path):
        print("❌ Eğitilmiş model yüklenemedi")
        return
    
    print("✅ Hibrit sistem hazır!")
    
    # Test soruları
    test_questions = [
        "AB Mavi Kart için 2025 maaş şartı nedir?",
        "81A ön onay vizesi nedir?",
        "Anmeldung nedir ve neden önemli?"
    ]
    
    results = []
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_questions)}: {question}")
        
        try:
            response = chatbot.ask_groq(question)
            print(f"✅ Yanıt: {response['answer'][:100]}...")
            print(f"📊 Model: {response.get('model', 'Unknown')}")
            print(f"⏱️ Süre: {response.get('response_time', 'Unknown')}")
            
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
    output_file = f"integrated_system_test_{timestamp}.json"
    output_path = os.path.join(PROJECT_ROOT, output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "test_info": {
                "timestamp": timestamp,
                "total_tests": len(test_questions),
                "system_type": "integrated_hybrid"
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Test sonuçları kaydedildi: {output_file}")
    
    # Özet
    successful_tests = sum(1 for r in results if r["success"])
    print(f"\n📊 Entegre Sistem Test Özeti:")
    print(f"   Toplam test: {len(test_questions)}")
    print(f"   Başarılı test: {successful_tests}")
    print(f"   Başarı oranı: {successful_tests/len(test_questions)*100:.1f}%")
    
    return results


if __name__ == "__main__":
    test_integrated_system()
