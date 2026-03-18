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
    // Returns the pre-signed S3 URL after following the redirect
    const response = await fetch(
      `${API_URL}/sales/calls/${callId}/audio`,
      {
        headers: await this.getHeaders(token),
        redirect: 'follow',
      },
    );
    if (!response.ok) {
      throw new Error(`Failed to get call audio: ${response.statusText}`);
    }
    return response.url;
  }
}

export const apiService = new ApiService();
