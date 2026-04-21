/** Public pricing page — accessible before and after login. */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { BillingStatus } from '../types';

const PLANS = [
  {
    key: 'free',
    name: 'Free',
    price: '$0',
    period: '/month',
    seats: '1 seat',
    features: ['1 manager seat', 'Manual call uploads', 'Full AI analysis'],
  },
  {
    key: 'solo',
    name: 'Solo',
    price: '$39',
    period: '/month',
    seats: '1 rep seat',
    features: [
      '1 rep seat',
      'Auto-recording via bot',
      'Full AI analysis',
      'Transcript download',
    ],
  },
  {
    key: 'team',
    name: 'Team',
    price: '$199',
    period: '/month',
    seats: '5 rep seats',
    features: [
      '5 rep seats',
      'Manager dashboard',
      'Rep performance filters',
      'Team invite links',
      'All Solo features',
    ],
    highlighted: true,
  },
  {
    key: 'unlimited',
    name: 'Unlimited',
    price: '$499',
    period: '/month',
    seats: 'Unlimited rep seats',
    features: [
      'Unlimited rep seats',
      'Unlimited managers',
      'Priority support',
      'All Team features',
    ],
  },
];

export function PricingPage({
  billingStatus,
}: {
  billingStatus?: BillingStatus | null;
}) {
  const { user, getAccessToken } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);

  const currentPlan = billingStatus?.plan ?? 'free';
  const canUpgrade =
    billingStatus?.role === 'owner' || billingStatus?.role === 'manager';

  async function handleUpgrade(planKey: string) {
    if (!user) {
      navigate('/');
      return;
    }
    setLoading(planKey);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const { checkout_url } = await apiService.createCheckout(
        planKey,
        token,
      );
      window.location.href = checkout_url;
    } catch (e) {
      console.error('Checkout failed:', e);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold text-gray-900">
          Simple, transparent pricing
        </h1>
        <p className="text-sm text-gray-500 mt-2">
          Owner seats are always free — you only pay for reps who
          record calls.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = plan.key === currentPlan;
          const isHighlighted = plan.highlighted;

          return (
            <div
              key={plan.key}
              className={`rounded-2xl border p-6 flex flex-col gap-4
                ${isHighlighted
                  ? 'border-blue-500 shadow-md'
                  : 'border-gray-200'
                }
                ${isCurrent ? 'bg-blue-50' : 'bg-white'}`}
            >
              {isHighlighted && (
                <span className="text-xs font-semibold text-blue-600
                  uppercase tracking-wide"
                >
                  Most popular
                </span>
              )}

              <div>
                <p className="text-base font-semibold text-gray-900">
                  {plan.name}
                </p>
                <p className="mt-1">
                  <span className="text-2xl font-bold text-gray-900">
                    {plan.price}
                  </span>
                  <span className="text-sm text-gray-400">
                    {plan.period}
                  </span>
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {plan.seats}
                </p>
              </div>

              <ul className="space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm
                      text-gray-600"
                  >
                    <Check className="w-4 h-4 text-green-500
                      flex-shrink-0 mt-0.5"
                    />
                    {f}
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <span className="text-center text-sm font-medium
                  text-blue-600 bg-blue-100 rounded-lg py-2"
                >
                  Current plan
                </span>
              ) : plan.key === 'free' ? null : !user ? (
                <button
                  onClick={() => navigate('/')}
                  className="w-full text-sm font-medium bg-blue-600
                    text-white rounded-lg py-2 hover:bg-blue-700"
                >
                  Get started
                </button>
              ) : canUpgrade ? (
                <button
                  onClick={() => handleUpgrade(plan.key)}
                  disabled={loading === plan.key}
                  className="w-full text-sm font-medium bg-blue-600
                    text-white rounded-lg py-2 hover:bg-blue-700
                    disabled:opacity-50"
                >
                  {loading === plan.key ? 'Redirecting…' : 'Upgrade →'}
                </button>
              ) : (
                <span className="text-center text-xs text-gray-400">
                  Ask your owner to upgrade
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
