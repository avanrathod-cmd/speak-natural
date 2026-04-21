/** Dashboard table listing all sales calls with scores and status. */

import { useState, useEffect, useRef } from 'react';
import { Pencil } from 'lucide-react';
import { BillingStatus, RepSummary, SalesCallListItem } from '../types';
import {
  Badge,
  ENGAGEMENT_COLORS,
  SENTIMENT_COLORS,
  scoreColor,
} from './ui';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

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
  showRep,
  reps,
  onClick,
  onSaveName,
}: {
  call: SalesCallListItem;
  showRep?: boolean;
  reps?: RepSummary[];
  onClick: () => void;
  onSaveName: (callId: string, name: string) => Promise<void>;
}) {
  function repLabel() {
    if (!call.rep_id || !reps) return '—';
    const rep = reps.find((r) => r.user_id === call.rep_id);
    return rep?.full_name ?? rep?.email ?? call.rep_id.slice(0, 8);
  }
  const isProcessing = call.status === 'processing';
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  function startEdit(e: React.MouseEvent) {
    e.stopPropagation();
    setEditValue(call.call_name ?? formatCallTitle(call));
    setEditing(true);
  }

  async function commit() {
    const trimmed = editValue.trim();
    setEditing(false);
    if (trimmed && trimmed !== (call.call_name ?? formatCallTitle(call))) {
      await onSaveName(call.call_id, trimmed);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') setEditing(false);
  }

  const displayName = call.call_name ?? formatCallTitle(call);

  return (
    <tr
      className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer
        transition-colors group"
      onClick={onClick}
    >
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          {editing ? (
            <input
              ref={inputRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commit}
              onKeyDown={handleKeyDown}
              onClick={(e) => e.stopPropagation()}
              maxLength={100}
              className="text-sm font-medium text-gray-900 border-b
                border-blue-400 outline-none bg-transparent w-full
                max-w-xs"
            />
          ) : (
            <p className="text-sm font-medium text-gray-900 capitalize">
              {displayName}
            </p>
          )}
          {call.source === 'attendee' && (
            <span className="text-xs font-medium bg-purple-100
              text-purple-700 px-1.5 py-0.5 rounded flex-shrink-0"
            >
              Bot
            </span>
          )}
          {!isProcessing && !editing && (
            <button
              onClick={startEdit}
              className="opacity-0 group-hover:opacity-100 transition-opacity
                text-gray-400 hover:text-gray-600 flex-shrink-0"
              title="Rename"
            >
              <Pencil className="w-3 h-3" />
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatCallDate(call)} · {formatDuration(call)}
        </p>
      </td>
      {showRep && (
        <td className="px-6 py-4 text-center">
          <span className="text-sm text-gray-600">{repLabel()}</span>
        </td>
      )}
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
          <span className="inline-flex items-center gap-1 text-xs px-2
            py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500
              animate-pulse block"
            />
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
  billingStatus,
  onOpenCall,
  onCallNameUpdate,
  onRepFilter,
}: {
  calls: SalesCallListItem[];
  billingStatus?: BillingStatus | null;
  onOpenCall: (call: SalesCallListItem) => void;
  onCallNameUpdate: (callId: string, name: string) => void;
  onRepFilter?: (repId?: string) => void;
}) {
  const { getAccessToken } = useAuth();
  const analyzed = calls.filter((c) => c.status === 'completed').length;
  const processing = calls.filter((c) => c.status === 'processing').length;

  const isAdmin =
    billingStatus?.role === 'owner' || billingStatus?.role === 'manager';

  const [reps, setReps] = useState<RepSummary[]>([]);
  const [selectedRep, setSelectedRep] = useState<string>('');

  useEffect(() => {
    if (!isAdmin) return;
    getAccessToken().then((token) => {
      if (!token) return;
      apiService.getReps(token).then(setReps).catch(console.error);
    });
  }, [isAdmin, getAccessToken]);

  function handleRepChange(repId: string) {
    setSelectedRep(repId);
    onRepFilter?.(repId || undefined);
  }

  function repLabel(rep: RepSummary) {
    return rep.full_name ?? rep.email ?? rep.user_id;
  }

  async function handleSaveName(callId: string, name: string) {
    const token = await getAccessToken();
    if (!token) return;
    try {
      await apiService.updateCall(callId, { call_name: name }, token);
      onCallNameUpdate(callId, name);
    } catch (e) {
      console.error('Failed to rename call:', e);
    }
  }

  const headers = isAdmin
    ? ['Call', 'Rep', 'Rep Score', 'Lead Score', 'Engagement', 'Sentiment']
    : ['Call', 'Rep Score', 'Lead Score', 'Engagement', 'Sentiment'];

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100
      overflow-hidden"
    >
      <div className="px-6 py-5 border-b border-gray-100 flex items-center
        justify-between gap-4"
      >
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            Sales Calls
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {analyzed} analyzed · {processing} processing
          </p>
        </div>
        {isAdmin && reps.length > 0 && (
          <select
            value={selectedRep}
            onChange={(e) => handleRepChange(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5
              outline-none focus:ring-2 focus:ring-blue-500 text-gray-700"
          >
            <option value="">All reps</option>
            {reps.map((r) => (
              <option key={r.user_id} value={r.user_id}>
                {repLabel(r)}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left">
              {headers.map((h, i) => (
                <th
                  key={h}
                  className={`px-6 py-3 text-xs font-medium text-gray-400
                    uppercase tracking-wide ${i >= 1 ? 'text-center' : ''}`}
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
                  colSpan={headers.length}
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
                  showRep={isAdmin}
                  reps={reps}
                  onClick={() => {
                    if (call.status === 'completed') onOpenCall(call);
                  }}
                  onSaveName={handleSaveName}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
