import {
  CoachingUploadResponse,
  CoachingStatusResponse,
  MetricsResponse,
  DetailedMetricsResponse,
  FeedbackResponse,
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
}

export const apiService = new ApiService();
