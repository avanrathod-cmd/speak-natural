import {
  BillingStatus,
  InviteInfo,
  RepSummary,
  SalesCallAnalysisResponse,
  SalesCallListItem,
  SalesCallStatus,
  SalesCallUploadResponse,
  TeamMember,
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

  async listSalesCalls(
    token: string,
    repId?: string,
  ): Promise<SalesCallListItem[]> {
    const url = new URL(`${API_URL}/sales/calls`);
    if (repId) url.searchParams.set('rep_id', repId);
    const response = await fetch(url.toString(), {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) {
      throw new Error(`List calls failed: ${response.statusText}`);
    }
    return response.json();
  }

  async exportCall(callId: string, token: string): Promise<Blob> {
    const response = await fetch(
      `${API_URL}/sales/calls/${callId}/export`,
      { headers: await this.getHeaders(token) },
    );
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    return response.blob();
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

  async updateCall(
    callId: string,
    patch: { call_name: string },
    token: string,
  ): Promise<{ call_id: string; call_name: string }> {
    const response = await fetch(`${API_URL}/sales/calls/${callId}`, {
      method: 'PATCH',
      headers: await this.getHeaders(token),
      body: JSON.stringify(patch),
    });
    if (!response.ok) {
      throw new Error(`Update call failed: ${response.statusText}`);
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

  // ── Billing ─────────────────────────────────────────────────────────────

  async getBillingStatus(token: string): Promise<BillingStatus> {
    const response = await fetch(`${API_URL}/billing/status`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch billing status');
    return response.json();
  }

  async createCheckout(
    plan: string,
    token: string,
  ): Promise<{ checkout_url: string }> {
    const response = await fetch(`${API_URL}/billing/checkout`, {
      method: 'POST',
      headers: await this.getHeaders(token),
      body: JSON.stringify({ plan }),
    });
    if (!response.ok) throw new Error('Failed to create checkout');
    return response.json();
  }

  async getBillingPortal(
    token: string,
  ): Promise<{ portal_url: string }> {
    const response = await fetch(`${API_URL}/billing/portal`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to get billing portal');
    return response.json();
  }

  // ── Team ─────────────────────────────────────────────────────────────────

  async getTeamMembers(token: string): Promise<TeamMember[]> {
    const response = await fetch(`${API_URL}/team/members`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch team members');
    return response.json();
  }

  async getReps(token: string): Promise<RepSummary[]> {
    const response = await fetch(`${API_URL}/team/reps`, {
      headers: await this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch reps');
    return response.json();
  }

  async inviteMember(
    email: string,
    role: string,
    token: string,
  ): Promise<{ invite_url: string }> {
    const response = await fetch(`${API_URL}/team/invite`, {
      method: 'POST',
      headers: await this.getHeaders(token),
      body: JSON.stringify({ email, role }),
    });
    if (!response.ok) throw new Error('Failed to create invite');
    return response.json();
  }

  async removeMember(userId: string, token: string): Promise<void> {
    const response = await fetch(
      `${API_URL}/team/members/${userId}`,
      { method: 'DELETE', headers: await this.getHeaders(token) },
    );
    if (!response.ok) throw new Error('Failed to remove member');
  }

  async getInviteInfo(inviteToken: string): Promise<InviteInfo> {
    const response = await fetch(
      `${API_URL}/team/invite/${inviteToken}`,
    );
    if (!response.ok) throw new Error('Invite not found or expired');
    return response.json();
  }

  async acceptInvite(
    inviteToken: string,
    token: string,
  ): Promise<void> {
    const response = await fetch(
      `${API_URL}/team/accept/${inviteToken}`,
      { method: 'POST', headers: await this.getHeaders(token) },
    );
    if (!response.ok) throw new Error('Failed to accept invite');
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
