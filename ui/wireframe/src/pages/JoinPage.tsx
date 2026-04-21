/** Invite acceptance page — public route at /join/:token. */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Phone } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { InviteInfo } from '../types';

const PENDING_INVITE_KEY = 'pending_invite_token';

export function JoinPage() {
  const { token } = useParams<{ token: string }>();
  const { user, getAccessToken, signInWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [error, setError] = useState('');
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiService
      .getInviteInfo(token)
      .then(setInfo)
      .catch(() =>
        setError('This invite link is invalid or has expired.'),
      );
  }, [token]);

  // Auto-accept once logged in
  useEffect(() => {
    if (!user || !token) return;
    setAccepting(true);
    getAccessToken()
      .then((t) => (t ? apiService.acceptInvite(token, t) : null))
      .then(() => {
        localStorage.removeItem(PENDING_INVITE_KEY);
        navigate('/dashboard');
      })
      .catch(() => {
        setError('Failed to accept invite. It may have already been used.');
        setAccepting(false);
      });
  }, [user, token, getAccessToken, navigate]);

  function handleSignIn() {
    if (token) localStorage.setItem(PENDING_INVITE_KEY, token);
    signInWithGoogle();
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center
      justify-center px-4"
    >
      <div className="bg-white rounded-2xl shadow-sm border
        border-gray-100 p-8 max-w-sm w-full text-center"
      >
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex
          items-center justify-center mx-auto mb-4"
        >
          <Phone className="w-5 h-5 text-white" />
        </div>

        {error ? (
          <>
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              Invite unavailable
            </h2>
            <p className="text-sm text-gray-500">{error}</p>
          </>
        ) : accepting ? (
          <p className="text-sm text-gray-400">Joining your team…</p>
        ) : info ? (
          <>
            <h2 className="text-base font-semibold text-gray-900 mb-1">
              You've been invited
            </h2>
            <p className="text-sm text-gray-500 mb-1">
              Join{' '}
              <span className="font-medium text-gray-700">
                {info.org_name}
              </span>{' '}
              as a{' '}
              <span className="font-medium text-gray-700">
                {info.role}
              </span>
            </p>
            <p className="text-xs text-gray-400 mb-6">
              {info.invited_email}
            </p>
            {user ? (
              <p className="text-sm text-gray-400">
                Signing you in…
              </p>
            ) : (
              <button
                onClick={handleSignIn}
                className="w-full text-sm bg-blue-600 text-white
                  rounded-lg py-2.5 hover:bg-blue-700 font-medium"
              >
                Create account / Sign in
              </button>
            )}
          </>
        ) : (
          <p className="text-sm text-gray-400">Loading invite…</p>
        )}
      </div>
    </div>
  );
}

export { PENDING_INVITE_KEY };
