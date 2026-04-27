/** Root component — manages navigation state and renders the active view. */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
} from 'react-router-dom';
import { Phone, Plus, ArrowLeft, UserCircle } from 'lucide-react';
import { CallDashboard } from './components/CallDashboard';
import { UploadView } from './components/UploadView';
import { ProcessingView } from './components/ProcessingView';
import { AnalysisView } from './components/AnalysisView';
import { useAuth } from './contexts/AuthContext';
import { apiService } from './services/api';
import { LandingPage } from './pages/LandingPage';
import { GuestFlowPage } from './pages/GuestFlowPage';
import { ProfilePage } from './pages/ProfilePage';
import { PricingPage } from './pages/PricingPage';
import { BillingPage } from './pages/BillingPage';
import { JoinPage, PENDING_INVITE_KEY } from './pages/JoinPage';
import {
  BillingStatus,
  SalesCallListItem,
  SalesCallAnalysis,
  SalesCallAnalysisResponse,
} from './types';
import './App.css';

function flattenAnalysis(r: SalesCallAnalysisResponse): SalesCallAnalysis {
  return {
    overall_rep_score: r.overall_rep_score ?? 0,
    communication_score: r.communication_score ?? 0,
    objection_handling_score: r.objection_handling_score ?? 0,
    closing_score: r.closing_score ?? 0,
    lead_score: r.lead_score ?? 0,
    engagement_level:
      (r.engagement_level as SalesCallAnalysis['engagement_level']) ??
      'medium',
    customer_sentiment:
      (r.customer_sentiment as SalesCallAnalysis['customer_sentiment']) ??
      'neutral',
    strengths: r.rep_analysis?.strengths ?? [],
    improvements: r.rep_analysis?.improvements ?? [],
    coaching_tips: r.rep_analysis?.coaching_tips ?? [],
    key_moments: r.rep_analysis?.key_moments ?? [],
    customer_interests: r.customer_analysis?.customer_interests ?? [],
    objections_raised: r.customer_analysis?.objections_raised ?? [],
    buying_signals: r.customer_analysis?.buying_signals ?? [],
    suggested_next_steps: r.customer_analysis?.suggested_next_steps ?? [],
  };
}

export default function App() {
  const { getAccessToken, user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [calls, setCalls] = useState<SalesCallListItem[]>([]);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [step, setStep] = useState(0);
  const [processingActive, setProcessingActive] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function handleCallNameUpdate(callId: string, name: string) {
    setCalls((prev) =>
      prev.map((c) =>
        c.call_id === callId ? { ...c, call_name: name } : c,
      ),
    );
  }

  const loadCalls = useCallback(async (repId?: string) => {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const data = await apiService.listSalesCalls(token, repId);
      setCalls(data);
    } catch (e) {
      console.error('Failed to load calls:', e);
    }
  }, [getAccessToken]);

  const loadBillingStatus = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const status = await apiService.getBillingStatus(token);
      setBillingStatus(status);
    } catch (e) {
      console.error('Failed to load billing status:', e);
    }
  }, [getAccessToken]);

  useEffect(() => {
    if (!user) return;
    loadCalls();
    loadBillingStatus();

    // Accept a pending invite carried over from the /join flow
    const pendingToken = localStorage.getItem(PENDING_INVITE_KEY);
    if (pendingToken) {
      getAccessToken().then((token) => {
        if (!token) return;
        apiService
          .acceptInvite(pendingToken, token)
          .catch(console.error)
          .finally(() => localStorage.removeItem(PENDING_INVITE_KEY));
      });
    }
  }, [user, loadCalls, loadBillingStatus, getAccessToken]);

  useEffect(() => {
    if (!user) return;
    const params = new URLSearchParams(window.location.search);
    if (
      params.get('calendar_linked') === 'true' ||
      params.get('zoom_connected') === 'true'
    ) {
      window.history.replaceState({}, '', window.location.pathname);
      navigate('/profile');
    }
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  // Public routes — no auth required
  if (!user) {
    return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/try/*" element={<GuestFlowPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/join/:token" element={<JoinPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  async function handleFile(file: File) {
    setStep(0);
    setProcessingActive(true);
    navigate('/processing');
    const token = await getAccessToken();
    if (!token) {
      setProcessingActive(false);
      navigate('/dashboard');
      return;
    }

    try {
      const { call_id } = await apiService.uploadSalesCall(file, token);
      setStep(1);

      pollRef.current = setInterval(async () => {
        try {
          const status = await apiService.getSalesCallStatus(
            call_id,
            token,
          );
          if (status.status === 'processing') {
            setStep(2);
          } else if (status.status === 'completed') {
            clearInterval(pollRef.current!);
            setStep(3);
            await loadCalls();
            setTimeout(() => {
              setProcessingActive(false);
              navigate(`/calls/${call_id}`);
            }, 400);
          } else if (status.status === 'failed') {
            clearInterval(pollRef.current!);
            console.error('Call processing failed:', status.error);
            setProcessingActive(false);
            navigate('/dashboard');
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 3000);
    } catch (e) {
      console.error('Upload failed:', e);
      setProcessingActive(false);
      navigate('/dashboard');
    }
  }

  function goToDashboard() {
    if (pollRef.current) clearInterval(pollRef.current);
    setProcessingActive(false);
    navigate('/dashboard');
  }

  const onCallsPage = location.pathname === '/dashboard';
  const showBack =
    location.pathname === '/upload' ||
    location.pathname.startsWith('/calls/');

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Phone className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900 leading-none">
            yoursalescoach.ai
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Sales Call Analyzer</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {showBack && (
            <button
              onClick={goToDashboard}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4" />
              Dashboard
            </button>
          )}
          {onCallsPage && (
            <button
              onClick={() => navigate('/upload')}
              className="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
            >
              <Plus className="w-4 h-4" />
              New Analysis
            </button>
          )}
          <button
            onClick={() => navigate('/profile')}
            className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-600"
            title="Profile"
          >
            <UserCircle className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <Routes>
          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />
          <Route
            path="/dashboard"
            element={
              <CallDashboard
                calls={calls}
                billingStatus={billingStatus}
                onOpenCall={(c) => navigate(`/calls/${c.call_id}`)}
                onCallNameUpdate={handleCallNameUpdate}
                onRepFilter={loadCalls}
              />
            }
          />
          <Route
            path="/upload"
            element={<UploadView onFile={handleFile} />}
          />
          <Route
            path="/processing"
            element={
              processingActive ? (
                <ProcessingView step={step} />
              ) : (
                <Navigate to="/dashboard" replace />
              )
            }
          />
          <Route
            path="/calls/:callId"
            element={
              <AnalysisRoute
                calls={calls}
                getAccessToken={getAccessToken}
                onCallNameUpdate={handleCallNameUpdate}
              />
            }
          />
          <Route path="/profile" element={<ProfilePage />} />
          <Route
            path="/pricing"
            element={<PricingPage billingStatus={billingStatus} />}
          />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="/join/:token" element={<JoinPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function AnalysisRoute({
  calls,
  getAccessToken,
  onCallNameUpdate,
}: {
  calls: SalesCallListItem[];
  getAccessToken: () => Promise<string | null>;
  onCallNameUpdate: (callId: string, name: string) => void;
}) {
  const { callId } = useParams<{ callId: string }>();
  const [analysis, setAnalysis] = useState<SalesCallAnalysis | null>(null);

  const selectedCall =
    calls.find((c) => c.call_id === callId) ??
    (callId ? { call_id: callId, status: 'completed' as const } : null);

  useEffect(() => {
    if (!callId) return;
    setAnalysis(null);
    (async () => {
      const token = await getAccessToken();
      if (!token) return;
      try {
        const data = await apiService.getSalesCallAnalysis(callId, token);
        setAnalysis(flattenAnalysis(data));
      } catch (e) {
        console.error('Failed to load analysis:', e);
      }
    })();
  }, [callId, getAccessToken]);

  if (!analysis) {
    return (
      <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-gray-100">
        <p className="text-gray-400 text-sm">Loading analysis…</p>
      </div>
    );
  }

  return (
    <AnalysisView
      analysis={analysis}
      selectedCall={selectedCall}
      onCallNameUpdate={onCallNameUpdate}
    />
  );
}
