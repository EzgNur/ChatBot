"""
Model eğitimi scripti
Hazırlanan verilerle model eğitimi yapar
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


class ModelTrainer:
    def __init__(self):
        self.training_data = []
        self.model = None
        
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
    
    def prepare_fine_tuning_data(self) -> List[Dict]:
        """Fine-tuning için veri hazırla"""
        print("🔧 Fine-tuning verisi hazırlanıyor...")
        
        fine_tuning_data = []
        
        for example in self.training_data:
            # OpenAI fine-tuning formatı
            fine_tuning_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "Sen Oktay Özdemir'in blog yazılarından eğitilmiş bir hukuk ve göç uzmanı asistanısın. Türkçe olarak kısa ve net şekilde cevapla."
                    },
                    {
                        "role": "user", 
                        "content": example["question"]
                    },
                    {
                        "role": "assistant",
                        "content": example["answer"]
                    }
                ]
            }
            fine_tuning_data.append(fine_tuning_example)
        
        print(f"✅ {len(fine_tuning_data)} fine-tuning örneği hazırlandı")
        return fine_tuning_data
    
    def prepare_lora_data(self) -> List[Dict]:
        """LoRA eğitimi için veri hazırla"""
        print("🔧 LoRA eğitim verisi hazırlanıyor...")
        
        lora_data = []
        
        for example in self.training_data:
            # LoRA formatı
            lora_example = {
                "instruction": example["question"],
                "input": "",
                "output": example["answer"],
                "category": example.get("category", "general"),
                "difficulty": example.get("difficulty", "medium")
            }
            lora_data.append(lora_example)
        
        print(f"✅ {len(lora_data)} LoRA örneği hazırlandı")
        return lora_data
    
    def save_training_files(self, data: List[Dict], format_type: str):
        """Eğitim dosyalarını kaydet"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "fine_tuning":
            filename = f"fine_tuning_data_{timestamp}.jsonl"
        elif format_type == "lora":
            filename = f"lora_data_{timestamp}.json"
        else:
            filename = f"training_data_{timestamp}.json"
        
        output_path = os.path.join(PROJECT_ROOT, "data", "training", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if format_type == "fine_tuning":
            # JSONL formatı
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        else:
            # JSON formatı
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 {format_type} verisi kaydedildi: {filename}")
        return output_path
    
    def generate_training_commands(self, data_file: str):
        """Eğitim komutlarını oluştur"""
        print("📝 Eğitim komutları oluşturuluyor...")
        
        commands = {
            "openai_fine_tuning": f"""
# OpenAI Fine-tuning
openai api fine_tunes.create -t {data_file} -m gpt-3.5-turbo --suffix "alternativkraft"
            """,
            "huggingface_lora": f"""
# Hugging Face LoRA
python -m transformers.trainer \\
    --model_name_or_path microsoft/DialoGPT-medium \\
    --train_file {data_file} \\
    --output_dir ./trained_model \\
    --per_device_train_batch_size 4 \\
    --gradient_accumulation_steps 4 \\
    --num_train_epochs 3 \\
    --learning_rate 5e-5 \\
    --fp16 \\
    --save_steps 500 \\
    --eval_steps 500 \\
    --logging_steps 100
            """,
            "local_training": f"""
# Yerel eğitim (CPU/GPU)
python -c "
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer

# Model ve tokenizer yükle
model_name = 'microsoft/DialoGPT-medium'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Eğitim verisi yükle
with open('{data_file}', 'r') as f:
    data = json.load(f)

# Eğitim başlat
trainer = Trainer(
    model=model,
    train_dataset=data,
    tokenizer=tokenizer,
    args=TrainingArguments(
        output_dir='./trained_model',
        num_train_epochs=3,
        per_device_train_batch_size=4,
        learning_rate=5e-5,
        save_steps=500,
        logging_steps=100
    )
)
trainer.train()
"
            """
        }
        
        # Komutları dosyaya kaydet
        commands_file = os.path.join(PROJECT_ROOT, "data", "training", "training_commands.txt")
        with open(commands_file, 'w', encoding='utf-8') as f:
            f.write("# Model Eğitimi Komutları\n")
            f.write("# " + "="*50 + "\n\n")
            
            for name, command in commands.items():
                f.write(f"# {name.upper()}\n")
                f.write(command.strip() + "\n\n")
        
        print(f"📝 Eğitim komutları kaydedildi: {commands_file}")
        return commands_file


def main():
    parser = argparse.ArgumentParser(description="Model eğitimi")
    parser.add_argument("--data-file", type=str, required=True,
                        help="Eğitim verisi dosyası")
    parser.add_argument("--format", choices=["fine_tuning", "lora", "both"], 
                        default="both", help="Eğitim formatı")
    parser.add_argument("--generate-commands", action="store_true",
                        help="Eğitim komutlarını oluştur")
    
    args = parser.parse_args()
    
    trainer = ModelTrainer()
    
    # Eğitim verisini yükle
    if not trainer.load_training_data(args.data_file):
        return
    
    # Veri formatlarını hazırla
    if args.format in ["fine_tuning", "both"]:
        fine_tuning_data = trainer.prepare_fine_tuning_data()
        trainer.save_training_files(fine_tuning_data, "fine_tuning")
    
    if args.format in ["lora", "both"]:
        lora_data = trainer.prepare_lora_data()
        trainer.save_training_files(lora_data, "lora")
    
    # Eğitim komutlarını oluştur
    if args.generate_commands:
        trainer.generate_training_commands(args.data_file)
    
    print("\n🎯 Model eğitimi için hazırlık tamamlandı!")
    print("📚 Eğitim verileri: data/training/ klasöründe")
    print("🚀 Eğitim komutları: training_commands.txt dosyasında")


if __name__ == "__main__":
    main()
