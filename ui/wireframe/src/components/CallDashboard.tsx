/** Dashboard table listing all sales calls with scores and status. */

import { User } from 'lucide-react';
import { SalesCallListItem } from '../types';
import {
  Badge,
  ENGAGEMENT_COLORS,
  SENTIMENT_COLORS,
  scoreColor,
} from './ui';

function formatCallTitle(item: SalesCallListItem): string {
  return item.audio_filename
    ? item.audio_filename.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ')
    : item.call_id;
}

function formatCallDate(item: SalesCallListItem): string {
  if (!item.created_at) return '—';
  return new Date(item.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function formatDuration(item: SalesCallListItem): string {
  if (!item.duration_seconds) return '—';
  const m = Math.floor(item.duration_seconds / 60);
  const s = Math.floor(item.duration_seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function DashboardRow({
  call,
  onClick,
}: {
  call: SalesCallListItem;
  onClick: () => void;
}) {
  const isProcessing = call.status === 'processing';
  return (
    <tr
      className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900 capitalize">
            {formatCallTitle(call)}
          </p>
          {call.source === 'attendee' && (
            <span className="text-xs font-medium bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
              Bot
            </span>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatCallDate(call)} · {formatDuration(call)}
        </p>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
            <User className="w-3.5 h-3.5 text-gray-500" />
          </div>
          <span className="text-sm text-gray-400 italic">—</span>
        </div>
      </td>
      <td className="px-6 py-4 text-center">
        {isProcessing ? (
          <span className="text-xs text-gray-400 italic">Processing…</span>
        ) : (
          <span
            className={`text-sm font-semibold ${scoreColor(call.overall_rep_score ?? 0)}`}
          >
            {call.overall_rep_score ?? '—'}
          </span>
        )}
      </td>
      <td className="px-6 py-4 text-center">
        {isProcessing ? (
          <span className="text-xs text-gray-400 italic">—</span>
        ) : (
          <span
            className={`text-sm font-semibold ${scoreColor(call.lead_score ?? 0)}`}
          >
            {call.lead_score ?? '—'}
          </span>
        )}
      </td>
      <td className="px-6 py-4 text-center">
        {isProcessing ? (
          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse block" />
            Processing
          </span>
        ) : call.engagement_level ? (
          <Badge value={call.engagement_level} map={ENGAGEMENT_COLORS} />
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-6 py-4 text-center">
        {isProcessing ? (
          <span className="text-xs text-gray-400">—</span>
        ) : call.customer_sentiment ? (
          <Badge value={call.customer_sentiment} map={SENTIMENT_COLORS} />
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
    </tr>
  );
}

export function CallDashboard({
  calls,
  onOpenCall,
}: {
  calls: SalesCallListItem[];
  onOpenCall: (call: SalesCallListItem) => void;
}) {
  const analyzed = calls.filter((c) => c.status === 'completed').length;
  const processing = calls.filter((c) => c.status === 'processing').length;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-900">
          Sales Calls
        </h2>
        <p className="text-sm text-gray-400 mt-0.5">
          {analyzed} analyzed · {processing} processing
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left">
              {[
                'Call',
                'Rep',
                'Rep Score',
                'Lead Score',
                'Engagement',
                'Sentiment',
              ].map((h, i) => (
                <th
                  key={h}
                  className={`px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide ${
                    i >= 2 ? 'text-center' : ''
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {calls.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-sm text-gray-400"
                >
                  No calls yet. Upload one to get started.
                </td>
              </tr>
            ) : (
              calls.map((call) => (
                <DashboardRow
                  key={call.call_id}
                  call={call}
                  onClick={() => {
                    if (call.status === 'completed') onOpenCall(call);
                  }}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
