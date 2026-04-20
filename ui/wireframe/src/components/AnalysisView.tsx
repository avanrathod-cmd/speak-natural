/**
 * Full analysis results view — banner summary, Rep Performance tab,
 * and Customer / Lead tab.
 */

import React, { useState, useEffect } from 'react';
import {
  CheckCircle,
  TrendingUp,
  AlertCircle,
  ChevronRight,
  Clock,
  User,
  Volume2,
  Download,
} from 'lucide-react';
import { SalesCallAnalysis, SalesCallListItem } from '../types';
import {
  Badge,
  ScoreBar,
  SENTIMENT_COLORS,
  ENGAGEMENT_COLORS,
  MOMENT_COLORS,
  scoreBg,
} from './ui';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

type Tab = 'rep' | 'customer';

type Analysis = SalesCallAnalysis;

function RepTab({ a }: { a: Analysis }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Scores */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-semibold text-gray-800">Performance Scores</h3>
        <ScoreBar score={a.communication_score} label="Communication" />
        <ScoreBar
          score={a.objection_handling_score}
          label="Objection Handling"
        />
        <ScoreBar score={a.closing_score} label="Closing" />
      </div>

      {/* Strengths + Improvements */}
      <div className="space-y-4">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            Strengths
          </h3>
          <ul className="space-y-2">
            {a.strengths.map((s, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-amber-500" />
            Areas to Improve
          </h3>
          <ul className="space-y-2">
            {a.improvements.map((s, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 flex-shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Key Moments */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 md:col-span-2">
        <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-500" />
          Key Moments
        </h3>
        <div className="space-y-3">
          {a.key_moments.map((m, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50"
            >
              <span className="text-xs font-mono bg-gray-200 text-gray-600 px-2 py-1 rounded flex-shrink-0">
                {m.time}
              </span>
              <span
                className={`text-xs px-2 py-1 rounded-full font-medium capitalize flex-shrink-0 ${
                  MOMENT_COLORS[m.type] ?? 'bg-gray-100 text-gray-600'
                }`}
              >
                {m.type.replace(/_/g, ' ')}
              </span>
              <span className="text-sm text-gray-600">{m.note}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Coaching Tips */}
      <div className="bg-amber-50 rounded-2xl p-6 border border-amber-100 md:col-span-2">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          Coaching Tips
        </h3>
        <ol className="space-y-2">
          {a.coaching_tips.map((tip, i) => (
            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="font-semibold text-amber-600 flex-shrink-0">
                {i + 1}.
              </span>
              {tip}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function CustomerTab({ a }: { a: Analysis }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Lead Quality */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-4">Lead Quality</h3>
        <div className="flex items-center gap-4">
          <div
            className={`w-20 h-20 rounded-full flex items-center justify-center font-bold text-white text-2xl flex-shrink-0 ${scoreBg(a.lead_score)}`}
          >
            {a.lead_score}
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Engagement</span>
              <Badge value={a.engagement_level} map={ENGAGEMENT_COLORS} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Sentiment</span>
              <Badge value={a.customer_sentiment} map={SENTIMENT_COLORS} />
            </div>
          </div>
        </div>
      </div>

      {/* Buying Signals */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-500" />
          Buying Signals
        </h3>
        <ul className="space-y-2">
          {a.buying_signals.map((s, i) => (
            <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
              {s}
            </li>
          ))}
        </ul>
      </div>

      {/* Objections */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          Objections Raised
        </h3>
        <ul className="space-y-2">
          {a.objections_raised.map((o, i) => (
            <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-2 flex-shrink-0" />
              {o}
            </li>
          ))}
        </ul>
      </div>

      {/* Customer Interests */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-3">
          Customer Interests
        </h3>
        <div className="flex flex-wrap gap-2">
          {a.customer_interests.map((interest, i) => (
            <span
              key={i}
              className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full"
            >
              {interest}
            </span>
          ))}
        </div>
      </div>

      {/* Next Steps */}
      <div className="bg-emerald-50 rounded-2xl p-6 border border-emerald-100 md:col-span-2">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-emerald-600" />
          Suggested Next Steps
        </h3>
        <ol className="space-y-2">
          {a.suggested_next_steps.map((s, i) => (
            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="font-semibold text-emerald-600 flex-shrink-0">
                {i + 1}.
              </span>
              {s}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function AnalysisView({
  analysis,
  selectedCall,
}: {
  analysis: Analysis;
  selectedCall: SalesCallListItem | null;
}) {
  const [tab, setTab] = useState<Tab>('rep');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioError, setAudioError] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const { getAccessToken } = useAuth();

  async function handleDownload() {
    if (!selectedCall?.call_id) return;
    setDownloading(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const blob = await apiService.exportCall(
        selectedCall.call_id,
        token,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `speaknatural-${selectedCall.call_id}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    if (!selectedCall?.call_id) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getAccessToken();
        if (!token) return;
        const url = await apiService.getCallAudio(
          selectedCall.call_id,
          token,
        );
        if (!cancelled) setAudioUrl(url);
      } catch {
        if (!cancelled) setAudioError(true);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedCall?.call_id, getAccessToken]);

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-blue-600 rounded-2xl p-6 text-white flex items-center justify-between">
        <div>
          {selectedCall?.audio_filename && (
            <p className="text-blue-300 text-xs font-medium mb-2 flex items-center gap-1.5">
              <User className="w-3 h-3" />
              {selectedCall.audio_filename.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ')}
            </p>
          )}
          <p className="text-blue-200 text-sm font-medium mb-1">
            Overall Rep Score
          </p>
          <p className="text-5xl font-bold">{analysis.overall_rep_score}</p>
          <p className="text-blue-200 text-sm mt-1">out of 100</p>
        </div>
        <div className="text-right space-y-2">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-1.5 text-xs text-blue-200 hover:text-white disabled:opacity-50 ml-auto"
          >
            <Download className="w-3.5 h-3.5" />
            {downloading ? 'Downloading…' : 'Download Transcript'}
          </button>
          <div className="flex items-center gap-2 justify-end">
            <span className="text-blue-200 text-sm">Lead</span>
            <span
              className={`text-sm font-semibold px-2 py-0.5 rounded-full ${scoreBg(analysis.lead_score)}`}
            >
              {analysis.lead_score}
            </span>
          </div>
          <div className="flex items-center gap-2 justify-end">
            <span className="text-blue-200 text-sm">Engagement</span>
            <Badge value={analysis.engagement_level} map={ENGAGEMENT_COLORS} />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <span className="text-blue-200 text-sm">Sentiment</span>
            <Badge value={analysis.customer_sentiment} map={SENTIMENT_COLORS} />
          </div>
        </div>
      </div>

      {/* Audio player */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 flex items-center gap-3">
        <Volume2 className="w-4 h-4 text-gray-400 flex-shrink-0" />
        {audioError ? (
          <div className="text-sm text-red-400">Could not load audio.</div>
        ) : audioUrl ? (
          <audio controls src={audioUrl} className="w-full h-8" />
        ) : (
          <div className="text-sm text-gray-400">Loading audio…</div>
        )}
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {(['rep', 'customer'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'rep' ? 'Rep Performance' : 'Customer / Lead'}
          </button>
        ))}
      </div>

      {tab === 'rep' && <RepTab a={analysis} />}
      {tab === 'customer' && <CustomerTab a={analysis} />}
    </div>
  );
}
