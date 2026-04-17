import {
  SalesCallUploadResponse,
  SalesCallStatus,
  SalesCallAnalysisResponse,
  SalesCallListItem,
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

  // ── Sales Analyzer ──────────────────────────────────────────────────────

  async uploadSalesCall(
    audioFile: File,
    token: string,
  ): Promise<SalesCallUploadResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    const response = await fetch(`${API_URL}/sales/calls/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getSalesCallStatus(
    callId: string,
    token: string,
  ): Promise<SalesCallStatus> {
    const response = await fetch(
      `${API_URL}/sales/calls/${callId}/status`,
      { headers: await this.getHeaders(token) },
    );
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getSalesCallAnalysis(
    callId: string,
    token: string,
  ): Promise<SalesCallAnalysisResponse> {
    const response = await fetch(
      `${API_URL}/sales/calls/${callId}/analysis`,
      { headers: await this.getHeaders(token) },
    );
    if (!response.ok) {
      throw new Error(`Analysis fetch failed: ${response.statusText}`);
    }
    return response.json();
  }

  async listSalesCalls(token: string): Promise<SalesCallListItem[]> {
    const response = await fetch(`${API_URL}/sales/calls`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) {
      throw new Error(`List calls failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getCallAudio(callId: string, token: string): Promise<string> {
    const response = await fetch(
      `${API_URL}/sales/calls/${callId}/audio`,
      { headers: await this.getHeaders(token) },
    );
    if (!response.ok) {
      throw new Error(`Failed to get call audio: ${response.statusText}`);
    }
    const data = await response.json();
    return data.url;
  }

  // ── Zoom OAuth ──────────────────────────────────────────────────────────

  async getZoomStatus(
    token: string,
  ): Promise<{ connected: boolean; connection_id: string | null }> {
    const response = await fetch(`${API_URL}/attendee/zoom/status`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) {
      throw new Error(`Zoom status check failed: ${response.statusText}`);
    }
    return response.json();
  }

  async initZoomOAuth(token: string): Promise<{ url: string }> {
    const response = await fetch(
      `${API_URL}/attendee/auth/zoom/init`,
      { headers: await this.getHeaders(token) },
    );
    if (!response.ok) {
      throw new Error(`Zoom OAuth init failed: ${response.statusText}`);
    }
    return response.json();
  }

  // ── Guest Analysis ───────────────────────────────────────────────────────

  async uploadGuestCall(
    audioFile: File,
  ): Promise<{ job_id: string; status: string }> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    const response = await fetch(
      `${API_URL}/sales/guest/calls/upload`,
      { method: 'POST', body: formData },
    );
    if (!response.ok) {
      throw new Error(`Guest upload failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getGuestCallStatus(
    jobId: string,
  ): Promise<{ job_id: string; status: string; error?: string }> {
    const response = await fetch(
      `${API_URL}/sales/guest/calls/${jobId}/status`,
    );
    if (!response.ok) {
      throw new Error(
        `Guest status check failed: ${response.statusText}`,
      );
    }
    return response.json();
  }

  async getGuestCallAnalysis(jobId: string): Promise<any> {
    const response = await fetch(
      `${API_URL}/sales/guest/calls/${jobId}/analysis`,
    );
    if (!response.ok) {
      throw new Error(
        `Guest analysis fetch failed: ${response.statusText}`,
      );
    }
    return response.json();
  }

  async deleteGuestCall(jobId: string): Promise<void> {
    await fetch(`${API_URL}/sales/guest/calls/${jobId}`, {
      method: 'DELETE',
    });
  }
}

export const apiService = new ApiService();
