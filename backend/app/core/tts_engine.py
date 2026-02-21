"""
VoiceForge TTS Engine - Qwen3-TTS Integration
Provides text-to-speech functionality using Qwen3-TTS models.
Supports: Preset Voices, Voice Design, and Voice Cloning.
"""

import os
import io
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import torch
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    CUSTOM_VOICE = "custom_voice"
    VOICE_DESIGN = "voice_design"
    BASE = "base"
    CUSTOM_VOICE_SMALL = "custom_voice_small"
    BASE_SMALL = "base_small"


@dataclass
class VoicePreset:
    """Configuration for a preset voice."""
    speaker: str
    instruct: str
    description: str


class QwenTTSEngine:
    """
    Main TTS Engine using Qwen3-TTS models.
    """
    
    # Model identifiers on HuggingFace
    MODELS = {
        ModelType.CUSTOM_VOICE: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        ModelType.VOICE_DESIGN: "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        ModelType.BASE: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        ModelType.CUSTOM_VOICE_SMALL: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        ModelType.BASE_SMALL: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    }
    
    # Local model directory names
    LOCAL_MODEL_NAMES = {
        ModelType.CUSTOM_VOICE: "Qwen3-TTS-12Hz-1.7B-CustomVoice",
        ModelType.VOICE_DESIGN: "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        ModelType.BASE: "Qwen3-TTS-12Hz-1.7B-Base",
        ModelType.CUSTOM_VOICE_SMALL: "Qwen3-TTS-12Hz-0.6B-CustomVoice",
        ModelType.BASE_SMALL: "Qwen3-TTS-12Hz-0.6B-Base",
    }

    def __init__(self, use_small_models: bool = False, models_dir: Optional[str] = None):
        """
        Initialize the TTS Engine.
        """
        self.use_small_models = use_small_models
        self._device = None
        self._dtype = None
        
        # Set models directory - check multiple locations
        if models_dir:
            self.models_dir = os.path.abspath(models_dir)
        else:
            # Try to find models directory relative to the project
            possible_paths = [
                os.path.join(os.getcwd(), "models"),
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"),
                os.path.join(os.path.dirname(__file__), "..", "..", "models"),
            ]
            self.models_dir = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.isdir(abs_path):
                    self.models_dir = abs_path
                    break
            if self.models_dir is None:
                self.models_dir = os.path.join(os.getcwd(), "models")
        
        logger.info(f"[VoiceForge] Models directory: {self.models_dir}")
        
        # Lazy-loaded models
        self._models: Dict[ModelType, Any] = {
            ModelType.CUSTOM_VOICE: None,
            ModelType.VOICE_DESIGN: None,
            ModelType.BASE: None,
            ModelType.CUSTOM_VOICE_SMALL: None,
            ModelType.BASE_SMALL: None,
        }
        
        # Track model loading status
        self._model_load_errors: Dict[ModelType, Optional[str]] = {}
        
        # Voice cloning prompt cache (for reusable prompts)
        self._clone_prompt_cache: Dict[str, Any] = {}
        
        # Initialize device and dtype
        self._init_device()
        
        # Define preset voices
        self.presets: Dict[str, VoicePreset] = {
            "Deep Male": VoicePreset(
                speaker="Ryan",
                instruct="Speak in a deep, calm, authoritative tone.",
                description="A deep, commanding male voice"
            ),
            "Energetic Female": VoicePreset(
                speaker="Vivian",
                instruct="Speak with enthusiasm, energy, and excitement.",
                description="A vibrant, energetic female voice"
            ),
            "Raspy Wizard": VoicePreset(
                speaker="Ryan",
                instruct="Speak like a wise old wizard with a raspy, mysterious voice.",
                description="An aged, mystical voice"
            ),
            "Soft Whisper": VoicePreset(
                speaker="Vivian",
                instruct="Speak softly and gently, almost whispering.",
                description="A soft, intimate whisper"
            ),
            "News Anchor": VoicePreset(
                speaker="Ryan",
                instruct="Speak clearly and professionally like a television news anchor.",
                description="Professional broadcast voice"
            ),
            "Cheerful Assistant": VoicePreset(
                speaker="Vivian",
                instruct="Speak in a friendly, helpful, and cheerful manner.",
                description="Warm and approachable assistant"
            ),
            "Dramatic Narrator": VoicePreset(
                speaker="Ryan",
                instruct="Speak with dramatic flair, building tension and atmosphere.",
                description="Cinematic narrator voice"
            ),
            "Calm Meditation": VoicePreset(
                speaker="Vivian",
                instruct="Speak slowly, calmly, and peacefully, suitable for meditation.",
                description="Peaceful, relaxing voice"
            ),
        }
        
        logger.info(f"[VoiceForge] TTS Engine initialized on {self.device}")

    def _init_device(self) -> None:
        """Detect and configure the best available device."""
        # Check environment variable override
        env_device = os.environ.get("VOICEFORGE_DEVICE", "").lower()
        if env_device == "cpu":
            self._device = "cpu"
            self._dtype = torch.float32
            logger.info("[VoiceForge] Device forced to CPU")
            return

        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            self._device = "mps"
            self._dtype = torch.float32  # MPS works best with float32
            logger.info("[VoiceForge] Using Apple MPS acceleration")
        elif torch.cuda.is_available():
            self._device = "cuda:0"
            self._dtype = torch.bfloat16  # CUDA can use bfloat16
            logger.info(f"[VoiceForge] Using CUDA: {torch.cuda.get_device_name(0)}")
        else:
            self._device = "cpu"
            self._dtype = torch.float32
            logger.warning("[VoiceForge] Using CPU - this will be slow!")

    @property
    def device(self) -> str:
        """Get the current device."""
        return self._device

    @property
    def dtype(self) -> torch.dtype:
        """Get the current dtype."""
        return self._dtype

    def _get_model_id(self, model_type: ModelType) -> str:
        """
        Get the appropriate model ID or local path based on configuration.
        Checks for local models first, then falls back to HuggingFace.
        """
        local_name = self.LOCAL_MODEL_NAMES.get(model_type)
        
        # Check for local model first
        if local_name and self.models_dir:
            local_path = os.path.join(self.models_dir, local_name)
            model_file = os.path.join(local_path, "model.safetensors")
            if os.path.exists(model_file):
                logger.info(f"[VoiceForge] Found local model: {local_path}")
                return local_path
        
        # Fall back to HuggingFace model ID
        model_id = self.MODELS.get(model_type)
        
        if model_id is None:
            # Fallback logic if specific type not found
            logger.error(f"[VoiceForge] No model ID found for {model_type}")
            raise ValueError(f"Unknown model type: {model_type}")
        
        logger.info(f"[VoiceForge] Will download from HuggingFace: {model_id}")
        return model_id

    def _load_model(self, model_type: ModelType) -> Any:
        """
        Load a model with proper error handling.
        
        Args:
            model_type: The type of model to load
            
        Returns:
            The loaded model instance
            
        Raises:
            RuntimeError: If model loading fails
        """
        from qwen_tts import Qwen3TTSModel
        
        model_id = self._get_model_id(model_type)
        logger.info(f"[VoiceForge] Loading {model_type.value} model: {model_id}")
        
        try:
            # Build model kwargs
            model_kwargs = {
                "device_map": self.device,
                "dtype": self.dtype,
            }
            
            # Add FlashAttention on CUDA if available
            if self.device.startswith("cuda"):
                try:
                    import flash_attn
                    model_kwargs["attn_implementation"] = "flash_attention_2"
                    logger.info("[VoiceForge] Using FlashAttention 2")
                except ImportError:
                    logger.info("[VoiceForge] FlashAttention not available, using standard attention")
            elif self.device == "mps":
                # Use SDPA (Scaled Dot Product Attention) for Mac/MPS
                # This often fixes memory/performance issues
                model_kwargs["attn_implementation"] = "sdpa"
                logger.info("[VoiceForge] Using SDPA (Scaled Dot Product Attention) for MPS")
            
            model = Qwen3TTSModel.from_pretrained(model_id, **model_kwargs)
            
            logger.info(f"[VoiceForge] Successfully loaded {model_type.value} model")
            self._model_load_errors[model_type] = None
            return model
            
        except Exception as e:
            error_msg = f"Failed to load {model_type.value} model: {str(e)}"
            logger.error(f"[VoiceForge] {error_msg}")
            self._model_load_errors[model_type] = error_msg
            raise RuntimeError(error_msg) from e

    @property
    def custom_voice_model(self) -> Any:
        """Lazily load and return the CustomVoice model (1.7B)."""
        if self._models[ModelType.CUSTOM_VOICE] is None:
            self._models[ModelType.CUSTOM_VOICE] = self._load_model(ModelType.CUSTOM_VOICE)
        return self._models[ModelType.CUSTOM_VOICE]
    
    @property
    def custom_voice_small_model(self) -> Any:
        """Lazily load and return the CustomVoice Small model (0.6B)."""
        if self._models[ModelType.CUSTOM_VOICE_SMALL] is None:
            self._models[ModelType.CUSTOM_VOICE_SMALL] = self._load_model(ModelType.CUSTOM_VOICE_SMALL)
        return self._models[ModelType.CUSTOM_VOICE_SMALL]

    @property
    def voice_design_model(self) -> Any:
        """Lazily load and return the VoiceDesign model."""
        if self._models[ModelType.VOICE_DESIGN] is None:
            self._models[ModelType.VOICE_DESIGN] = self._load_model(ModelType.VOICE_DESIGN)
        return self._models[ModelType.VOICE_DESIGN]

    @property
    def base_model(self) -> Any:
        """Lazily load and return the Base model (1.7B) for voice cloning."""
        if self._models[ModelType.BASE] is None:
            self._models[ModelType.BASE] = self._load_model(ModelType.BASE)
        return self._models[ModelType.BASE]
    
    @property
    def base_small_model(self) -> Any:
        """Lazily load and return the Base Small model (0.6B) for voice cloning."""
        if self._models[ModelType.BASE_SMALL] is None:
            self._models[ModelType.BASE_SMALL] = self._load_model(ModelType.BASE_SMALL)
        return self._models[ModelType.BASE_SMALL]

    def _audio_to_bytes(self, audio_data, sample_rate: int, format: str = 'WAV') -> bytes:
        """Convert audio array to bytes."""
        byte_io = io.BytesIO()
        sf.write(byte_io, audio_data, sample_rate, format=format)
        byte_io.seek(0)
        return byte_io.read()

    def get_available_presets(self) -> Dict[str, str]:
        """Get dictionary of available preset names and descriptions."""
        return {name: preset.description for name, preset in self.presets.items()}

    def get_supported_speakers(self) -> list:
        """Get list of supported speakers from the CustomVoice model."""
        try:
            return self.custom_voice_model.get_supported_speakers()
        except Exception as e:
            logger.warning(f"[VoiceForge] Could not get speakers: {e}")
            return ["Ryan", "Vivian"]  # Fallback defaults

    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        # Return known supported languages without triggering model load
        return [
            "Auto", "Chinese", "English", "Japanese", "Korean",
            "German", "French", "Russian", "Portuguese",
            "Spanish", "Italian"
        ]

    def generate_preset(
        self,
        text: str,
        preset_name: str,
        language: str = "Auto",
        model_size: str = "1.7B"
    ) -> bytes:
        """
        Generate speech using a preset voice.
        
        Args:
            text: The text to synthesize
            preset_name: Name of the preset to use
            language: Language code or "Auto" for automatic detection
            model_size: Model size to use: "1.7B" (default) or "0.6B"
            
        Returns:
            WAV audio as bytes
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        preset = self.presets.get(preset_name)
        if preset is None:
            logger.warning(f"[VoiceForge] Unknown preset '{preset_name}', using 'Deep Male'")
            preset = self.presets["Deep Male"]
        
        logger.info(f"[VoiceForge] Generating preset '{preset_name}' (size: {model_size}) for {len(text)} chars")
        
        try:
            # Select model based on size
            if model_size in ["0.6B", "small", "small-model"]:
                model = self.custom_voice_small_model
            else:
                model = self.custom_voice_model
                
            wavs, sr = model.generate_custom_voice(
                text=text,
                language=language,
                speaker=preset.speaker,
                instruct=preset.instruct,
            )
            
            logger.info(f"[VoiceForge] Generated {len(wavs[0])/sr:.2f}s of audio at {sr}Hz")
            return self._audio_to_bytes(wavs[0], sr)
            
        except Exception as e:
            error_msg = str(e)
            if "channels > 65536" in error_msg and self.device == "mps":
                logger.warning(f"[VoiceForge] MPS limit exceeded ({error_msg}). Switching to CPU and retrying...")
                
                # 1. Unload model to free MPS memory
                model_type = ModelType.CUSTOM_VOICE_SMALL if model_size in ["0.6B", "small", "small-model"] else ModelType.CUSTOM_VOICE
                self.unload_model(model_type)
                
                # 2. Force CPU for this session
                self._device = "cpu"
                self._dtype = torch.float32
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

                # 3. Retry recursively
                logger.info("[VoiceForge] Retrying generation on CPU...")
                return self.generate_preset(
                    text=text,
                    preset_name=preset_name,
                    language=language,
                    model_size=model_size
                )
                
            logger.error(f"[VoiceForge] Preset generation failed: {e}")
            raise RuntimeError(f"Speech generation failed: {str(e)}") from e

    def generate_voice_design(
        self,
        text: str,
        voice_description: str,
        language: str = "Auto"
    ) -> bytes:
        """
        Generate speech with a designed voice from natural language description.
        
        Args:
            text: The text to synthesize
            voice_description: Natural language description of desired voice
            language: Language code or "Auto" for automatic detection
            
        Returns:
            WAV audio as bytes
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if not voice_description.strip():
            raise ValueError("Voice description cannot be empty")
        
        logger.info(f"[VoiceForge] Generating voice design for {len(text)} chars")
        logger.debug(f"[VoiceForge] Voice description: {voice_description[:100]}...")
        
        try:
            wavs, sr = self.voice_design_model.generate_voice_design(
                text=text,
                language=language,
                instruct=voice_description,
            )
            
            logger.info(f"[VoiceForge] Generated {len(wavs[0])/sr:.2f}s of audio at {sr}Hz")
            return self._audio_to_bytes(wavs[0], sr)
            
        except Exception as e:
            error_msg = str(e)
            if "channels > 65536" in error_msg and self.device == "mps":
                logger.warning(f"[VoiceForge] MPS limit exceeded ({error_msg}). Switching to CPU and retrying...")
                
                # 1. Unload model to free MPS memory
                self.unload_model(ModelType.VOICE_DESIGN)
                
                # 2. Force CPU for this session
                self._device = "cpu"
                self._dtype = torch.float32
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

                # 3. Retry recursively
                logger.info("[VoiceForge] Retrying generation on CPU...")
                return self.generate_voice_design(
                    text=text,
                    voice_description=voice_description,
                    language=language
                )
                
            logger.error(f"[VoiceForge] Voice design generation failed: {e}")
            raise RuntimeError(f"Voice design failed: {str(e)}") from e

    def generate_clone(
        self,
        text: str,
        reference_audio_path: str,
        reference_text: Optional[str] = None,
        language: str = "Auto",
        use_x_vector_only: bool = False,
        model_size: str = "1.7B"
    ) -> bytes:
        """
        Clone a voice from reference audio and synthesize new text.
        
        Args:
            text: The text to synthesize
            reference_audio_path: Path/URL to reference audio file
            reference_text: Transcript of the reference audio (recommended for quality)
            language: Language code or "Auto" for automatic detection
            use_x_vector_only: If True, use only speaker embedding (faster but lower quality)
            model_size: "1.7B" or "0.6B"
            
        Returns:
            WAV audio as bytes
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        logger.info(f"[VoiceForge] Cloning voice for {len(text)} chars (size: {model_size})")
        
        # Determine which model to use
        is_small = model_size in ["0.6B", "small", "small-model"]
        model_type = ModelType.BASE_SMALL if is_small else ModelType.BASE
        
        try:
            # Select model
            model = self.base_small_model if is_small else self.base_model
            
            if reference_text and not use_x_vector_only:
                # Full voice cloning with reference transcript
                wavs, sr = model.generate_voice_clone(
                    text=text,
                    language=language,
                    ref_audio=reference_audio_path,
                    ref_text=reference_text,
                )
            else:
                # X-vector only mode
                prompt = model.create_voice_clone_prompt(
                    ref_audio=reference_audio_path,
                    x_vector_only_mode=True,
                )
                wavs, sr = model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                )
            
            logger.info(f"[VoiceForge] Generated {len(wavs[0])/sr:.2f}s of audio at {sr}Hz")
            return self._audio_to_bytes(wavs[0], sr)
            
        except Exception as e:
            error_msg = str(e)
            if "channels > 65536" in error_msg and self.device == "mps":
                logger.warning(f"[VoiceForge] MPS limit exceeded ({error_msg}). Switching to CPU and retrying...")
                
                # 1. Unload model to free MPS memory
                self.unload_model(model_type)
                
                # 2. Force CPU for this session
                self._device = "cpu"
                self._dtype = torch.float32
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

                # 3. Reload happens automatically on next property access
                
                # 4. Retry recursively
                logger.info("[VoiceForge] Retrying generation on CPU...")
                return self.generate_clone(
                    text=text,
                    reference_audio_path=reference_audio_path,
                    reference_text=reference_text,
                    language=language,
                    use_x_vector_only=use_x_vector_only,
                    model_size=model_size
                )
                
            logger.error(f"[VoiceForge] Voice cloning failed: {e}")
            raise RuntimeError(f"Voice cloning failed: {str(e)}") from e

    def create_reusable_clone_prompt(
        self,
        reference_audio_path: str,
        reference_text: Optional[str] = None,
        prompt_id: Optional[str] = None
    ) -> str:
        """
        Create a reusable voice clone prompt for multiple generations.
        
        Args:
            reference_audio_path: Path/URL to reference audio
            reference_text: Transcript of reference audio
            prompt_id: Optional ID for caching (auto-generated if not provided)
            
        Returns:
            Prompt ID that can be used with generate_from_cached_clone
        """
        import hashlib
        
        if prompt_id is None:
            # Generate ID from audio path
            prompt_id = hashlib.md5(reference_audio_path.encode()).hexdigest()[:12]
        
        logger.info(f"[VoiceForge] Creating reusable clone prompt: {prompt_id}")
        
        prompt = self.base_model.create_voice_clone_prompt(
            ref_audio=reference_audio_path,
            ref_text=reference_text,
            x_vector_only_mode=(reference_text is None),
        )
        
        self._clone_prompt_cache[prompt_id] = prompt
        return prompt_id

    def generate_from_cached_clone(
        self,
        text: str,
        prompt_id: str,
        language: str = "Auto"
    ) -> bytes:
        """
        Generate speech using a cached voice clone prompt.
        
        Args:
            text: The text to synthesize
            prompt_id: ID of the cached clone prompt
            language: Language code
            
        Returns:
            WAV audio as bytes
        """
        if prompt_id not in self._clone_prompt_cache:
            raise ValueError(f"Clone prompt '{prompt_id}' not found in cache")
        
        prompt = self._clone_prompt_cache[prompt_id]
        
        wavs, sr = self.base_model.generate_voice_clone(
            text=text,
            language=language,
            voice_clone_prompt=prompt,
        )
        
        return self._audio_to_bytes(wavs[0], sr)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status information."""
        return {
            "device": self.device,
            "dtype": str(self.dtype),
            "use_small_models": self.use_small_models,
            "models_loaded": {
                model_type.value: self._models[model_type] is not None
                for model_type in ModelType
            },
            "model_errors": {
                k.value: v for k, v in self._model_load_errors.items() if v is not None
            },
            "available_presets": list(self.presets.keys()),
            "cached_clone_prompts": list(self._clone_prompt_cache.keys()),
        }

    def unload_model(self, model_type: ModelType) -> None:
        """Unload a specific model to free memory."""
        if self._models[model_type] is not None:
            logger.info(f"[VoiceForge] Unloading {model_type.value} model")
            del self._models[model_type]
            self._models[model_type] = None
            
            # Clear CUDA cache if applicable
            if self.device.startswith("cuda"):
                torch.cuda.empty_cache()

    def unload_all_models(self) -> None:
        """Unload all models to free memory."""
        for model_type in ModelType:
            self.unload_model(model_type)


# Check if we should use small models based on environment
# Default to small models since they're faster to download and use less memory
USE_SMALL_MODELS = os.environ.get("VOICEFORGE_SMALL_MODELS", "0").lower() not in ("0", "false", "no")

# Get custom models directory if set
MODELS_DIR = os.environ.get("VOICEFORGE_MODELS_DIR", None)

# Singleton instance
tts_engine = QwenTTSEngine(use_small_models=USE_SMALL_MODELS, models_dir=MODELS_DIR)

