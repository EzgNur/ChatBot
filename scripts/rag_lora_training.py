"""
RAG + LoRA eğitim scripti
Hugging Face LoRA ile model eğitimi yapar
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

from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import warnings
warnings.filterwarnings("ignore")


class RAGLoRATrainer:
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.training_data = []
        
    def load_training_data(self, data_file: str) -> bool:
        """Eğitim verisini yükle"""
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.training_data = json.load(f)
            print(f"✅ {len(self.training_data)} eğitim örneği yüklendi")
            return True
        except Exception as e:
            print(f"❌ Eğitim verisi yüklenemedi: {e}")
            return False
    
    def prepare_lora_config(self):
        """LoRA konfigürasyonu hazırla"""
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,  # Rank
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["c_attn", "c_proj", "w1", "w2"]  # DialoGPT için
        )
        return lora_config
    
    def prepare_model_and_tokenizer(self):
        """Model ve tokenizer'ı hazırla"""
        print("🔄 Model ve tokenizer yükleniyor...")
        
        try:
            # Tokenizer yükle
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Model yükle
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # LoRA konfigürasyonu uygula
            lora_config = self.prepare_lora_config()
            self.model = get_peft_model(self.model, lora_config)
            
            print("✅ Model ve tokenizer hazırlandı")
            return True
            
        except Exception as e:
            print(f"❌ Model yüklenemedi: {e}")
            return False
    
    def prepare_dataset(self) -> Dataset:
        """Eğitim veri setini hazırla"""
        print("🔧 Eğitim veri seti hazırlanıyor...")
        
        def format_instruction(example):
            """Soru-cevap formatını dönüştür"""
            instruction = example["instruction"]
            output = example["output"]
            
            # DialoGPT formatı: <|endoftext|>soru<|endoftext|>cevap<|endoftext|>
            text = f"<|endoftext|>{instruction}<|endoftext|>{output}<|endoftext|>"
            return {"text": text}
        
        # Veri setini formatla
        formatted_data = [format_instruction(ex) for ex in self.training_data]
        
        # Hugging Face Dataset oluştur
        dataset = Dataset.from_list(formatted_data)
        
        # Tokenize
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt"
            )
        
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        print(f"✅ {len(tokenized_dataset)} tokenized örnek hazırlandı")
        return tokenized_dataset
    
    def train_model(self, output_dir: str = "./trained_model"):
        """Model eğitimini başlat"""
        print("🚀 LoRA eğitimi başlıyor...")
        
        # Veri setini hazırla
        dataset = self.prepare_dataset()
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=2,  # Küçük batch size
            gradient_accumulation_steps=4,
            learning_rate=5e-5,
            warmup_steps=100,
            logging_steps=10,
            save_steps=500,
            eval_strategy="no",  # Güncellenmiş parametre
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_pin_memory=False,
            fp16=torch.cuda.is_available(),  # GPU varsa fp16 kullan
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )
        
        # Eğitimi başlat
        print("🎯 Eğitim başlıyor...")
        trainer.train()
        
        # Modeli kaydet
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)
        
        print(f"✅ Eğitim tamamlandı! Model kaydedildi: {output_dir}")
        return True
    
    def test_trained_model(self, test_question: str = "AB Mavi Kart için 2025 maaş şartı nedir?"):
        """Eğitilmiş modeli test et"""
        print(f"🧪 Test sorusu: {test_question}")
        
        # Test için modeli hazırla
        inputs = self.tokenizer.encode(
            f"<|endoftext|>{test_question}<|endoftext|>",
            return_tensors="pt"
        )
        
        # Yanıt üret
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Yanıtı decode et
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"🤖 Model yanıtı: {response}")
        
        return response


def main():
    parser = argparse.ArgumentParser(description="RAG + LoRA eğitimi")
    parser.add_argument("--data-file", type=str, required=True,
                        help="Eğitim verisi dosyası")
    parser.add_argument("--model-name", type=str, default="microsoft/DialoGPT-medium",
                        help="Base model adı")
    parser.add_argument("--output-dir", type=str, default="./trained_model",
                        help="Çıktı dizini")
    parser.add_argument("--test", action="store_true",
                        help="Eğitim sonrası test yap")
    
    args = parser.parse_args()
    
    # Trainer oluştur
    trainer = RAGLoRATrainer(args.model_name)
    
    # Eğitim verisini yükle
    if not trainer.load_training_data(args.data_file):
        return
    
    # Model ve tokenizer'ı hazırla
    if not trainer.prepare_model_and_tokenizer():
        return
    
    # Model eğitimini başlat
    if trainer.train_model(args.output_dir):
        print("🎉 RAG + LoRA eğitimi başarıyla tamamlandı!")
        
        # Test yap
        if args.test:
            trainer.test_trained_model()
    
    print("\n📊 Eğitim Özeti:")
    print(f"   Model: {args.model_name}")
    print(f"   Eğitim örnekleri: {len(trainer.training_data)}")
    print(f"   Çıktı dizini: {args.output_dir}")
    print(f"   LoRA parametreleri: r=16, alpha=32, dropout=0.1")


if __name__ == "__main__":
    main()
