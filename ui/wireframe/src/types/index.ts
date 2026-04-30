// Auth Types
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

// Sales Analyzer Types
export interface SalesCallUploadResponse {
  call_id: string;
  status: string;
}

export interface SalesCallStatus {
  call_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
}

export interface SalesCallListItem {
  call_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  source?: 'manual' | 'attendee';
  error?: string;
  audio_filename?: string;
  call_name?: string;
  created_at?: string;
  duration_seconds?: number;
  overall_rep_score?: number;
  lead_score?: number;
  engagement_level?: 'high' | 'medium' | 'low';
  customer_sentiment?: 'positive' | 'neutral' | 'negative';
  rep_id?: string;
}

// Billing + Team types

export type UserRole = 'owner' | 'manager' | 'rep';

export interface AnalysisQuota {
  quota_minutes: number;
  used_minutes: number;
  remaining_minutes: number;
}

export interface BillingStatus {
  plan: string;
  status: string;
  role: UserRole;
  seat_limit: number;
  seats_used: number;
  period_end: string | null;
  analysis_quota: AnalysisQuota | null;
}

export interface TeamMember {
  user_id: string;
  email: string | null;
  role: UserRole;
  full_name: string | null;
  created_at: string | null;
}

export interface RepSummary {
  user_id: string;
  email: string | null;
  full_name: string | null;
}

export interface InviteInfo {
  org_name: string;
  invited_email: string;
  role: UserRole;
}

export interface KeyMoment {
  time: string;
  type: string;
  note: string;
}

export interface SalesCallAnalysis {
  overall_rep_score: number;
  communication_score: number;
  objection_handling_score: number;
  closing_score: number;
  strengths: string[];
  improvements: string[];
  coaching_tips: string[];
  key_moments: KeyMoment[];
  lead_score: number;
  engagement_level: 'high' | 'medium' | 'low';
  customer_sentiment: 'positive' | 'neutral' | 'negative';
  customer_interests: string[];
  objections_raised: string[];
  buying_signals: string[];
  suggested_next_steps: string[];
}

export interface SalesCallAnalysisResponse {
  call_id: string;
  status: string;
  error?: string;
  overall_rep_score?: number;
  communication_score?: number;
  objection_handling_score?: number;
  closing_score?: number;
  lead_score?: number;
  engagement_level?: string;
  customer_sentiment?: string;
  rep_analysis?: {
    strengths: string[];
    improvements: string[];
    coaching_tips: string[];
    key_moments: KeyMoment[];
  };
  customer_analysis?: {
    customer_interests: string[];
    objections_raised: string[];
    buying_signals: string[];
    suggested_next_steps: string[];
  };
  created_at?: string;
}
