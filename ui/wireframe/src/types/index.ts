// API Response Types
export interface CoachingUploadResponse {
  coaching_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  created_at: string;
}

export interface CoachingStatusResponse {
  coaching_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: string;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface MetricsResponse {
  coaching_id: string;
  overall_score: number;
  pace_wpm: number;
  pitch_variation: 'excellent' | 'good' | 'moderate' | 'needs improvement';
  energy_level: 'good' | 'moderate' | 'low';
  pause_distribution: {
    pause_count: number;
    total_pause_duration: number;
    average_pause: number;
  };
}

export interface DetailedMetricsResponse {
  coaching_id: string;
  metrics: {
    overall_score: number;
    pace: {
      words_per_minute: number;
      rating: string;
      definition: string;
    };
    pitch_variation: {
      range_hz: number;
      std_hz: number;
      rating: string;
      definition: string;
    };
    energy_level: {
      intensity_mean_db: number;
      intensity_std_db: number;
      rating: string;
      definition: string;
    };
    pause_distribution: {
      pause_count: number;
      total_duration_seconds: number;
      average_duration_seconds: number;
      rating: string;
      definition: string;
    };
    filler_words: {
      count: number;
      ratio: number;
      rating: string;
      definition: string;
    };
    voice_quality: {
      harmonics_to_noise_ratio_db: number;
      rating: string;
      definition: string;
    };
    ai_insights?: {
      top_strengths: string[];
      top_improvements: string[];
      overall_impression: string;
      confidence: string;
    };
  };
}

export interface FeedbackResponse {
  coaching_id: string;
  general_feedback: string;
  strong_points: string[];
  improvements: string[];
  segments: FeedbackSegment[];
}

export interface SessionsResponse {
  sessions: SessionItem[];
  count: number;
}

export interface SessionItem {
  coaching_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
}

export interface FeedbackSegment {
  segment_id: number;
  text: string;
  start_time: number;
  end_time: number;
  issue_type?: string;
  issue_description?: string;
  tip?: string;
  severity: 'good' | 'warning' | 'error';
}

// NEW: Waveform API Response
export interface WaveformResponse {
  coaching_id: string;
  duration_seconds: number;
  sample_rate: number;
  waveform_data: {
    peaks: number[];
    sample_count: number;
    sample_interval_ms: number;
  };
  quality_segments: QualitySegment[];
}

export interface QualitySegment {
  start_time: number;
  end_time: number;
  quality: 'good' | 'warning' | 'error';
  color: string;
  reason: string;
}

// NEW: Interactive Transcript API Response
export interface TranscriptResponse {
  coaching_id: string;
  segments: TranscriptSegmentAPI[];
  segment_count: number;
}

export interface TranscriptSegmentAPI {
  segment_id: number;
  start_time: number;
  end_time: number;
  duration: number;
  text: string;
  word_count: number;
  severity: 'good' | 'warning' | 'error';
  severity_score: number;
  quality_score: number;
  is_exemplary: boolean;
  issues: SegmentIssue[];
  primary_issue: SegmentIssue | null;
  metrics: {
    pace_wpm: number;
    filler_ratio: number;
    confidence: number;
  };
  original_audio_url: string;
  improved_audio_url: string;
}

export interface SegmentIssue {
  type: string;
  description: string;
  tip: string;
}

// Frontend-only Types (For UI Display)
export interface TranscriptSegment {
  id: number;
  text: string;
  startTime: string;
  endTime: string;
  start_seconds: number;
  end_seconds: number;
  issue: string | null;
  issueText?: string;
  score: 'good' | 'warning' | 'error';
  tip?: string;
  pace_wpm?: number;
  original_audio_url?: string;
  improved_audio_url?: string;
}

export interface ProgressTrackerData {
  thisWeekScore: number;
  callsAnalyzed: number;
  segmentsPracticed: number;
  weeklyTrend: Array<{
    week: string;
    score: number;
  }>;
}

export interface WaveformSegment {
  width: string;
  height: string;
  color: 'bg-green-500' | 'bg-yellow-500' | 'bg-red-500';
  startTime: number;
  endTime: number;
}

// Supabase Auth Types
export interface User {
  id: string;
  email: string;
  user_metadata: {
    avatar_url?: string;
    full_name?: string;
  };
}

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

// Component State Types
export type ViewType = 'upload' | 'analysis' | 'sessions';
export type PlayingVersion = 'original' | 'improved';

// Practice Theme Types
export interface PracticeTheme {
  id: string;
  name: string;
  description: string;
  icon: 'MessageSquare' | 'TrendingUp' | 'PlayCircle';
}

export interface PracticeThemesResponse {
  themes: PracticeTheme[];
}

export interface PracticeDialogueResponse {
  theme_id: string;
  theme_name: string;
  dialogue: string;
  word_count: number;
}
