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

// Frontend-only Types (Mock Data)
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
export type ViewType = 'upload' | 'analysis';
export type PlayingVersion = 'original' | 'improved';
