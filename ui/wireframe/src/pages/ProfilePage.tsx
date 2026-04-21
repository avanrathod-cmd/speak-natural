import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, CreditCard } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function ProfilePage() {
  const { user, signOut, getAccessToken } = useAuth();
  const navigate = useNavigate();

  const [calendarLinked, setCalendarLinked] = useState(false);
  const [calendarLinking, setCalendarLinking] = useState(false);
  const [zoomConnected, setZoomConnected] = useState(false);
  const [zoomConnecting, setZoomConnecting] = useState(false);

  const fetchStatus = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const [calResp, zoomData] = await Promise.all([
        fetch('/attendee/status', {
          headers: { Authorization: `Bearer ${token}` },
        }),
        apiService.getZoomStatus(token),
      ]);
      if (calResp.ok) {
        const data = await calResp.json();
        setCalendarLinked(data.linked);
      }
      setZoomConnected(zoomData.connected);
    } catch {
      // non-fatal
    }
  }, [getAccessToken]);

  useEffect(() => {
    fetchStatus();
    const params = new URLSearchParams(window.location.search);
    if (params.get('calendar_linked') === 'true') {
      setCalendarLinked(true);
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (params.get('zoom_connected') === 'true') {
      setZoomConnected(true);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [fetchStatus]);

  const handleLinkCalendar = async () => {
    setCalendarLinking(true);
    try {
      const token = await getAccessToken();
      const resp = await fetch(`${API_URL}/attendee/auth/google/init`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('Failed to start OAuth flow');
      const { url } = await resp.json();
      window.location.href = url;
    } catch (e) {
      console.error('Calendar link error:', e);
      setCalendarLinking(false);
    }
  };

  const handleConnectZoom = async () => {
    setZoomConnecting(true);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error('Not authenticated');
      const { url } = await apiService.initZoomOAuth(token);
      window.location.href = url;
    } catch (e) {
      console.error('Zoom link error:', e);
      setZoomConnecting(false);
    }
  };

  return (
    <div className="max-w-lg">
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-1.5 text-sm text-gray-500
          hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </button>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100
        overflow-hidden"
      >
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Profile</h2>
        </div>

        <div className="px-6 py-5 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-400 uppercase
            tracking-wide mb-1"
          >
            Email
          </p>
          <p className="text-sm text-gray-900">{user?.email}</p>
        </div>

        <div className="px-6 py-5 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-400 uppercase
            tracking-wide mb-4"
          >
            Integrations
          </p>
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Google Calendar
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Auto-join meetings from your calendar
                </p>
              </div>
              {calendarLinked ? (
                <span className="flex items-center gap-1.5 text-xs
                  text-purple-700 bg-purple-50 border border-purple-200
                  px-3 py-1.5 rounded-lg font-medium"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Connected
                </span>
              ) : (
                <button
                  onClick={handleLinkCalendar}
                  disabled={calendarLinking}
                  className="text-sm bg-purple-600 text-white px-4 py-2
                    rounded-lg hover:bg-purple-700 font-medium
                    disabled:opacity-50"
                >
                  {calendarLinking ? 'Redirecting…' : 'Connect'}
                </button>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">Zoom</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {calendarLinked
                    ? 'Auto-record Zoom meetings'
                    : 'Connect Google Calendar first'}
                </p>
              </div>
              {zoomConnected ? (
                <span className="flex items-center gap-1.5 text-xs
                  text-blue-700 bg-blue-50 border border-blue-200
                  px-3 py-1.5 rounded-lg font-medium"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Connected
                </span>
              ) : (
                <button
                  onClick={handleConnectZoom}
                  disabled={zoomConnecting || !calendarLinked}
                  title={
                    !calendarLinked
                      ? 'Connect Google Calendar first'
                      : undefined
                  }
                  className="text-sm bg-blue-600 text-white px-4 py-2
                    rounded-lg hover:bg-blue-700 font-medium
                    disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {zoomConnecting ? 'Redirecting…' : 'Connect'}
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="px-6 py-5 border-b border-gray-100">
          <button
            onClick={() => navigate('/billing')}
            className="flex items-center gap-2 text-sm text-gray-700
              hover:text-gray-900 font-medium"
          >
            <CreditCard className="w-4 h-4" />
            Billing &amp; Team
          </button>
        </div>

        <div className="px-6 py-4">
          <button
            onClick={signOut}
            className="text-sm text-red-500 hover:text-red-700 font-medium"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
