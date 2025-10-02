"""
Kapsamlı model test scripti
Vectorstore'daki tüm verileri test eder ve detaylı analiz sağlar
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import argparse

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vectorstore.build_store import OptimizedVectorStoreBuilder
from backend.core.chatbot.bot import FreeChatBot


class ComprehensiveModelTester:
    def __init__(self, test_file: str = "tests/test_set.json"):
        self.test_file = test_file
        self.builder = OptimizedVectorStoreBuilder()
        self.chatbot = None
        self.results = []
        
    def load_test_cases(self) -> List[Dict]:
        """Test case'lerini yükle"""
        try:
            with open(self.test_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Test dosyası yüklenemedi: {e}")
            return []
    
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
    
    def test_single_question(self, test_case: Dict) -> Dict:
        """Tek bir soruyu test et"""
        question = test_case["question"]
        expected_keywords = test_case.get("expected_keywords", [])
        expected_urls = test_case.get("expected_urls", [])
        category = test_case.get("category", "Unknown")
        difficulty = test_case.get("difficulty", "medium")
        test_type = test_case.get("test_type", "general")
        
        print(f"\n🔍 Test: {question}")
        print(f"📂 Kategori: {category} | Zorluk: {difficulty} | Tip: {test_type}")
        
        start_time = time.time()
        
        try:
            # GROQ chatbot'a soru sor
            response_dict = self.chatbot.ask_groq(question)
            response = response_dict.get("answer", str(response_dict))
            response_time = time.time() - start_time
            
            # Yanıtı analiz et
            analysis = self.analyze_response(response, expected_keywords, expected_urls)
            
            result = {
                "question": question,
                "category": category,
                "difficulty": difficulty,
                "test_type": test_type,
                "response": response,
                "response_time": response_time,
                "expected_keywords": expected_keywords,
                "expected_urls": expected_urls,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Test hatası: {e}")
            return {
                "question": question,
                "category": category,
                "difficulty": difficulty,
                "test_type": test_type,
                "response": f"Hata: {str(e)}",
                "response_time": 0,
                "expected_keywords": expected_keywords,
                "expected_urls": expected_urls,
                "analysis": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_response(self, response: str, expected_keywords: List[str], expected_urls: List[str]) -> Dict:
        """Yanıtı analiz et"""
        analysis = {
            "keyword_matches": [],
            "keyword_missed": [],
            "url_matches": [],
            "url_missed": [],
            "response_length": len(response),
            "has_specific_info": False,
            "has_urls": False,
            "confidence_score": 0
        }
        
        response_lower = response.lower()
        
        # Anahtar kelime analizi
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                analysis["keyword_matches"].append(keyword)
            else:
                analysis["keyword_missed"].append(keyword)
        
        # URL analizi
        for url in expected_urls:
            if url in response:
                analysis["url_matches"].append(url)
            else:
                analysis["url_missed"].append(url)
        
        # Genel analiz
        analysis["has_specific_info"] = len(analysis["keyword_matches"]) > 0
        analysis["has_urls"] = len(analysis["url_matches"]) > 0
        
        # Güven skoru hesapla
        keyword_score = len(analysis["keyword_matches"]) / len(expected_keywords) if expected_keywords else 0
        url_score = len(analysis["url_matches"]) / len(expected_urls) if expected_urls else 0
        analysis["confidence_score"] = (keyword_score + url_score) / 2 if (expected_keywords or expected_urls) else 0
        
        return analysis
    
    def run_comprehensive_test(self, max_tests: int = None) -> Dict:
        """Kapsamlı test çalıştır"""
        print("🚀 Kapsamlı model testi başlıyor...")
        
        # Test case'lerini yükle
        test_cases = self.load_test_cases()
        if not test_cases:
            return {"error": "Test case'leri yüklenemedi"}
        
        if max_tests:
            test_cases = test_cases[:max_tests]
        
        print(f"📋 {len(test_cases)} test case yüklendi")
        
        # Chatbot'u başlat
        if not self.initialize_chatbot():
            return {"error": "Chatbot başlatılamadı"}
        
        # Testleri çalıştır
        results = []
        start_time = time.time()
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(test_cases)}")
            
            result = self.test_single_question(test_case)
            results.append(result)
            
            # Kısa özet
            analysis = result["analysis"]
            expected_keywords = test_case.get("expected_keywords", [])
            expected_urls = test_case.get("expected_urls", [])
            print(f"✅ Anahtar kelime eşleşmesi: {len(analysis['keyword_matches'])}/{len(expected_keywords)}")
            print(f"🔗 URL eşleşmesi: {len(analysis['url_matches'])}/{len(expected_urls)}")
            print(f"📊 Güven skoru: {analysis['confidence_score']:.2f}")
            print(f"⏱️  Yanıt süresi: {result['response_time']:.2f}s")
        
        total_time = time.time() - start_time
        
        # Genel analiz
        summary = self.generate_summary(results, total_time)
        
        return {
            "summary": summary,
            "detailed_results": results,
            "test_metadata": {
                "total_tests": len(test_cases),
                "total_time": total_time,
                "average_response_time": total_time / len(test_cases),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def generate_summary(self, results: List[Dict], total_time: float) -> Dict:
        """Test sonuçlarının özetini oluştur"""
        if not results:
            return {"error": "Test sonucu bulunamadı"}
        
        # Genel istatistikler
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["analysis"]["confidence_score"] > 0.5)
        avg_confidence = sum(r["analysis"]["confidence_score"] for r in results) / total_tests
        avg_response_time = sum(r["response_time"] for r in results) / total_tests
        
        # Kategori analizi
        categories = {}
        for result in results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "successful": 0, "avg_confidence": 0}
            categories[cat]["total"] += 1
            if result["analysis"]["confidence_score"] > 0.5:
                categories[cat]["successful"] += 1
            categories[cat]["avg_confidence"] += result["analysis"]["confidence_score"]
        
        for cat in categories:
            categories[cat]["avg_confidence"] /= categories[cat]["total"]
            categories[cat]["success_rate"] = categories[cat]["successful"] / categories[cat]["total"]
        
        # Zorluk analizi
        difficulties = {}
        for result in results:
            diff = result["difficulty"]
            if diff not in difficulties:
                difficulties[diff] = {"total": 0, "successful": 0, "avg_confidence": 0}
            difficulties[diff]["total"] += 1
            if result["analysis"]["confidence_score"] > 0.5:
                difficulties[diff]["successful"] += 1
            difficulties[diff]["avg_confidence"] += result["analysis"]["confidence_score"]
        
        for diff in difficulties:
            difficulties[diff]["avg_confidence"] /= difficulties[diff]["total"]
            difficulties[diff]["success_rate"] = difficulties[diff]["successful"] / difficulties[diff]["total"]
        
        # En iyi ve en kötü performanslar
        best_tests = sorted(results, key=lambda x: x["analysis"]["confidence_score"], reverse=True)[:3]
        worst_tests = sorted(results, key=lambda x: x["analysis"]["confidence_score"])[:3]
        
        return {
            "overall_stats": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests,
                "average_confidence": avg_confidence,
                "average_response_time": avg_response_time,
                "total_time": total_time
            },
            "category_performance": categories,
            "difficulty_performance": difficulties,
            "best_performing_tests": [
                {
                    "question": t["question"],
                    "category": t["category"],
                    "confidence_score": t["analysis"]["confidence_score"]
                } for t in best_tests
            ],
            "worst_performing_tests": [
                {
                    "question": t["question"],
                    "category": t["category"],
                    "confidence_score": t["analysis"]["confidence_score"]
                } for t in worst_tests
            ]
        }
    
    def save_results(self, results: Dict, output_file: str = None):
        """Sonuçları kaydet"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Test sonuçları kaydedildi: {output_file}")
        return output_file
    
    def print_summary(self, summary: Dict):
        """Özeti yazdır"""
        print("\n" + "="*80)
        print("📊 KAPSAMLI MODEL TEST SONUÇLARI")
        print("="*80)
        
        stats = summary["overall_stats"]
        print(f"\n🎯 GENEL İSTATİSTİKLER:")
        print(f"   Toplam test: {stats['total_tests']}")
        print(f"   Başarılı test: {stats['successful_tests']}")
        print(f"   Başarı oranı: {stats['success_rate']:.1%}")
        print(f"   Ortalama güven skoru: {stats['average_confidence']:.2f}")
        print(f"   Ortalama yanıt süresi: {stats['average_response_time']:.2f}s")
        print(f"   Toplam süre: {stats['total_time']:.2f}s")
        
        print(f"\n📂 KATEGORİ PERFORMANSI:")
        for cat, data in summary["category_performance"].items():
            print(f"   {cat}: {data['success_rate']:.1%} başarı ({data['avg_confidence']:.2f} güven)")
        
        print(f"\n🎚️ ZORLUK PERFORMANSI:")
        for diff, data in summary["difficulty_performance"].items():
            print(f"   {diff}: {data['success_rate']:.1%} başarı ({data['avg_confidence']:.2f} güven)")
        
        print(f"\n🏆 EN İYİ PERFORMANS:")
        for test in summary["best_performing_tests"]:
            print(f"   {test['category']}: {test['confidence_score']:.2f} - {test['question'][:50]}...")
        
        print(f"\n⚠️  EN DÜŞÜK PERFORMANS:")
        for test in summary["worst_performing_tests"]:
            print(f"   {test['category']}: {test['confidence_score']:.2f} - {test['question'][:50]}...")


def main():
    parser = argparse.ArgumentParser(description="Kapsamlı model test aracı")
    parser.add_argument("--test-file", default="tests/test_set.json", help="Test dosyası yolu")
    parser.add_argument("--max-tests", type=int, default=None, help="Maksimum test sayısı")
    parser.add_argument("--output", default=None, help="Sonuç dosyası yolu")
    parser.add_argument("--quick", action="store_true", help="Hızlı test (sadece 5 test)")
    
    args = parser.parse_args()
    
    if args.quick:
        args.max_tests = 5
    
    tester = ComprehensiveModelTester(args.test_file)
    results = tester.run_comprehensive_test(args.max_tests)
    
    if "error" in results:
        print(f"❌ Test hatası: {results['error']}")
        return
    
    # Sonuçları kaydet
    output_file = tester.save_results(results, args.output)
    
    # Özeti yazdır
    tester.print_summary(results["summary"])
    
    print(f"\n✅ Test tamamlandı! Detaylı sonuçlar: {output_file}")


if __name__ == "__main__":
    main()
