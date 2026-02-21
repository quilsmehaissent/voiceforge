#!/usr/bin/env python3
"""
Qwen3-TTS Model Downloader
Downloads all Qwen3-TTS models to the local models directory.

Usage:
    python download_models.py [--token YOUR_HF_TOKEN]

Or set HF_TOKEN environment variable.
"""

import os
import sys
import argparse
from pathlib import Path

# Models to download
MODELS = [
    "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", 
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
]

def main():
    parser = argparse.ArgumentParser(description='Download Qwen3-TTS models')
    parser.add_argument('--token', type=str, help='HuggingFace token (or set HF_TOKEN env var)')
    parser.add_argument('--models-dir', type=str, default='./models', help='Directory to save models')
    args = parser.parse_args()
    
    # Get token
    token = args.token or os.environ.get('HF_TOKEN')
    
    if not token:
        print("⚠️  No HuggingFace token provided.")
        print("   Get a token from: https://huggingface.co/settings/tokens")
        print("\n   Then run one of:")
        print("   - python download_models.py --token YOUR_TOKEN")
        print("   - export HF_TOKEN=YOUR_TOKEN && python download_models.py")
        print("\n   Or login with: python -c 'from huggingface_hub import login; login()'")
        sys.exit(1)
    
    try:
        from huggingface_hub import snapshot_download, login
    except ImportError:
        print("Installing huggingface_hub...")
        os.system("pip install -U huggingface_hub")
        from huggingface_hub import snapshot_download, login
    
    # Login with token
    print(f"🔑 Logging in to HuggingFace...")
    login(token=token)
    
    models_dir = Path(args.models_dir)
    models_dir.mkdir(exist_ok=True)
    
    print(f"\n📥 Downloading {len(MODELS)} Qwen3-TTS models to {models_dir.absolute()}")
    print("=" * 60)
    
    for model_name in MODELS:
        local_name = model_name.split('/')[-1]
        local_dir = models_dir / local_name
        
        print(f"\n{'=' * 60}")
        print(f"📦 Model: {model_name}")
        print(f"📁 Target: {local_dir}")
        
        try:
            snapshot_download(
                repo_id=model_name,
                local_dir=str(local_dir),
                token=token,
            )
            print(f"✅ Successfully downloaded: {local_name}")
        except Exception as e:
            print(f"❌ Failed to download {local_name}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("🎉 Download complete!")
    print("\nDownloaded models:")
    for model_name in MODELS:
        local_name = model_name.split('/')[-1]
        local_dir = models_dir / local_name
        if local_dir.exists():
            size = sum(f.stat().st_size for f in local_dir.rglob('*') if f.is_file())
            size_gb = size / (1024**3)
            print(f"  ✅ {local_name}: {size_gb:.2f} GB")
        else:
            print(f"  ❌ {local_name}: Not downloaded")

if __name__ == "__main__":
    main()
