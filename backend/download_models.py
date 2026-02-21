#!/usr/bin/env python3
"""
VoiceForge Model Downloader

Downloads Qwen3-TTS models from HuggingFace.
Run this script to download all required models before starting the server.

Usage:
    python download_models.py [--small]
    
Options:
    --small     Download smaller 0.6B models instead of 1.7B models
"""

import os
import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Download Qwen3-TTS models")
    parser.add_argument("--small", action="store_true", 
                       help="Download smaller 0.6B models instead of 1.7B")
    parser.add_argument("--models-dir", default="./models",
                       help="Directory to save models")
    args = parser.parse_args()
    
    # Set custom cache to avoid permission issues
    models_dir = Path(args.models_dir).absolute()
    cache_dir = models_dir / ".hf_cache"
    os.environ["HF_HOME"] = str(cache_dir)
    os.environ["HF_HUB_DISABLE_XET"] = "1"  # Disable XET for more reliable downloads
    
    from huggingface_hub import snapshot_download
    
    # Define models to download
    if args.small:
        models = {
            "Qwen/Qwen3-TTS-Tokenizer-12Hz": "Qwen3-TTS-Tokenizer-12Hz",
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice": "Qwen3-TTS-12Hz-0.6B-CustomVoice",
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base": "Qwen3-TTS-12Hz-0.6B-Base",
        }
        print("🔽 Downloading SMALL (0.6B) models (~5GB total)...")
    else:
        models = {
            "Qwen/Qwen3-TTS-Tokenizer-12Hz": "Qwen3-TTS-Tokenizer-12Hz",
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice": "Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign": "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base": "Qwen3-TTS-12Hz-1.7B-Base",
        }
        print("🔽 Downloading FULL (1.7B) models (~22GB total)...")
    
    print(f"📁 Models will be saved to: {models_dir}")
    print("-" * 60)
    
    for repo_id, local_name in models.items():
        local_dir = models_dir / local_name
        
        if (local_dir / "model.safetensors").exists():
            print(f"✅ {local_name} already exists, skipping...")
            continue
        
        print(f"\n⏬ Downloading {repo_id}...")
        try:
            snapshot_download(
                repo_id,
                local_dir=str(local_dir),
                resume_download=True,
            )
            print(f"✅ {local_name} downloaded successfully!")
        except Exception as e:
            print(f"❌ Failed to download {repo_id}: {e}")
            print("   Try running the script again to resume.")
            return 1
    
    print("\n" + "=" * 60)
    print("🎉 All models downloaded successfully!")
    print("=" * 60)
    print("\nYou can now start the VoiceForge server:")
    print("  cd ..")
    print("  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
