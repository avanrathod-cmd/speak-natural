import {
  CoachingUploadResponse,
  CoachingStatusResponse,
  MetricsResponse,
  DetailedMetricsResponse,
  FeedbackResponse,
  WaveformResponse,
  TranscriptResponse,
  SessionsResponse,
  PracticeThemesResponse,
  PracticeDialogueResponse,
  PracticeAnalyzeResponse,
} from '../types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  private async getHeaders(token?: string): Promise<HeadersInit> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async uploadAudio(audioFile: File, token: string): Promise<CoachingUploadResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);

    const response = await fetch(`${API_URL}/upload-audio`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getCoachingStatus(coachingId: string, token: string): Promise<CoachingStatusResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/status`, {
      headers: await this.getHeaders(token),
    });

    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return response.json();
  }

  async getMetrics(coachingId: string, token: string): Promise<MetricsResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/metrics`, {
      headers: await this.getHeaders(token),
    });

    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }

    return response.json();
  }

  async getDetailedMetrics(coachingId: string, token: string): Promise<DetailedMetricsResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/metrics/detailed`, {
      headers: await this.getHeaders(token),
    });

    if (!response.ok) {
      throw new Error(`Failed to get detailed metrics: ${response.statusText}`);
    }

    return response.json();
  }

  async getFeedback(coachingId: string, token: string): Promise<FeedbackResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/feedback`, {
      headers: await this.getHeaders(token),
    });

    if (!response.ok) {
      throw new Error(`Failed to get feedback: ${response.statusText}`);
    }

    return response.json();
  }

  async getWaveform(coachingId: string, token: string, samples: number = 1000): Promise<WaveformResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/waveform?samples=${samples}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get waveform: ${response.statusText}`);
    }

    return response.json();
  }

  async getTranscript(coachingId: string, token: string, maxSegments: number = 6): Promise<TranscriptResponse> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/transcript?max_segments=${maxSegments}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get transcript: ${response.statusText}`);
    }

    return response.json();
  }

  async getVisualization(coachingId: string, vizType: string, token: string): Promise<Blob> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/visualizations/${vizType}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get visualization: ${response.statusText}`);
    }

    return response.blob();
  }

  async downloadResults(coachingId: string, token: string): Promise<Blob> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/download`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to download results: ${response.statusText}`);
    }

    return response.blob();
  }

  async verifyAuth(token: string): Promise<any> {
    const response = await fetch(`${API_URL}/auth/verify`, {
      headers: await this.getHeaders(token),
    });

    if (!response.ok) {
      throw new Error(`Auth verification failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getSessions(token: string): Promise<SessionsResponse> {
    const response = await fetch(`${API_URL}/sessions`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get sessions: ${response.statusText}`);
    }

    return response.json();
  }

  async getPracticeThemes(token?: string): Promise<PracticeThemesResponse> {
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/practice/themes`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to get practice themes: ${response.statusText}`);
    }

    return response.json();
  }

  async getPracticeDialogue(themeId: string, token?: string): Promise<PracticeDialogueResponse> {
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/practice/dialogue/${themeId}`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to get practice dialogue: ${response.statusText}`);
    }

    return response.json();
  }

  async getFullOriginalAudio(coachingId: string, token: string): Promise<Blob> {
    const response = await fetch(`${API_URL}/coaching/${coachingId}/full_original`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get full original audio: ${response.statusText}`);
    }

    return response.blob();
  }

  async analyzePractice(
    coachingId: string,
    segmentId: number,
    audioBlob: Blob,
    improvedSsml: string,
    token: string
  ): Promise<PracticeAnalyzeResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'practice.webm');
    formData.append('improved_ssml', improvedSsml);

    const response = await fetch(
      `${API_URL}/coaching/${coachingId}/segment/${segmentId}/practice-analyze`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Analysis failed: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService();
