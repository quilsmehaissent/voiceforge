"""
VoiceForge API Routes
Provides REST endpoints for text-to-speech functionality.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import io
import os
import tempfile
import uuid
import logging

from backend.app.core.tts_engine import tts_engine

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@router.get("/status")
async def get_engine_status():
    """Get the current status of the TTS engine."""
    try:
        status = tts_engine.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_available_presets():
    """Get list of available voice presets."""
    try:
        presets = tts_engine.get_available_presets()
        return JSONResponse(content={"presets": presets})
    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    try:
        languages = tts_engine.get_supported_languages()
        return JSONResponse(content={"languages": languages})
    except Exception as e:
        logger.error(f"Failed to get languages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speakers")
async def get_supported_speakers():
    """Get list of supported speakers for CustomVoice model."""
    try:
        speakers = tts_engine.get_supported_speakers()
        return JSONResponse(content={"speakers": speakers})
    except Exception as e:
        logger.error(f"Failed to get speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TTS Generation Endpoints
# ============================================================================

@router.post("/tts/preset")
async def generate_preset(
    text: str = Form(..., description="Text to synthesize"),
    preset_name: str = Form(..., description="Name of the voice preset"),
    language: str = Form("Auto", description="Language code or 'Auto'"),
    model_size: str = Form("1.7B", description="Model size: '1.7B' or '0.6B'")
):
    """
    Generate speech using a preset voice.
    
    Returns audio/wav stream.
    """
    try:
        # Validate input
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        logger.info(f"[API] Preset generation: preset={preset_name}, chars={len(text)}, size={model_size}")
        
        audio_bytes = tts_engine.generate_preset(
            text=text,
            preset_name=preset_name,
            language=language,
            model_size=model_size
        )
        
        # Save to static file
        filename = f"preset_{uuid.uuid4()}.wav"
        filepath = os.path.join("backend/static/generations", filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
            
        return JSONResponse(content={
            "status": "success",
            "url": f"/static/generations/{filename}",
            "filename": filename,
            "model_size": model_size,
            "feature": "preset"
        })
        
    except ValueError as e:
        logger.warning(f"[API] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"[API] Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/tts/design")
async def generate_voice_design(
    text: str = Form(..., description="Text to synthesize"),
    voice_description: str = Form(..., description="Natural language voice description"),
    language: str = Form("Auto", description="Language code or 'Auto'")
):
    """
    Generate speech with a custom voice designed from natural language description.
    
    Example descriptions:
    - "A warm, professional female voice with a friendly tone"
    - "An old British man with a deep, raspy voice"
    - "A young energetic teenager speaking excitedly"
    
    Returns audio/wav stream.
    """
    try:
        # Validate input
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if not voice_description.strip():
            raise HTTPException(status_code=400, detail="Voice description cannot be empty")
        
        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        logger.info(f"[API] Voice design: chars={len(text)}, desc_len={len(voice_description)}")
        
        audio_bytes = tts_engine.generate_voice_design(
            text=text,
            voice_description=voice_description,
            language=language
        )
        
        # Save to static file
        filename = f"design_{uuid.uuid4()}.wav"
        filepath = os.path.join("backend/static/generations", filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
            
        return JSONResponse(content={
            "status": "success",
            "url": f"/static/generations/{filename}",
            "filename": filename,
            "model_size": "1.7B", # Design typically uses the main model
            "feature": "design"
        })
        
    except ValueError as e:
        logger.warning(f"[API] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"[API] Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/tts/clone")
async def generate_clone(
    text: str = Form(..., description="Text to synthesize"),
    file: UploadFile = File(..., description="Reference audio file (WAV/MP3)"),
    reference_text: Optional[str] = Form(None, description="Transcript of reference audio (recommended)"),
    language: str = Form("Auto", description="Language code or 'Auto'"),
    model_size: str = Form("1.7B", description="Model size: '1.7B' or '0.6B'")
):
    """
    Clone a voice from reference audio and synthesize new content.
    
    For best quality, provide the transcript of the reference audio.
    Without a transcript, the system will use x-vector mode which is faster but may have lower quality.
    
    Supported audio formats: WAV, MP3
    Recommended reference audio: 5-30 seconds of clear speech
    
    Returns audio/wav stream.
    """
    temp_filepath = None
    
    try:
        # Validate input
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Save to temp file
        temp_filepath = os.path.join(tempfile.gettempdir(), f"voiceforge_{uuid.uuid4()}{file_ext}")
        with open(temp_filepath, "wb") as f:
            f.write(file_content)
        
        logger.info(f"[API] Voice clone: chars={len(text)}, file={file.filename}, has_transcript={reference_text is not None}, size={model_size}")
        
        audio_bytes = tts_engine.generate_clone(
            text=text,
            reference_audio_path=temp_filepath,
            reference_text=reference_text.strip() if reference_text else None,
            language=language,
            model_size=model_size
        )
        
        # Save to static file
        filename = f"clone_{uuid.uuid4()}.wav"
        filepath = os.path.join("backend/static/generations", filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
            
        return JSONResponse(content={
            "status": "success",
            "url": f"/static/generations/{filename}",
            "filename": filename,
            "model_size": model_size,
            "feature": "clone"
        })
        
    except ValueError as e:
        logger.warning(f"[API] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"[API] Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        # Clean up temp file
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception as e:
                logger.warning(f"[API] Failed to cleanup temp file: {e}")


# ============================================================================
# Advanced Clone Endpoints (for reusable prompts)
# ============================================================================

@router.post("/tts/clone/create-prompt")
async def create_clone_prompt(
    file: UploadFile = File(..., description="Reference audio file"),
    reference_text: Optional[str] = Form(None, description="Transcript of reference audio"),
    prompt_id: Optional[str] = Form(None, description="Custom ID for the prompt")
):
    """
    Create a reusable voice clone prompt.
    
    This extracts voice characteristics from the reference audio once,
    allowing multiple generations without re-processing the reference.
    
    Returns the prompt_id to use with /tts/clone/from-prompt
    """
    temp_filepath = None
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Save to temp file
        file_ext = os.path.splitext(file.filename)[1].lower()
        file_content = await file.read()
        temp_filepath = os.path.join(tempfile.gettempdir(), f"voiceforge_{uuid.uuid4()}{file_ext}")
        
        with open(temp_filepath, "wb") as f:
            f.write(file_content)
        
        created_id = tts_engine.create_reusable_clone_prompt(
            reference_audio_path=temp_filepath,
            reference_text=reference_text.strip() if reference_text else None,
            prompt_id=prompt_id
        )
        
        return JSONResponse(content={
            "success": True,
            "prompt_id": created_id,
            "message": f"Clone prompt created. Use prompt_id '{created_id}' with /tts/clone/from-prompt"
        })
        
    except Exception as e:
        logger.error(f"[API] Create clone prompt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except:
                pass


@router.post("/tts/clone/from-prompt")
async def generate_from_clone_prompt(
    text: str = Form(..., description="Text to synthesize"),
    prompt_id: str = Form(..., description="ID of the cached clone prompt"),
    language: str = Form("Auto", description="Language code or 'Auto'")
):
    """
    Generate speech using a cached voice clone prompt.
    
    Use /tts/clone/create-prompt first to create the prompt.
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        audio_bytes = tts_engine.generate_from_cached_clone(
            text=text,
            prompt_id=prompt_id,
            language=language
        )
        
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=voiceforge-clone.wav"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Generate from prompt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/generations/{filename}")
async def delete_generation(filename: str):
    """
    Delete a generated audio file.
    """
    try:
        # Prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
            
        filepath = os.path.join("backend/static/generations", filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return JSONResponse(content={"status": "success", "message": "File deleted"})
        else:
            raise HTTPException(status_code=404, detail="File not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
