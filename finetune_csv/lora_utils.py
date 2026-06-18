"""LoRA utilities for Kronos predictor fine-tuning."""
import os
from peft import LoraConfig, get_peft_model, PeftModel


def apply_lora(model, config):
    """Wrap model with LoRA adapters. Returns PeftModel."""
    lora_config = LoraConfig(
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        target_modules=config.lora_target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
    )

    peft_model = get_peft_model(model, lora_config)

    # Log trainable params
    trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in peft_model.parameters())
    print(f"LoRA adapter applied: {trainable:,} trainable / {total:,} total params ({100*trainable/total:.2f}%)")

    return peft_model


def save_lora(peft_model, save_dir):
    """Save LoRA adapter weights (lightweight, ~25 MB)."""
    peft_model.save_pretrained(save_dir)


def merge_and_save_lora_offline(base_model_path, adapter_path, output_path):
    """Merge LoRA adapter weights back into base model and save as standard model on CPU."""
    from model import Kronos
    
    print(f"Offline merging LoRA weights from {adapter_path} into base model {base_model_path}...")
    
    # Load base model on CPU
    base_model_cpu = Kronos.from_pretrained(base_model_path)
    
    # Wrap in PEFT and load adapter on CPU
    peft_model_cpu = PeftModel.from_pretrained(base_model_cpu, adapter_path)
    
    # Merge weights and unload adapter
    merged_model = peft_model_cpu.merge_and_unload()
    
    # Save the merged model to output path
    os.makedirs(output_path, exist_ok=True)
    merged_model.save_pretrained(output_path)
    print(f"Successfully merged and saved standard model to {output_path}")
