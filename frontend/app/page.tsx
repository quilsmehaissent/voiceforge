'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  Mic,
  Layers,
  Download,
  History,
  Volume2,
  Upload,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
  Settings,
  ChevronDown,
  Trash2,
  Edit2,
  Folder,
  FolderPlus,
  MoreHorizontal,
  Save,
  Check
} from 'lucide-react';

// Types
interface HistoryItem {
  id: number;
  text: string;
  type: 'presets' | 'design' | 'clone';
  time: string;
  url: string;
  filename?: string;
  modelSize?: string;
  preset?: string;
  description?: string;
  folder?: string;
  label?: string; // User-defined name
}

interface EngineStatus {
  device: string;
  models_loaded: Record<string, boolean>;
  available_presets: number;
  use_small_models: boolean;
}

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'info';
  onClose: () => void;
}

// Toast Component
function Toast({ message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = {
    success: 'bg-green-500/90',
    error: 'bg-red-500/90',
    info: 'bg-indigo-500/90'
  }[type];

  const Icon = type === 'success' ? CheckCircle2 : type === 'error' ? AlertCircle : AlertCircle;

  return (
    <div className={`fixed top-4 right-4 z-50 ${bgColor} text-white px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 animate-slide-in`}>
      <Icon size={20} />
      <span className="font-medium">{message}</span>
      <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full transition-colors">
        <X size={16} />
      </button>
    </div>
  );
}

// Main Component
export default function Home() {
  const [activeTab, setActiveTab] = useState<'presets' | 'design' | 'clone'>('presets');
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [generatedHistory, setGeneratedHistory] = useState<HistoryItem[]>([]);
  const [folders, setFolders] = useState<string[]>(['Favorites', 'Work']);
  const [activeFolder, setActiveFolder] = useState<string>('All');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Engine status
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  // Preset State
  const [selectedPreset, setSelectedPreset] = useState('Deep Male');
  const [availablePresets, setAvailablePresets] = useState<Record<string, string>>({});

  // Voice Design State
  const [voiceDescription, setVoiceDescription] = useState('');

  // Clone State
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [referenceText, setReferenceText] = useState('');

  // Language selection and Model Size
  const [language, setLanguage] = useState('Auto');
  const [modelSize, setModelSize] = useState('1.7B');
  const [availableLanguages, setAvailableLanguages] = useState<string[]>([]);

  // Audio player
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const API_BASE = 'http://localhost:8000';

  // Fetch engine status and presets on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [statusRes, presetsRes, languagesRes] = await Promise.all([
          fetch(`${API_BASE}/health`),
          fetch(`${API_BASE}/api/presets`),
          fetch(`${API_BASE}/api/languages`)
        ]);

        if (statusRes.ok) {
          const data = await statusRes.json();
          setEngineStatus(data.engine);
          if (data.engine.use_small_models) {
            setModelSize('0.6B');
          }
        }

        if (presetsRes.ok) {
          const data = await presetsRes.json();
          setAvailablePresets(data.presets || {});
          const presetNames = Object.keys(data.presets || {});
          if (presetNames.length > 0 && !presetNames.includes(selectedPreset)) {
            setSelectedPreset(presetNames[0]);
          }
        }

        if (languagesRes.ok) {
          const data = await languagesRes.json();
          setAvailableLanguages(data.languages || ['Auto', 'English', 'Chinese']);
        }
      } catch (error) {
        console.error('Failed to fetch status:', error);
        setToast({ message: 'Failed to connect to backend', type: 'error' });
      } finally {
        setStatusLoading(false);
      }
    };

    fetchStatus();
  }, []);

  // Enforce 1.7B model for Voice Design
  useEffect(() => {
    if (activeTab === 'design') {
      setModelSize('1.7B');
    }
  }, [activeTab]);

  // Load from LocalStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem('voiceforge_history');
    const savedFolders = localStorage.getItem('voiceforge_folders');

    if (savedHistory) {
      try {
        setGeneratedHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }

    if (savedFolders) {
      try {
        setFolders(JSON.parse(savedFolders));
      } catch (e) {
        console.error("Failed to parse folders", e);
      }
    }
  }, []);

  // Save to LocalStorage
  useEffect(() => {
    localStorage.setItem('voiceforge_history', JSON.stringify(generatedHistory));
    localStorage.setItem('voiceforge_folders', JSON.stringify(folders));
  }, [generatedHistory, folders]);

  // Audio time update
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioUrl]);

  const handleGenerate = async () => {
    if (!text.trim()) {
      setToast({ message: 'Please enter some text to generate', type: 'error' });
      return;
    }

    if (activeTab === 'design' && !voiceDescription.trim()) {
      setToast({ message: 'Please describe the voice you want', type: 'error' });
      return;
    }

    if (activeTab === 'clone' && !cloneFile) {
      setToast({ message: 'Please upload a reference audio file', type: 'error' });
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('text', text);
    formData.append('language', language);
    formData.append('model_size', modelSize);

    let endpoint = '';

    if (activeTab === 'presets') {
      endpoint = `${API_BASE}/api/tts/preset`;
      formData.append('preset_name', selectedPreset);
    } else if (activeTab === 'design') {
      endpoint = `${API_BASE}/api/tts/design`;
      formData.append('voice_description', voiceDescription);
    } else if (activeTab === 'clone') {
      endpoint = `${API_BASE}/api/tts/clone`;
      if (cloneFile) {
        formData.append('file', cloneFile);
      }
      if (referenceText.trim()) {
        formData.append('reference_text', referenceText);
      }
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Generation failed' }));
        throw new Error(error.detail || 'Generation failed');
      }

      // Handle JSON response
      const data = await response.json();
      const url = `${API_BASE}${data.url}`;

      setAudioUrl(url);
      setIsPlaying(false);
      setCurrentTime(0);

      // Add to history
      const historyItem: HistoryItem = {
        id: Date.now(),
        text: text.substring(0, 60) + (text.length > 60 ? '...' : ''),
        type: activeTab,
        time: new Date().toLocaleTimeString(),
        url: url,
        filename: data.filename,
        modelSize: data.model_size,
        label: text.substring(0, 30) || 'Untitled Generation',
        folder: 'All'
      };

      if (activeTab === 'presets') {
        historyItem.preset = selectedPreset;
      } else if (activeTab === 'design') {
        historyItem.description = voiceDescription.substring(0, 30) + '...';
      }

      setGeneratedHistory(prev => [historyItem, ...prev]);

      setToast({ message: 'Audio generated successfully!', type: 'success' });

      // Auto-play
      setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.play();
          setIsPlaying(true);
        }
      }, 100);

    } catch (error) {
      console.error(error);
      setToast({
        message: error instanceof Error ? error.message : 'Failed to generate audio',
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (item: HistoryItem) => {
    try {
      // Optimistic update
      setGeneratedHistory(prev => prev.filter(i => i.id !== item.id));

      if (item.filename) {
        await fetch(`${API_BASE}/api/generations/${item.filename}`, {
          method: 'DELETE'
        });
      }
      setToast({ message: 'Deleted successfully', type: 'success' });
    } catch (error) {
      console.error('Delete failed:', error);
      setToast({ message: 'Failed to delete file', type: 'error' });
    }
  };

  const handleRename = (id: number) => {
    if (!editLabel.trim()) return;
    setGeneratedHistory(prev => prev.map(item =>
      item.id === id ? { ...item, label: editLabel } : item
    ));
    setEditingId(null);
  };

  const startEditing = (item: HistoryItem) => {
    setEditingId(item.id);
    setEditLabel(item.label || item.text);
  };

  const handleMoveFolder = (id: number, folder: string) => {
    setGeneratedHistory(prev => prev.map(item =>
      item.id === id ? { ...item, folder: folder } : item
    ));
    setToast({ message: `Moved to ${folder}`, type: 'success' });
  };

  const createFolder = () => {
    const name = prompt("Enter folder name:");
    if (name && !folders.includes(name)) {
      setFolders(prev => [...prev, name]);
    }
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = percent * duration;
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const playHistoryItem = (item: HistoryItem) => {
    setAudioUrl(item.url);
    setTimeout(() => {
      if (audioRef.current) {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }, 100);
  };

  return (
    <div className="flex h-screen bg-neutral-950 text-white font-sans overflow-hidden">
      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Sidebar */}
      <aside className="w-72 border-r border-neutral-800 bg-neutral-900/50 backdrop-blur flex flex-col">
        <div className="p-6 border-b border-neutral-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Volume2 size={20} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-xl tracking-tight">VoiceForge</h1>
              <p className="text-xs text-neutral-500">Qwen3-TTS Studio</p>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="px-4 py-3 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-neutral-500 uppercase tracking-wider">System</span>
            {statusLoading ? (
              <Loader2 size={12} className="text-neutral-500 animate-spin" />
            ) : engineStatus ? (
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs text-green-400">{engineStatus.device.toUpperCase()}</span>
                <span className="text-xs text-neutral-600">•</span>
                <span className="text-xs text-neutral-400">
                  {engineStatus.use_small_models ? '0.6B' : '1.7B'}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-red-500 rounded-full" />
                <span className="text-xs text-red-400">Offline</span>
              </div>
            )}
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <button
            onClick={() => setActiveTab('presets')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all ${activeTab === 'presets'
              ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-white border border-indigo-500/30'
              : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
              }`}
          >
            <Layers size={18} />
            <div className="text-left">
              <span className="font-medium block">Presets</span>
              <span className="text-xs opacity-60">Ready-made voices</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('design')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all ${activeTab === 'design'
              ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-white border border-indigo-500/30'
              : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
              }`}
          >
            <Sparkles size={18} />
            <div className="text-left">
              <span className="font-medium block">Voice Design</span>
              <span className="text-xs opacity-60">Create from description</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('clone')}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all ${activeTab === 'clone'
              ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-white border border-indigo-500/30'
              : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
              }`}
          >
            <Mic size={18} />
            <div className="text-left">
              <span className="font-medium block">Voice Clone</span>
              <span className="text-xs opacity-60">Clone any voice</span>
            </div>
          </button>
        </nav>

        <div className="p-4 border-t border-neutral-800 space-y-3">
          {/* Language Selector */}
          <div className="mb-4">
            {/* Language Selector */}
            <label className="text-xs text-neutral-500 mb-1.5 block uppercase tracking-wider">Language</label>
            <div className="relative">
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-neutral-900 border border-neutral-800 text-white text-sm rounded-lg px-3 py-2 appearance-none focus:outline-none focus:border-indigo-500 transition-colors"
              >
                {availableLanguages.map(lang => (
                  <option key={lang} value={lang}>{lang}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 pointer-events-none" />
            </div>
          </div>

          {/* Model Size Selector */}
          <div className="mb-4">
            <label className="text-xs text-neutral-500 mb-1.5 block uppercase tracking-wider">Model Size</label>
            <div className="grid grid-cols-2 bg-neutral-900 border border-neutral-800 rounded-lg p-1">
              <button
                onClick={() => setModelSize('1.7B')}
                className={`text-xs font-medium py-1.5 rounded-md transition-all ${modelSize === '1.7B' ? 'bg-indigo-500/20 text-indigo-400' : 'text-neutral-500 hover:text-neutral-300'}`}
              >
                1.7B (High)
              </button>
              <button
                onClick={() => setModelSize('0.6B')}
                disabled={activeTab === 'design'}
                title={activeTab === 'design' ? 'Not available for Voice Design' : 'Faster generation, slightly lower quality'}
                className={`text-xs font-medium py-1.5 rounded-md transition-all ${modelSize === '0.6B'
                  ? 'bg-indigo-500/20 text-indigo-400'
                  : activeTab === 'design'
                    ? 'text-neutral-700 cursor-not-allowed opacity-50'
                    : 'text-neutral-500 hover:text-neutral-300'
                  }`}
              >
                0.6B (Fast)
              </button>
            </div>
          </div>

          <div className="text-xs text-neutral-600 text-center text-opacity-50">Powered by Qwen3-TTS</div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative">
        <div className="flex-1 p-8 overflow-y-auto pb-32">
          <div className="max-w-4xl mx-auto space-y-8">

            {/* Header Area */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">
                  {activeTab === 'presets' && 'Voice Presets'}
                  {activeTab === 'design' && 'Voice Design'}
                  {activeTab === 'clone' && 'Voice Clone'}
                </h2>
                <p className="text-neutral-500 mt-1">
                  {activeTab === 'presets' && 'Generate speech using curated voice characters'}
                  {activeTab === 'design' && 'Create a unique voice from natural language description'}
                  {activeTab === 'clone' && 'Clone any voice from a reference audio sample'}
                </p>
              </div>
            </div>

            {/* Input Form */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

              {/* Left Column: Text Input */}
              <div className="lg:col-span-2 space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 focus-within:ring-2 focus-within:ring-indigo-500/50 focus-within:border-indigo-500/50 transition-all">
                  <label className="text-xs font-medium text-neutral-500 mb-3 block uppercase tracking-wider">
                    Text to Speak
                  </label>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter the text you want to convert to speech..."
                    className="w-full h-48 bg-transparent text-lg text-neutral-200 placeholder-neutral-600 focus:outline-none resize-none leading-relaxed"
                  />
                  <div className="flex justify-between items-center text-xs text-neutral-500 mt-3 pt-3 border-t border-neutral-800">
                    <span>{text.length} / 5000 characters</span>
                    <button
                      onClick={() => setText('')}
                      className="hover:text-neutral-300 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {/* Sample texts */}
                <div className="flex flex-wrap gap-2">
                  {[
                    "Hello! Welcome to VoiceForge.",
                    "The quick brown fox jumps over the lazy dog.",
                    "In a world where technology meets creativity, anything is possible."
                  ].map((sample, i) => (
                    <button
                      key={i}
                      onClick={() => setText(sample)}
                      className="text-xs px-3 py-1.5 bg-neutral-900 border border-neutral-800 rounded-full text-neutral-400 hover:text-white hover:border-neutral-600 transition-colors"
                    >
                      {sample.substring(0, 30)}...
                    </button>
                  ))}
                </div>
              </div>

              {/* Right Column: Controls */}
              <div className="space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 space-y-5">

                  {activeTab === 'presets' && (
                    <div>
                      <label className="text-xs font-medium text-neutral-500 mb-3 block uppercase tracking-wider">
                        Voice Preset
                      </label>
                      <div className="space-y-2">
                        {Object.entries(availablePresets).length > 0 ? (
                          Object.entries(availablePresets).map(([name, description]) => (
                            <button
                              key={name}
                              onClick={() => setSelectedPreset(name)}
                              className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${selectedPreset === name
                                ? 'bg-indigo-500/20 border-indigo-500/50 text-white'
                                : 'bg-neutral-950 border-neutral-800 text-neutral-400 hover:border-neutral-700 hover:text-neutral-200'
                                }`}
                            >
                              <div className="font-medium">{name}</div>
                              <div className="text-xs opacity-60 mt-0.5">{description}</div>
                            </button>
                          ))
                        ) : (
                          ['Deep Male', 'Energetic Female', 'Raspy Wizard', 'Soft Whisper', 'News Anchor'].map(name => (
                            <button
                              key={name}
                              onClick={() => setSelectedPreset(name)}
                              className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${selectedPreset === name
                                ? 'bg-indigo-500/20 border-indigo-500/50 text-white'
                                : 'bg-neutral-950 border-neutral-800 text-neutral-400 hover:border-neutral-700 hover:text-neutral-200'
                                }`}
                            >
                              <div className="font-medium">{name}</div>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  {activeTab === 'design' && (
                    <div>
                      <label className="text-xs font-medium text-neutral-500 mb-3 block uppercase tracking-wider">
                        Voice Description
                      </label>
                      <textarea
                        value={voiceDescription}
                        onChange={(e) => setVoiceDescription(e.target.value)}
                        placeholder="Describe the voice you want to create...&#10;&#10;Examples:&#10;• A warm, professional female with a friendly tone&#10;• An old British man with a deep, raspy voice&#10;• A young energetic teenager speaking excitedly"
                        className="w-full h-40 bg-neutral-950 border border-neutral-800 text-white rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors resize-none text-sm leading-relaxed"
                      />
                      <div className="flex flex-wrap gap-2 mt-3">
                        {[
                          "A deep, authoritative male narrator",
                          "A cheerful young woman with energy",
                          "A calm, soothing meditation guide"
                        ].map((desc, i) => (
                          <button
                            key={i}
                            onClick={() => setVoiceDescription(desc)}
                            className="text-xs px-2 py-1 bg-neutral-800 rounded-md text-neutral-500 hover:text-white transition-colors"
                          >
                            {desc.substring(0, 25)}...
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeTab === 'clone' && (
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs font-medium text-neutral-500 mb-3 block uppercase tracking-wider">
                          Reference Audio
                        </label>
                        <div className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer relative ${cloneFile ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-neutral-800 hover:border-neutral-600'
                          }`}>
                          <input
                            type="file"
                            accept="audio/*"
                            onChange={(e) => setCloneFile(e.target.files?.[0] || null)}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                          />
                          {cloneFile ? (
                            <>
                              <CheckCircle2 size={24} className="mx-auto text-indigo-400 mb-2" />
                              <p className="text-sm text-white font-medium truncate px-2">{cloneFile.name}</p>
                              <p className="text-xs text-neutral-500 mt-1">
                                {(cloneFile.size / 1024 / 1024).toFixed(2)} MB
                              </p>
                            </>
                          ) : (
                            <>
                              <Upload size={24} className="mx-auto text-neutral-500 mb-2" />
                              <p className="text-sm text-neutral-400">Drop audio file or click to upload</p>
                              <p className="text-xs text-neutral-600 mt-1">WAV, MP3, M4A • Max 10MB</p>
                            </>
                          )}
                        </div>
                        {cloneFile && (
                          <button
                            onClick={() => setCloneFile(null)}
                            className="text-xs text-red-400 hover:text-red-300 mt-2 transition-colors"
                          >
                            Remove file
                          </button>
                        )}
                      </div>

                      <div>
                        <label className="text-xs font-medium text-neutral-500 mb-2 block uppercase tracking-wider">
                          Reference Transcript
                          <span className="text-neutral-600 normal-case ml-1">(recommended)</span>
                        </label>
                        <textarea
                          value={referenceText}
                          onChange={(e) => setReferenceText(e.target.value)}
                          placeholder="Enter what is being said in the reference audio for better cloning quality..."
                          className="w-full h-24 bg-neutral-950 border border-neutral-800 text-white rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors resize-none text-sm"
                        />
                        <p className="text-xs text-neutral-600 mt-1">
                          Providing the transcript improves voice cloning accuracy
                        </p>
                      </div>
                    </div>
                  )}

                  <button
                    onClick={handleGenerate}
                    disabled={loading || !text.trim()}
                    className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-indigo-600 disabled:hover:to-purple-600 text-white font-semibold py-4 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/30"
                  >
                    {loading ? (
                      <>
                        <Loader2 size={20} className="animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Play size={18} fill="currentColor" />
                        Generate Speech
                      </>
                    )}
                  </button>
                </div>
              </div>

            </div>

            {/* History Section */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2">
                  <History size={16} /> Library
                </h3>
                <div className="flex items-center gap-2">
                  <select
                    value={activeFolder}
                    onChange={(e) => setActiveFolder(e.target.value)}
                    className="bg-neutral-900 border border-neutral-800 text-xs text-white rounded-lg px-2 py-1.5 focus:outline-none"
                  >
                    <option value="All">All Items</option>
                    {folders.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <button onClick={createFolder} className="p-1.5 hover:bg-neutral-800 rounded-lg text-neutral-400 hover:text-white" title="New Folder">
                    <FolderPlus size={16} />
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {generatedHistory.filter(item => activeFolder === 'All' || item.folder === activeFolder).length === 0 ? (
                  <div className="text-neutral-600 text-sm italic py-8 text-center border border-dashed border-neutral-800 rounded-xl">
                    {generatedHistory.length === 0 ? "No generations yet." : `No items in ${activeFolder}.`}
                  </div>
                ) : (
                  generatedHistory
                    .filter(item => activeFolder === 'All' || item.folder === activeFolder)
                    .map((item) => (
                      <div
                        key={item.id}
                        className="bg-neutral-900/50 border border-neutral-800 p-4 rounded-xl hover:border-neutral-700 transition-all group"
                      >
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div className="flex-1 min-w-0">
                            {editingId === item.id ? (
                              <div className="flex items-center gap-2">
                                <input
                                  value={editLabel}
                                  onChange={(e) => setEditLabel(e.target.value)}
                                  className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1 text-sm text-white w-full focus:outline-none focus:border-indigo-500"
                                  autoFocus
                                />
                                <button onClick={() => handleRename(item.id)} className="p-1 text-green-400 hover:text-green-300"><Check size={16} /></button>
                                <button onClick={() => setEditingId(null)} className="p-1 text-neutral-500 hover:text-neutral-300"><X size={16} /></button>
                              </div>
                            ) : (
                              <h4 className="font-medium text-white truncate text-base flex items-center gap-2">
                                {item.label || item.text}
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button onClick={() => startEditing(item)} className="p-1 text-neutral-500 hover:text-white">
                                    <Edit2 size={12} />
                                  </button>
                                </span>
                              </h4>
                            )}
                            <p className="text-xs text-neutral-500 truncate mt-1">{item.text}</p>
                          </div>

                          <div className="flex items-center gap-1">
                            <div className="relative group/folder">
                              <button className="p-2 hover:bg-neutral-800 rounded-lg text-neutral-500 hover:text-white transition-colors">
                                <Folder size={16} />
                              </button>
                              <div className="absolute right-0 top-full mt-1 bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl py-1 px-1 hidden group-hover/folder:block z-20 w-32">
                                <div className="text-[10px] uppercase text-neutral-500 px-2 py-1">Move to...</div>
                                {folders.map(f => (
                                  <button
                                    key={f}
                                    onClick={() => handleMoveFolder(item.id, f)}
                                    className={`text-xs w-full text-left px-2 py-1.5 rounded hover:bg-neutral-800 ${item.folder === f ? 'text-indigo-400' : 'text-neutral-300'}`}
                                  >
                                    {f}
                                  </button>
                                ))}
                                {item.folder !== 'All' && item.folder && (
                                  <button
                                    onClick={() => handleMoveFolder(item.id, 'All')}
                                    className="text-xs w-full text-left px-2 py-1.5 rounded hover:bg-neutral-800 text-neutral-400 italic"
                                  >
                                    Remove from folder
                                  </button>
                                )}
                              </div>
                            </div>

                            <button
                              onClick={() => handleDelete(item)}
                              className="p-2 hover:bg-red-500/10 rounded-lg text-neutral-500 hover:text-red-400 transition-colors"
                              title="Delete"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-800/50">
                          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar mask-linear-fade">
                            {/* Feature Badge */}
                            <span className={`text-[10px] font-medium uppercase tracking-wider px-2 py-1 rounded-md border ${item.type === 'presets' ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' :
                              item.type === 'design' ? 'bg-purple-500/10 border-purple-500/20 text-purple-400' :
                                'bg-pink-500/10 border-pink-500/20 text-pink-400'
                              }`}>
                              {item.type}
                            </span>

                            {/* Model Size Badge (0.6 or 1.7) */}
                            {item.modelSize && (
                              <span className={`text-[10px] font-medium px-2 py-1 rounded-md border flex items-center gap-1 ${item.modelSize.includes('1.7') ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                                }`}>
                                <div className="w-1.5 h-1.5 rounded-full bg-current" />
                                {item.modelSize}
                              </span>
                            )}

                            {/* Extra Info */}
                            {item.preset && <span className="text-xs text-neutral-500 border border-neutral-800 px-2 py-1 rounded-md">{item.preset}</span>}
                            <span className="text-xs text-neutral-600 whitespace-nowrap">{item.time}</span>
                          </div>

                          <div className="flex items-center gap-2 ml-4">
                            <a
                              href={item.url}
                              download={`voiceforge-${item.id}.wav`}
                              className="p-2 bg-neutral-800 hover:bg-neutral-700 rounded-full text-neutral-400 hover:text-white transition-colors"
                            >
                              <Download size={14} />
                            </a>
                            <button
                              onClick={() => playHistoryItem(item)}
                              className="p-2 bg-indigo-500 hover:bg-indigo-400 rounded-full text-white transition-colors shadow-lg shadow-indigo-500/20"
                            >
                              <Play size={14} fill="currentColor" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Global Player Bar */}
        {audioUrl && (
          <div className="absolute bottom-0 left-0 right-0 bg-neutral-900/95 backdrop-blur-xl border-t border-neutral-800 p-4 flex items-center gap-6 px-8 z-50">
            <audio
              ref={audioRef}
              src={audioUrl}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />

            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-full flex items-center justify-center hover:scale-105 transition-transform shadow-lg shadow-indigo-500/30"
            >
              {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-0.5" />}
            </button>

            {/* Info */}
            <div className="min-w-0">
              <div className="text-sm font-medium text-white truncate">Now Playing</div>
              <div className="text-xs text-neutral-500">Generated audio</div>
            </div>

            {/* Progress Bar */}
            <div className="flex-1 flex items-center gap-3">
              <span className="text-xs text-neutral-500 w-10">{formatTime(currentTime)}</span>
              <div
                className="flex-1 h-1.5 bg-neutral-800 rounded-full cursor-pointer group"
                onClick={handleSeek}
              >
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full relative group-hover:from-indigo-400 group-hover:to-purple-400 transition-colors"
                  style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                >
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-md" />
                </div>
              </div>
              <span className="text-xs text-neutral-500 w-10">{formatTime(duration)}</span>
            </div>

            {/* Download */}
            <a
              href={audioUrl}
              download="voiceforge-generated.wav"
              className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium text-neutral-300 hover:text-white transition-colors"
            >
              <Download size={16} />
              Download
            </a>
          </div>
        )}
      </main>

      <style jsx>{`
        @keyframes slide-in {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
