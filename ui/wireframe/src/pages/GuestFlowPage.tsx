/**
 * Guest (unauthenticated) analysis flow.
 *
 * Sub-routes (relative to /try):
 *   /            — upload
 *   /processing  — polls status (jobId via navigation state)
 *   /result/:jobId — shows completed analysis + sign-up CTA
 */

import { useEffect, useRef, useState } from 'react';
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';
import { Phone } from 'lucide-react';
import { AnalysisView } from '../components/AnalysisView';
import { ProcessingView } from '../components/ProcessingView';
import { UploadView } from '../components/UploadView';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { SalesCallAnalysis } from '../types';

export function GuestFlowPage() {
  const { signInWithGoogle } = useAuth();

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
        <div className="ml-auto">
          <button
            onClick={signInWithGoogle}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Sign in
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <Routes>
          <Route index element={<GuestUpload />} />
          <Route path="processing" element={<GuestProcessing />} />
          <Route path="result/:jobId" element={<GuestResult />} />
          <Route path="*" element={<Navigate to="/try" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function GuestUpload() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    try {
      const { job_id } = await apiService.uploadGuestCall(file);
      navigate('processing', { state: { jobId: job_id } });
    } catch (e) {
      console.error('Guest upload failed:', e);
      setError('Upload failed. Please try again.');
    }
  }

  return (
    <div className="space-y-4">
      <UploadView onFile={handleFile} />
      {error && (
        <p className="text-center text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}

function GuestProcessing() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const jobId = (location.state as { jobId?: string } | null)?.jobId;

  useEffect(() => {
    if (!jobId) return;

    pollRef.current = setInterval(async () => {
      try {
        const status = await apiService.getGuestCallStatus(jobId);
        if (status.status === 'transcribing') {
          setStep(1);
        } else if (status.status === 'analyzing') {
          setStep(2);
        } else if (status.status === 'completed') {
          clearInterval(pollRef.current!);
          setStep(3);
          setTimeout(
            () => navigate(`/try/result/${jobId}`, { replace: true }),
            400,
          );
        } else if (status.status === 'failed') {
          clearInterval(pollRef.current!);
          navigate('/try', { replace: true });
        }
      } catch (e) {
        console.error('Guest polling error:', e);
      }
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, navigate]);

  if (!jobId) return <Navigate to="/try" replace />;

  return <ProcessingView step={step} />;
}

function GuestResult() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { signInWithGoogle } = useAuth();
  const [analysis, setAnalysis] = useState<SalesCallAnalysis | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    (async () => {
      try {
        const data = await apiService.getGuestCallAnalysis(jobId);
        setAnalysis(data as SalesCallAnalysis);
      } catch (e) {
        console.error('Failed to load guest analysis:', e);
        setError(true);
      }
    })();
  }, [jobId]);

  function analyzeAnother() {
    if (jobId) apiService.deleteGuestCall(jobId).catch(() => {});
    navigate('/try');
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-gray-100">
        <p className="text-gray-500 mb-4">
          Failed to load analysis. Please try again.
        </p>
        <button
          onClick={analyzeAnother}
          className="text-blue-600 text-sm hover:underline"
        >
          ← Try another call
        </button>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-gray-100">
        <p className="text-gray-400 text-sm">Loading analysis…</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-blue-600 rounded-2xl px-6 py-4 flex items-center justify-between gap-6">
        <div>
          <p className="text-white font-medium">
            Save this analysis and track your team's progress
          </p>
          <p className="text-blue-100 text-sm mt-0.5">
            Sign up free to keep your results and analyze more calls
          </p>
        </div>
        <div className="flex-shrink-0 flex items-center gap-3">
          <button
            onClick={analyzeAnother}
            className="text-blue-100 hover:text-white text-sm"
          >
            Analyze another
          </button>
          <button
            onClick={signInWithGoogle}
            className="bg-white text-blue-600 px-4 py-2 rounded-lg font-medium text-sm hover:bg-blue-50"
          >
            Sign up free
          </button>
        </div>
      </div>
      <AnalysisView analysis={analysis} selectedCall={null} />
    </div>
  );
}
