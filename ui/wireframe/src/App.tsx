import React, { useState, useEffect, useCallback } from 'react';
import { PlayCircle, Mic, Upload, TrendingUp, MessageSquare, Volume2, CheckCircle, AlertCircle, Play, Pause, RotateCcw, LogOut } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import { apiService } from './services/api';
import {
  ViewType,
  PlayingVersion,
  TranscriptSegment,
  DetailedMetricsResponse,
  QualitySegment
} from './types';
import {
  mockTranscriptSegments,
  mockProgressData,
  mockWaveformSegments,
  convertTranscriptSegmentsToUI,
  convertWaveformToUI
} from './data/mockData';
import './App.css';

export default function SpeechCoachApp() {
  const { user, loading: authLoading, signInWithGoogle, signOut, getAccessToken } = useAuth();

  const [activeView, setActiveView] = useState<ViewType>('upload');
  const [expandedSection, setExpandedSection] = useState('feedback');
  const [playingSegment, setPlayingSegment] = useState<number | null>(null);
  const [playingVersion, setPlayingVersion] = useState<PlayingVersion | null>(null);
  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  // Backend integration state
  const [currentCoachingId, setCurrentCoachingId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<DetailedMetricsResponse | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<'idle' | 'pending' | 'processing' | 'completed' | 'failed'>('idle');

  // NEW: Transcript and waveform state
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegment[]>([]);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [waveformPeaks, setWaveformPeaks] = useState<number[]>([]);
  const [waveformQualitySegments, setWaveformQualitySegments] = useState<QualitySegment[]>([]);
  const [isLoadingWaveform, setIsLoadingWaveform] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);

  const loadTranscript = useCallback(async (coachingId: string) => {
    try {
      setIsLoadingTranscript(true);
      const token = await getAccessToken();
      if (!token) return;

      const transcriptData = await apiService.getTranscript(coachingId, token, 6);
      const uiSegments = convertTranscriptSegmentsToUI(transcriptData.segments);
      setTranscriptSegments(uiSegments);
    } catch (error) {
      console.error('Error loading transcript:', error);
      // Fallback to mock data on error
      setTranscriptSegments(mockTranscriptSegments);
    } finally {
      setIsLoadingTranscript(false);
    }
  }, [getAccessToken]);

  const loadWaveform = useCallback(async (coachingId: string) => {
    try {
      setIsLoadingWaveform(true);
      const token = await getAccessToken();
      if (!token) return;

      const waveformData = await apiService.getWaveform(coachingId, token, 1000);
      const { peaks, qualitySegments } = convertWaveformToUI(waveformData);
      setWaveformPeaks(peaks);
      setWaveformQualitySegments(qualitySegments);
    } catch (error) {
      console.error('Error loading waveform:', error);
      // Fallback to mock on error
      setWaveformPeaks([]);
      setWaveformQualitySegments([]);
    } finally {
      setIsLoadingWaveform(false);
    }
  }, [getAccessToken]);

  const loadMetrics = useCallback(async (coachingId: string) => {
    const token = await getAccessToken();
    if (!token) return;

    // Load metrics (don't block on failure)
    setIsLoadingMetrics(true);
    try {
      const detailedMetrics = await apiService.getDetailedMetrics(coachingId, token);
      setMetrics(detailedMetrics);
    } catch (error) {
      console.error('Error loading detailed metrics (non-blocking):', error);
      // Set default metrics so UI can still render
      setMetrics(null);
    } finally {
      setIsLoadingMetrics(false);
    }

    // Load transcript and waveform independently (in parallel)
    loadTranscript(coachingId);
    loadWaveform(coachingId);

    // Always switch to analysis view
    setActiveView('analysis');
  }, [getAccessToken, loadTranscript, loadWaveform]);

  // Poll for processing status
  useEffect(() => {
    if (!currentCoachingId || processingStatus === 'completed' || processingStatus === 'failed') {
      return;
    }

    const pollStatus = async () => {
      try {
        const token = await getAccessToken();
        if (!token) return;

        const status = await apiService.getCoachingStatus(currentCoachingId, token);
        setProcessingStatus(status.status);

        if (status.status === 'completed') {
          // Load metrics once processing is complete
          loadMetrics(currentCoachingId);
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    };

    const interval = setInterval(pollStatus, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [currentCoachingId, processingStatus, getAccessToken, loadMetrics]);

  const handleFileUpload = async (file: File) => {
    try {
      setIsUploading(true);
      setUploadError(null);
      const token = await getAccessToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await apiService.uploadAudio(file, token);
      setCurrentCoachingId(response.coaching_id);
      setProcessingStatus(response.status);

      // Show processing message
      alert('Audio uploaded successfully! Processing...');
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks: BlobPart[] = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });

        await handleFileUpload(audioFile);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Store mediaRecorder in window for access
      (window as any).currentRecorder = mediaRecorder;
    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('Please allow microphone access to record');
    }
  };

  const handleStopRecording = () => {
    if ((window as any).currentRecorder) {
      (window as any).currentRecorder.stop();
      setIsRecording(false);
    }
  };

  // Simulate recording timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Login screen
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl font-semibold text-gray-700">Loading...</div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Speech Coach AI</h1>
            <p className="text-gray-600">Master American English communication for sales success</p>
          </div>

          <button
            onClick={signInWithGoogle}
            className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>

          <div className="mt-6 text-sm text-gray-500 text-center">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </div>
        </div>
      </div>
    );
  }

  const NavButton = ({ view, label }: { view: ViewType; label: string }) => (
    <button
      onClick={() => setActiveView(view)}
      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
        activeView === view
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
    >
      {label}
    </button>
  );

  const playSegmentAudio = (segment: TranscriptSegment, version: PlayingVersion) => {
    // Stop current audio if playing
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    }

    const audioUrl = version === 'original' ? segment.original_audio_url : segment.improved_audio_url;

    if (!audioUrl) {
      console.warn('No audio URL available for this segment');
      return;
    }

    const audio = new Audio(audioUrl);

    audio.onplay = () => {
      setPlayingSegment(segment.id);
      setPlayingVersion(version);
    };

    audio.onended = () => {
      setPlayingSegment(null);
      setPlayingVersion(null);
    };

    audio.onerror = (e) => {
      console.error('Audio playback error:', e);
      setPlayingSegment(null);
      setPlayingVersion(null);
    };

    setCurrentAudio(audio);
    audio.play();
  };

  const stopAudio = () => {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    }
    setPlayingSegment(null);
    setPlayingVersion(null);
  };

  const SegmentPlayer = ({ segment }: { segment: TranscriptSegment }) => {
    const isPlaying = playingSegment === segment.id;
    const isHovered = hoveredSegment === segment.id;

    const getBorderColor = () => {
      if (segment.score === 'warning') return 'border-l-yellow-500';
      if (segment.score === 'error') return 'border-l-red-500';
      return 'border-l-green-500';
    };

    const getBgColor = () => {
      if (isPlaying) return 'bg-blue-50';
      if (isHovered) return 'bg-gray-50';
      return 'bg-white';
    };

    return (
      <div
        className={`${getBgColor()} border-l-4 ${getBorderColor()} p-4 rounded transition-colors cursor-pointer mb-3`}
        onMouseEnter={() => setHoveredSegment(segment.id)}
        onMouseLeave={() => setHoveredSegment(null)}
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 text-xs text-gray-500 font-mono mt-1 w-12">
            {segment.startTime}
          </div>

          <div className="flex-1">
            <p className="text-gray-900 mb-2 leading-relaxed">{segment.text}</p>

            {segment.issue && (
              <div className="flex items-center gap-2 text-sm text-yellow-700 bg-yellow-50 px-3 py-1.5 rounded mb-3">
                <AlertCircle className="w-4 h-4" />
                <span>{segment.issueText}</span>
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (isPlaying && playingVersion === 'original') {
                    stopAudio();
                  } else {
                    playSegmentAudio(segment, 'original');
                  }
                }}
                disabled={!segment.original_audio_url}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  isPlaying && playingVersion === 'original'
                    ? 'bg-blue-600 text-white'
                    : segment.original_audio_url
                    ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                {isPlaying && playingVersion === 'original' ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Your Version
              </button>

              <button
                onClick={() => {
                  if (isPlaying && playingVersion === 'improved') {
                    stopAudio();
                  } else {
                    playSegmentAudio(segment, 'improved');
                  }
                }}
                disabled={!segment.improved_audio_url}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  isPlaying && playingVersion === 'improved'
                    ? 'bg-green-600 text-white'
                    : segment.improved_audio_url
                    ? 'bg-green-50 text-green-700 hover:bg-green-100'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                {isPlaying && playingVersion === 'improved' ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Improved Version
              </button>

              <button
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium bg-gray-50 text-gray-600 hover:bg-gray-100"
                title="Compare side by side"
              >
                <RotateCcw className="w-4 h-4" />
                Compare
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const WaveformView = () => {
    const getSegmentColor = (time: number): string => {
      const segment = waveformQualitySegments.find(
        (s) => time >= s.start_time && time < s.end_time
      );
      return segment?.color || '#10b981'; // Default to green
    };

    const renderWaveform = () => {
      if (isLoadingWaveform) {
        return (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <div className="text-sm text-gray-600">Loading waveform...</div>
          </div>
        );
      }

      if (waveformPeaks.length === 0) {
        // Fallback to mock visualization
        return (
          <>
            {mockWaveformSegments.map((seg, idx) => (
              <div
                key={idx}
                className={`${seg.color} rounded-t cursor-pointer hover:opacity-80 transition-opacity`}
                style={{ width: seg.width, height: seg.height }}
              />
            ))}
          </>
        );
      }

      // Render actual waveform from API data
      const duration = waveformQualitySegments.length > 0
        ? Math.max(...waveformQualitySegments.map(s => s.end_time))
        : 20;

      return (
        <>
          {waveformPeaks.slice(0, 100).map((peak, idx) => {
            const time = (idx / 100) * duration;
            const color = getSegmentColor(time);
            const height = Math.max(10, peak * 100);

            return (
              <div
                key={idx}
                className="rounded-t cursor-pointer hover:opacity-80 transition-opacity flex-1"
                style={{
                  height: `${height}%`,
                  backgroundColor: color,
                  minWidth: '2px',
                }}
              />
            );
          })}
        </>
      );
    };

    return (
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Audio Waveform</h3>
          <div className="flex gap-2">
            <button className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200">
              Full Recording
            </button>
            <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
              Segment View
            </button>
          </div>
        </div>

        <div className="relative bg-gray-50 rounded-lg p-4 h-32 flex items-end gap-px">
          {renderWaveform()}
        </div>

        <div className="flex items-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#10b981' }}></div>
            <span className="text-gray-600">Good delivery</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#f59e0b' }}></div>
            <span className="text-gray-600">Needs improvement</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#3b82f6' }}></div>
            <span className="text-gray-600">Low confidence</span>
          </div>
        </div>
      </div>
    );
  };

  const UploadView = () => (
    <div className="max-w-4xl mx-auto">
      {uploadError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <strong>Error:</strong> {uploadError}
        </div>
      )}

      {processingStatus !== 'idle' && processingStatus !== 'completed' && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <div>
              <div className="font-semibold text-blue-900">Processing your audio...</div>
              <div className="text-sm text-blue-700">Status: {processingStatus}</div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-12 text-center">
        <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <h2 className="text-2xl font-semibold mb-2">Upload or Record Your Sales Call</h2>
        <p className="text-gray-600 mb-6">
          Upload an audio file or record directly from your microphone
        </p>

        {!isRecording && !isUploading ? (
          <div className="flex gap-4 justify-center">
            <label className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer">
              <Upload className="w-5 h-5" />
              Upload Audio
              <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleFileUpload(file);
                  }
                }}
              />
            </label>
            <button
              onClick={handleStartRecording}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Mic className="w-5 h-5" />
              Start Recording
            </button>
          </div>
        ) : isUploading ? (
          <div className="flex items-center justify-center gap-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="text-gray-700">Uploading...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3">
              <div className="relative">
                <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center animate-pulse">
                  <Mic className="w-8 h-8 text-white" />
                </div>
                <div className="absolute inset-0 w-16 h-16 bg-red-600 rounded-full animate-ping opacity-20"></div>
              </div>
              <div className="text-left">
                <div className="text-2xl font-bold text-red-600 font-mono">{formatTime(recordingTime)}</div>
                <div className="text-sm text-gray-600">Recording in progress...</div>
              </div>
            </div>

            <div className="flex gap-3 justify-center">
              <button
                onClick={handleStopRecording}
                className="flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Pause className="w-5 h-5" />
                Stop & Analyze
              </button>
              <button
                onClick={() => {
                  if ((window as any).currentRecorder) {
                    (window as any).currentRecorder.stop();
                  }
                  setIsRecording(false);
                  setRecordingTime(0);
                }}
                className="flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>

            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-900">
                <strong>Tip:</strong> Speak naturally as if you're on a real sales call. We'll analyze your tone, pacing, and delivery.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-6 rounded-lg">
          <MessageSquare className="w-8 h-8 text-blue-600 mb-3" />
          <h3 className="font-semibold mb-2">Transcript Analysis</h3>
          <p className="text-sm text-gray-600">AI-powered speech-to-text with timing</p>
        </div>
        <div className="bg-purple-50 p-6 rounded-lg">
          <TrendingUp className="w-8 h-8 text-purple-600 mb-3" />
          <h3 className="font-semibold mb-2">Vocal Patterns</h3>
          <p className="text-sm text-gray-600">Pitch, pace, and energy analysis</p>
        </div>
        <div className="bg-green-50 p-6 rounded-lg">
          <Volume2 className="w-8 h-8 text-green-600 mb-3" />
          <h3 className="font-semibold mb-2">AI Coaching</h3>
          <p className="text-sm text-gray-600">Personalized delivery improvements</p>
        </div>
      </div>
    </div>
  );

  const AnalysisView = () => {
    if (isLoadingMetrics) {
      return (
        <div className="max-w-6xl mx-auto flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <div className="text-lg text-gray-700">Loading analysis...</div>
          </div>
        </div>
      );
    }

    // Use real metrics if available, otherwise show sample data
    const displayMetrics = metrics?.metrics || {
      overall_score: 7.2,
      pace: { words_per_minute: 165, rating: 'too fast' },
      pitch_variation: { rating: 'good' },
      energy_level: { rating: 'moderate' },
      pause_distribution: { rating: 'needs work' },
    };

    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-semibold">Sales Call Analysis</h2>
              <p className="text-gray-600">
                {currentCoachingId ? `Session: ${currentCoachingId}` : 'Client Demo Call - Jan 13, 2026'} • 0:18 duration
              </p>
            </div>
            <div className="flex gap-2">
              <button className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
                <PlayCircle className="w-5 h-5" />
                Play Full Original
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <PlayCircle className="w-5 h-5" />
                Play Full Improved
              </button>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Overall Score</div>
              <div className="text-3xl font-bold text-blue-600">{displayMetrics.overall_score.toFixed(1)}/10</div>
              <div className="text-xs text-gray-500 mt-1">
                {displayMetrics.overall_score >= 8 ? 'Excellent!' : displayMetrics.overall_score >= 7 ? 'Good progress!' : 'Keep practicing'}
              </div>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Pacing</div>
              <div className="text-3xl font-bold text-yellow-600 capitalize">
                {displayMetrics.pace.rating}
              </div>
              <div className="text-xs text-gray-500 mt-1">{displayMetrics.pace.words_per_minute} wpm avg</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Pitch Variation</div>
              <div className="text-3xl font-bold text-green-600 capitalize">
                {displayMetrics.pitch_variation.rating}
              </div>
              <div className="text-xs text-gray-500 mt-1">Natural range</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Energy Level</div>
              <div className="text-3xl font-bold text-purple-600 capitalize">
                {displayMetrics.energy_level.rating}
              </div>
              <div className="text-xs text-gray-500 mt-1">Could be higher</div>
            </div>
          </div>
        </div>

        <WaveformView />

        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                  Interactive Transcript
                </h3>
                <span className="text-sm text-gray-500">Click any segment to play & compare</span>
              </div>

              {isLoadingTranscript ? (
                <div className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <div className="text-sm text-gray-600">Loading transcript segments...</div>
                </div>
              ) : transcriptSegments.length > 0 ? (
                <div className="space-y-0">
                  {transcriptSegments.map(segment => (
                    <SegmentPlayer key={segment.id} segment={segment} />
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-gray-500">
                  <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <div>No transcript segments available</div>
                </div>
              )}

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                <div className="flex items-start gap-3">
                  <Volume2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-gray-700">
                    <strong className="text-blue-900">Pro Tip:</strong> Practice each yellow segment individually.
                    Listen to the improved version, then record yourself mimicking it. Compare until you match the delivery.
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div
                className="flex items-center justify-between mb-4 cursor-pointer"
                onClick={() => setExpandedSection(expandedSection === 'feedback' ? '' : 'feedback')}
              >
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                  Detailed AI Coaching
                </h3>
                <span className="text-2xl text-gray-400">{expandedSection === 'feedback' ? '−' : '+'}</span>
              </div>

              {expandedSection === 'feedback' && (
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900 mb-1">Speaking Too Quickly (Segment 2)</div>
                      <p className="text-sm text-gray-600 mb-2">
                        You're averaging 180 words per minute in this section. American listeners prefer 130-150 wpm
                        for sales conversations. This makes you sound rushed and harder to follow.
                      </p>
                      <div className="text-sm font-medium text-blue-600">Tip: Add a pause after "platform" and before "and show you"</div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900 mb-1">Weak Sentence Endings (Segment 3)</div>
                      <p className="text-sm text-gray-600 mb-2">
                        Your voice drops off at "five years", making you sound uncertain.
                        Americans expect confident endings, especially on declarative statements.
                      </p>
                      <div className="text-sm font-medium text-blue-600">Tip: Maintain energy through "years" - treat it like an important word</div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900 mb-1">Excellent Opening (Segment 1)</div>
                      <p className="text-sm text-gray-600">
                        Your greeting has perfect pacing and warm tone. This is exactly how American sales professionals
                        open conversations. Keep doing this!
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                Key Metrics
              </h3>

              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Speaking Pace</span>
                    <span className="font-medium">{displayMetrics.pace.words_per_minute} wpm</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-yellow-500" style={{width: '85%'}}></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Target: 130-150 wpm</div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Pitch Variety</span>
                    <span className="font-medium capitalize">{displayMetrics.pitch_variation.rating}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{width: '75%'}}></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Natural variation detected</div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Pause Distribution</span>
                    <span className="font-medium capitalize">{displayMetrics.pause_distribution.rating}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-red-500" style={{width: '45%'}}></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">More pauses recommended</div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Energy Consistency</span>
                    <span className="font-medium capitalize">{displayMetrics.energy_level.rating}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{width: '60%'}}></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Voice drops at sentence ends</div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-100">
              <h3 className="text-lg font-semibold mb-3">Practice Workflow</h3>
              <div className="space-y-2 text-sm text-gray-700">
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-blue-600">1.</span>
                  <span>Play your version of a yellow segment</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-blue-600">2.</span>
                  <span>Listen to the improved version</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-blue-600">3.</span>
                  <span>Record yourself mimicking it</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-blue-600">4.</span>
                  <span>Compare until you match</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6 border border-green-100">
              <h3 className="text-lg font-semibold mb-3">Progress Tracker</h3>
              <div className="mb-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-900">
                <strong>Note:</strong> Progress tracking not available from backend yet.
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-700">This Week</span>
                  <span className="font-semibold text-green-600">+{mockProgressData.thisWeekScore} points</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-700">Calls Analyzed</span>
                  <span className="font-semibold">{mockProgressData.callsAnalyzed}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-700">Segments Practiced</span>
                  <span className="font-semibold text-blue-600">{mockProgressData.segmentsPracticed}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Speech Coach AI</h1>
            <p className="text-gray-600">Master American English communication for sales success</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              {user.email}
            </div>
            <button
              onClick={signOut}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white rounded-lg hover:bg-gray-100 border border-gray-200 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>

        <div className="flex gap-3 mb-8">
          <NavButton view="upload" label="Upload/Record" />
          <NavButton view="analysis" label="Analysis & Coaching" />
        </div>

        {activeView === 'upload' && <UploadView />}
        {activeView === 'analysis' && <AnalysisView />}
      </div>
    </div>
  );
}
