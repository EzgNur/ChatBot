"""
Geliştirilmiş model test scripti - Daha esnek ve gerçekçi değerlendirme
"""

import sys
import os
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any
import argparse

# Proje kökünü PYTHONPATH'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vectorstore.build_store import OptimizedVectorStoreBuilder
from backend.core.chatbot.bot import FreeChatBot


class ImprovedModelTester:
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
    
    def improved_analyze_response(self, response: str, expected_keywords: List[str], expected_urls: List[str], question: str) -> Dict:
        """Geliştirilmiş yanıt analizi"""
        analysis = {
            "keyword_matches": [],
            "keyword_missed": [],
            "url_matches": [],
            "url_missed": [],
            "response_length": len(response),
            "has_specific_info": False,
            "has_urls": False,
            "confidence_score": 0,
            "semantic_matches": [],
            "context_quality": 0,
            "completeness_score": 0
        }
        
        response_lower = response.lower()
        question_lower = question.lower()
        
        # 1. Anahtar kelime analizi (daha esnek)
        for keyword in expected_keywords:
            keyword_lower = keyword.lower()
            
            # Tam eşleşme
            if keyword_lower in response_lower:
                analysis["keyword_matches"].append(keyword)
            # Kısmi eşleşme (anahtar kelimenin %70'i)
            elif len(keyword_lower) > 3 and any(keyword_lower[:int(len(keyword_lower)*0.7)] in response_lower for _ in [1]):
                analysis["keyword_matches"].append(f"{keyword} (kısmi)")
            # Semantik eşleşme
            elif self.semantic_match(keyword_lower, response_lower):
                analysis["semantic_matches"].append(keyword)
            else:
                analysis["keyword_missed"].append(keyword)
        
        # 2. URL analizi
        for url in expected_urls:
            if url in response:
                analysis["url_matches"].append(url)
            else:
                analysis["url_missed"].append(url)
        
        # 3. İçerik kalitesi analizi
        analysis["context_quality"] = self.analyze_context_quality(response, question)
        
        # 4. Tamamlama skoru
        analysis["completeness_score"] = self.analyze_completeness(response, question)
        
        # 5. Genel analiz
        analysis["has_specific_info"] = len(analysis["keyword_matches"]) > 0 or len(analysis["semantic_matches"]) > 0
        analysis["has_urls"] = len(analysis["url_matches"]) > 0
        
        # 6. Geliştirilmiş güven skoru hesaplama
        keyword_score = len(analysis["keyword_matches"]) / len(expected_keywords) if expected_keywords else 0
        semantic_score = len(analysis["semantic_matches"]) / len(expected_keywords) if expected_keywords else 0
        url_score = len(analysis["url_matches"]) / len(expected_urls) if expected_urls else 0
        
        # Ağırlıklı skor hesaplama
        analysis["confidence_score"] = (
            keyword_score * 0.4 +           # Anahtar kelimeler %40
            semantic_score * 0.3 +          # Semantik eşleşmeler %30
            url_score * 0.1 +               # URL'ler %10
            analysis["context_quality"] * 0.1 +  # İçerik kalitesi %10
            analysis["completeness_score"] * 0.1  # Tamamlama %10
        )
        
        return analysis
    
    def semantic_match(self, keyword: str, response: str) -> bool:
        """Semantik eşleşme kontrolü"""
        # Sayısal değerler için
        if keyword.replace(",", "").replace(".", "").isdigit():
            # Yanıtta sayısal değer var mı?
            numbers = re.findall(r'\d+[.,]?\d*', response)
            return len(numbers) > 0
        
        # Anahtar kavramlar için
        semantic_mappings = {
            "maaş": ["ücret", "gelir", "brüt", "net"],
            "vize": ["oturum", "ikamet", "izin"],
            "başvuru": ["müracaat", "talep", "istek"],
            "belge": ["doküman", "evrak", "kağıt"],
            "süre": ["zaman", "dönem", "periyot"],
            "şart": ["koşul", "gereklilik", "kriter"]
        }
        
        for concept, synonyms in semantic_mappings.items():
            if concept in keyword:
                return any(syn in response for syn in synonyms)
        
        return False
    
    def analyze_context_quality(self, response: str, question: str) -> float:
        """İçerik kalitesi analizi"""
        score = 0.0
        
        # Uzunluk kontrolü
        if len(response) > 100:
            score += 0.2
        if len(response) > 300:
            score += 0.2
        
        # Yapısal kalite
        if "•" in response or "-" in response or "1." in response:
            score += 0.2  # Liste formatı
        
        if ":" in response:
            score += 0.1  # Açıklama formatı
        
        # Soruya özel yanıt
        question_words = question.lower().split()
        response_words = response.lower().split()
        common_words = set(question_words) & set(response_words)
        if len(common_words) > 2:
            score += 0.3
        
        return min(score, 1.0)
    
    def analyze_completeness(self, response: str, question: str) -> float:
        """Tamamlama skoru analizi"""
        score = 0.0
        
        # Soru türüne göre analiz
        if "nedir" in question.lower() or "nelerdir" in question.lower():
            if len(response.split()) > 20:
                score += 0.5
            if ":" in response or "•" in response:
                score += 0.3
            if any(word in response.lower() for word in ["şart", "koşul", "gereklilik"]):
                score += 0.2
        
        elif "nasıl" in question.lower():
            if any(word in response.lower() for word in ["adım", "süreç", "işlem"]):
                score += 0.5
            if ":" in response or "•" in response:
                score += 0.3
            if len(response.split()) > 30:
                score += 0.2
        
        elif "ne kadar" in question.lower() or "kaç" in question.lower():
            if re.search(r'\d+', response):
                score += 0.5
            if any(word in response.lower() for word in ["euro", "€", "tl", "yıl", "ay", "gün"]):
                score += 0.3
            if len(response.split()) > 15:
                score += 0.2
        
        return min(score, 1.0)
    
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
            
            # Geliştirilmiş yanıt analizi
            analysis = self.improved_analyze_response(response, expected_keywords, expected_urls, question)
            
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
    
    def run_improved_test(self, max_tests: int = None) -> Dict:
        """Geliştirilmiş test çalıştır"""
        print("🚀 Geliştirilmiş model testi başlıyor...")
        
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
            
            # Geliştirilmiş özet
            analysis = result["analysis"]
            expected_keywords = test_case.get("expected_keywords", [])
            expected_urls = test_case.get("expected_urls", [])
            
            print(f"✅ Anahtar kelime eşleşmesi: {len(analysis['keyword_matches'])}/{len(expected_keywords)}")
            print(f"🧠 Semantik eşleşme: {len(analysis['semantic_matches'])}")
            print(f"🔗 URL eşleşmesi: {len(analysis['url_matches'])}/{len(expected_urls)}")
            print(f"📊 İçerik kalitesi: {analysis['context_quality']:.2f}")
            print(f"📈 Tamamlama skoru: {analysis['completeness_score']:.2f}")
            print(f"🎯 Geliştirilmiş güven skoru: {analysis['confidence_score']:.2f}")
            print(f"⏱️  Yanıt süresi: {result['response_time']:.2f}s")
        
        total_time = time.time() - start_time
        
        # Genel analiz
        summary = self.generate_improved_summary(results, total_time)
        
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
    
    def generate_improved_summary(self, results: List[Dict], total_time: float) -> Dict:
        """Geliştirilmiş test sonuçlarının özetini oluştur"""
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
                categories[cat] = {
                    "total": 0, "successful": 0, "avg_confidence": 0,
                    "avg_context_quality": 0, "avg_completeness": 0
                }
            categories[cat]["total"] += 1
            if result["analysis"]["confidence_score"] > 0.5:
                categories[cat]["successful"] += 1
            categories[cat]["avg_confidence"] += result["analysis"]["confidence_score"]
            categories[cat]["avg_context_quality"] += result["analysis"]["context_quality"]
            categories[cat]["avg_completeness"] += result["analysis"]["completeness_score"]
        
        for cat in categories:
            categories[cat]["avg_confidence"] /= categories[cat]["total"]
            categories[cat]["avg_context_quality"] /= categories[cat]["total"]
            categories[cat]["avg_completeness"] /= categories[cat]["total"]
            categories[cat]["success_rate"] = categories[cat]["successful"] / categories[cat]["total"]
        
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
            "improvement_suggestions": self.generate_improvement_suggestions(results)
        }
    
    def generate_improvement_suggestions(self, results: List[Dict]) -> List[str]:
        """İyileştirme önerileri oluştur"""
        suggestions = []
        
        # Düşük performanslı kategoriler
        low_performance = [r for r in results if r["analysis"]["confidence_score"] < 0.3]
        if low_performance:
            categories = [r["category"] for r in low_performance]
            suggestions.append(f"Düşük performans kategorileri: {', '.join(set(categories))}")
        
        # URL eksikliği
        no_urls = [r for r in results if not r["analysis"]["url_matches"]]
        if len(no_urls) > len(results) * 0.5:
            suggestions.append("URL'ler yanıtlarda eksik - Vectorstore'da URL bilgileri kontrol edin")
        
        # İçerik kalitesi
        low_quality = [r for r in results if r["analysis"]["context_quality"] < 0.3]
        if low_quality:
            suggestions.append("İçerik kalitesi düşük - Prompt template'i iyileştirin")
        
        # Tamamlama skoru
        incomplete = [r for r in results if r["analysis"]["completeness_score"] < 0.3]
        if incomplete:
            suggestions.append("Yanıtlar eksik - Daha detaylı bilgi için chunk sayısını artırın")
        
        return suggestions
    
    def save_results(self, results: Dict, output_file: str = None):
        """Sonuçları kaydet"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"improved_test_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Geliştirilmiş test sonuçları kaydedildi: {output_file}")
        return output_file
    
    def print_improved_summary(self, summary: Dict):
        """Geliştirilmiş özeti yazdır"""
        print("\n" + "="*80)
        print("📊 GELİŞTİRİLMİŞ MODEL TEST SONUÇLARI")
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
            print(f"      İçerik kalitesi: {data['avg_context_quality']:.2f}")
            print(f"      Tamamlama: {data['avg_completeness']:.2f}")
        
        print(f"\n💡 İYİLEŞTİRME ÖNERİLERİ:")
        for suggestion in summary["improvement_suggestions"]:
            print(f"   • {suggestion}")


def main():
    parser = argparse.ArgumentParser(description="Geliştirilmiş model test aracı")
    parser.add_argument("--test-file", default="tests/test_set.json", help="Test dosyası yolu")
    parser.add_argument("--max-tests", type=int, default=None, help="Maksimum test sayısı")
    parser.add_argument("--output", default=None, help="Sonuç dosyası yolu")
    parser.add_argument("--quick", action="store_true", help="Hızlı test (sadece 5 test)")
    
    args = parser.parse_args()
    
    if args.quick:
        args.max_tests = 5
    
    tester = ImprovedModelTester(args.test_file)
    results = tester.run_improved_test(args.max_tests)
    
    if "error" in results:
        print(f"❌ Test hatası: {results['error']}")
        return
    
    # Sonuçları kaydet
    output_file = tester.save_results(results, args.output)
    
    # Özeti yazdır
    tester.print_improved_summary(results["summary"])
    
    print(f"\n✅ Geliştirilmiş test tamamlandı! Detaylı sonuçlar: {output_file}")


if __name__ == "__main__":
    main()
