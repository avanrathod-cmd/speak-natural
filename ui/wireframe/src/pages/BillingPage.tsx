/** Billing and team management page. */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle,
  Copy,
  ExternalLink,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { BillingStatus, TeamMember } from '../types';

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  solo: 'Solo',
  team: 'Team',
  unlimited: 'Unlimited',
};

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-gray-100 text-gray-600',
  solo: 'bg-blue-100 text-blue-700',
  team: 'bg-purple-100 text-purple-700',
  unlimited: 'bg-green-100 text-green-700',
};

export function BillingPage() {
  const { getAccessToken } = useAuth();
  const navigate = useNavigate();

  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'manager' | 'rep'>('rep');
  const [inviteUrl, setInviteUrl] = useState('');
  const [inviting, setInviting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [upgraded, setUpgraded] = useState(false);

  const isAdmin =
    status?.role === 'owner' || status?.role === 'manager';
  const atSeatLimit =
    status != null && status.seats_used >= status.seat_limit;

  const load = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const [s, m] = await Promise.all([
        apiService.getBillingStatus(token),
        apiService.getTeamMembers(token),
      ]);
      setStatus(s);
      setMembers(m);
    } catch (e) {
      console.error('Failed to load billing:', e);
    }
  }, [getAccessToken]);

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    if (params.get('upgraded') === 'true') {
      setUpgraded(true);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [load]);

  async function handleInvite() {
    const email = inviteEmail.trim();
    if (!email) return;
    setInviting(true);
    setInviteUrl('');
    try {
      const token = await getAccessToken();
      if (!token) return;
      const { invite_url } = await apiService.inviteMember(
        email,
        inviteRole,
        token,
      );
      setInviteUrl(invite_url);
      setInviteEmail('');
    } catch (e) {
      console.error('Invite failed:', e);
    } finally {
      setInviting(false);
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(inviteUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleRemove(userId: string) {
    const token = await getAccessToken();
    if (!token) return;
    try {
      await apiService.removeMember(userId, token);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      setStatus((prev) =>
        prev ? { ...prev, seats_used: prev.seats_used - 1 } : prev,
      );
    } catch (e) {
      console.error('Remove failed:', e);
    }
  }

  async function handlePortal() {
    const token = await getAccessToken();
    if (!token) return;
    try {
      const { portal_url } = await apiService.getBillingPortal(token);
      window.open(portal_url, '_blank');
    } catch (e) {
      console.error('Portal failed:', e);
    }
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    );
  }

  const seatPct =
    status.seat_limit > 0 && status.seat_limit < 9999
      ? Math.min(
          100,
          Math.round((status.seats_used / status.seat_limit) * 100),
        )
      : null;

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

      {upgraded && (
        <div className="mb-4 flex items-center gap-2 text-sm
          text-green-700 bg-green-50 border border-green-200
          rounded-xl px-4 py-3"
        >
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          Plan upgraded successfully!
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm border
        border-gray-100 overflow-hidden"
      >
        {/* Plan */}
        <div className="px-6 py-5 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-400 uppercase
            tracking-wide mb-3"
          >
            Current Plan
          </p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`text-sm font-semibold px-3 py-1 rounded-full
                  ${PLAN_COLORS[status.plan] ?? PLAN_COLORS.free}`}
              >
                {PLAN_LABELS[status.plan] ?? status.plan}
              </span>
              {status.period_end && (
                <span className="text-xs text-gray-400">
                  Renews{' '}
                  {new Date(status.period_end).toLocaleDateString(
                    'en-US',
                    { month: 'short', day: 'numeric', year: 'numeric' },
                  )}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {status.plan !== 'unlimited' && (
                <button
                  onClick={() => navigate('/pricing')}
                  className="text-xs text-blue-600 hover:underline"
                >
                  View plans
                </button>
              )}
              {isAdmin && status.plan !== 'free' && (
                <button
                  onClick={handlePortal}
                  className="flex items-center gap-1 text-xs
                    text-gray-500 hover:text-gray-700"
                >
                  Manage
                  <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {seatPct !== null && (
            <div className="mt-4">
              <div className="flex justify-between text-xs
                text-gray-500 mb-1"
              >
                <span>Seats used</span>
                <span>
                  {status.seats_used} / {status.seat_limit}
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all
                    ${seatPct >= 100
                      ? 'bg-red-500'
                      : seatPct >= 80
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                    }`}
                  style={{ width: `${seatPct}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Team members */}
        <div className="px-6 py-5 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-400 uppercase
            tracking-wide mb-4"
          >
            Team Members
          </p>
          <div className="space-y-3">
            {members.map((m) => (
              <div
                key={m.user_id}
                className="flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {m.full_name ?? m.email ?? m.user_id}
                  </p>
                  {m.full_name && m.email && (
                    <p className="text-xs text-gray-400">{m.email}</p>
                  )}
                  <span className="text-xs text-gray-400 capitalize">
                    {m.role}
                  </span>
                </div>
                {isAdmin && m.role !== 'owner' && (
                  <button
                    onClick={() => handleRemove(m.user_id)}
                    className="text-gray-300 hover:text-red-500
                      transition-colors"
                    title="Remove member"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Invite */}
        {isAdmin && (
          <div className="px-6 py-5 border-b border-gray-100">
            <p className="text-xs font-medium text-gray-400 uppercase
              tracking-wide mb-3"
            >
              Invite Member
            </p>

            {atSeatLimit ? (
              <p className="text-sm text-amber-600">
                Seat limit reached.{' '}
                <button
                  onClick={() => navigate('/pricing')}
                  className="underline"
                >
                  Upgrade
                </button>{' '}
                to invite more members.
              </p>
            ) : (
              <div className="space-y-3">
                <input
                  type="email"
                  placeholder="rep@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full text-sm border border-gray-200
                    rounded-lg px-3 py-2 outline-none
                    focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex items-center gap-2">
                  <select
                    value={inviteRole}
                    onChange={(e) =>
                      setInviteRole(e.target.value as 'manager' | 'rep')
                    }
                    className="text-sm border border-gray-200 rounded-lg
                      px-3 py-2 outline-none focus:ring-2
                      focus:ring-blue-500"
                  >
                    <option value="rep">Rep</option>
                    <option value="manager">Manager</option>
                  </select>
                  <button
                    onClick={handleInvite}
                    disabled={inviting || !inviteEmail.trim()}
                    className="flex-1 text-sm bg-blue-600 text-white
                      rounded-lg py-2 hover:bg-blue-700
                      disabled:opacity-50"
                  >
                    {inviting ? 'Generating…' : 'Get Invite Link'}
                  </button>
                </div>

                {inviteUrl && (
                  <div className="flex items-center gap-2 bg-gray-50
                    border border-gray-200 rounded-lg px-3 py-2"
                  >
                    <p className="text-xs text-gray-600 flex-1 truncate">
                      {inviteUrl}
                    </p>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1 text-xs
                        text-blue-600 hover:text-blue-800 flex-shrink-0"
                    >
                      {copied ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Sign out placeholder */}
        <div className="px-6 py-4" />
      </div>
    </div>
  );
}
