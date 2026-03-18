/** Root component — manages navigation state and renders the active view. */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Phone, Plus, ArrowLeft } from 'lucide-react';
import { CallDashboard } from './components/CallDashboard';
import { UploadView } from './components/UploadView';
import { ProcessingView } from './components/ProcessingView';
import { AnalysisView } from './components/AnalysisView';
import { useAuth } from './contexts/AuthContext';
import { apiService } from './services/api';
import {
  SalesCallListItem,
  SalesCallAnalysis,
  SalesCallAnalysisResponse,
} from './types';
import './App.css';

type Stage = 'dashboard' | 'idle' | 'processing' | 'complete';

function flattenAnalysis(r: SalesCallAnalysisResponse): SalesCallAnalysis {
  return {
    overall_rep_score: r.overall_rep_score ?? 0,
    communication_score: r.communication_score ?? 0,
    objection_handling_score: r.objection_handling_score ?? 0,
    closing_score: r.closing_score ?? 0,
    lead_score: r.lead_score ?? 0,
    engagement_level: (r.engagement_level as SalesCallAnalysis['engagement_level']) ?? 'medium',
    customer_sentiment: (r.customer_sentiment as SalesCallAnalysis['customer_sentiment']) ?? 'neutral',
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

export default function SalesCallAnalyzer() {
  const { getAccessToken, user, loading, signInWithGoogle, signOut } = useAuth();

  const [stage, setStage] = useState<Stage>('dashboard');
  const [step, setStep] = useState(0);
  const [calls, setCalls] = useState<SalesCallListItem[]>([]);
  const [selectedCall, setSelectedCall] = useState<SalesCallListItem | null>(null);
  const [analysis, setAnalysis] = useState<SalesCallAnalysis | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadCalls = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const data = await apiService.listSalesCalls(token);
      setCalls(data);
    } catch (e) {
      console.error('Failed to load calls:', e);
    }
  }, [getAccessToken]);

  useEffect(() => {
    if (user) loadCalls();
  }, [user, loadCalls]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl p-12 shadow-sm border border-gray-100 text-center max-w-sm w-full">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Phone className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mb-1">SpeakRight</h1>
          <p className="text-sm text-gray-500 mb-8">Sales Call Analyzer</p>
          <button
            onClick={signInWithGoogle}
            className="w-full bg-blue-600 text-white py-2.5 px-4 rounded-lg hover:bg-blue-700 font-medium text-sm"
          >
            Sign in with Google
          </button>
        </div>
      </div>
    );
  }

  async function openCall(call: SalesCallListItem) {
    setSelectedCall(call);
    setAnalysis(null);
    setStage('complete');
    const token = await getAccessToken();
    if (!token) return;
    try {
      const data = await apiService.getSalesCallAnalysis(call.call_id, token);
      setAnalysis(flattenAnalysis(data));
    } catch (e) {
      console.error('Failed to load analysis:', e);
    }
  }

  async function handleFile(file: File) {
    setStage('processing');
    setStep(0);
    const token = await getAccessToken();
    if (!token) { setStage('dashboard'); return; }

    try {
      const { call_id } = await apiService.uploadSalesCall(file, token);
      setStep(1);

      pollRef.current = setInterval(async () => {
        try {
          const status = await apiService.getSalesCallStatus(call_id, token);
          if (status.status === 'processing') {
            setStep(2);
          } else if (status.status === 'completed') {
            clearInterval(pollRef.current!);
            setStep(3);
            const data = await apiService.getSalesCallAnalysis(call_id, token);
            setAnalysis(flattenAnalysis(data));
            setSelectedCall({ call_id, status: 'completed' });
            await loadCalls();
            setTimeout(() => setStage('complete'), 400);
          } else if (status.status === 'failed') {
            clearInterval(pollRef.current!);
            console.error('Call processing failed:', status.error);
            setStage('dashboard');
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 3000);
    } catch (e) {
      console.error('Upload failed:', e);
      setStage('dashboard');
    }
  }

  function goToDashboard() {
    if (pollRef.current) clearInterval(pollRef.current);
    setStage('dashboard');
    setSelectedCall(null);
    setAnalysis(null);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Phone className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900 leading-none">
            SpeakRight
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Sales Call Analyzer</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={signOut}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Sign out
          </button>
          {(stage === 'complete' || stage === 'idle') && (
            <button
              onClick={goToDashboard}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4" />
              Dashboard
            </button>
          )}
          {stage === 'dashboard' && (
            <button
              onClick={() => setStage('idle')}
              className="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
            >
              <Plus className="w-4 h-4" />
              New Analysis
            </button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {stage === 'dashboard' && (
          <CallDashboard calls={calls} onOpenCall={openCall} />
        )}
        {stage === 'idle' && (
          <UploadView onFile={handleFile} />
        )}
        {stage === 'processing' && (
          <ProcessingView step={step} />
        )}
        {stage === 'complete' && analysis && (
          <AnalysisView
            analysis={analysis}
            selectedCall={selectedCall}
          />
        )}
        {stage === 'complete' && !analysis && (
          <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-gray-100">
            <p className="text-gray-400 text-sm">Loading analysis…</p>
          </div>
        )}
      </main>
    </div>
  );
}
