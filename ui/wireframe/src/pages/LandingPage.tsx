/** Public marketing landing page shown to unauthenticated visitors. */

import { BarChart2, MessageSquare, Phone, TrendingUp, Upload, Users, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function LandingPage() {
  const navigate = useNavigate();
  const { signInWithGoogle } = useAuth();

  return (
    <div className="min-h-screen bg-white">

      {/* Nav */}
      <nav className="px-6 py-4 flex items-center border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Phone className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-gray-900">yoursalescoach.ai</span>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <button
            onClick={signInWithGoogle}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Sign in
          </button>
          <button
            onClick={() => navigate('/try')}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
          >
            Try free
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-6">
          Turn every sales call<br />into a coaching opportunity
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          Upload any sales call and get instant AI analysis — rep performance
          scores, customer sentiment, buying signals, and actionable coaching
          tips.
        </p>
        <div className="flex items-center justify-center gap-6">
          <button
            onClick={() => navigate('/try')}
            className="bg-blue-600 text-white px-8 py-3.5 rounded-xl hover:bg-blue-700 font-semibold text-lg"
          >
            Try it free — no signup
          </button>
          <button
            onClick={signInWithGoogle}
            className="text-gray-600 hover:text-gray-900 text-sm font-medium"
          >
            Sign in →
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="grid grid-cols-3 gap-6">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="bg-gray-50 rounded-2xl p-6">
              <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">
            How it works
          </h2>
          <div className="grid grid-cols-3 gap-8">
            {STEPS.map(({ icon: Icon, step, title, desc }) => (
              <div key={step} className="text-center">
                <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm border border-gray-100">
                  <Icon className="w-6 h-6 text-blue-600" />
                </div>
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">
                  Step {step}
                </p>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Ready to see it in action?
        </h2>
        <p className="text-gray-500 mb-8">
          Upload a call right now — no signup, no credit card.
        </p>
        <button
          onClick={() => navigate('/try')}
          className="bg-blue-600 text-white px-8 py-3.5 rounded-xl hover:bg-blue-700 font-semibold text-lg"
        >
          Analyze a call free
        </button>
      </section>

    </div>
  );
}

const FEATURES = [
  {
    icon: BarChart2,
    title: 'Rep performance scoring',
    desc: 'Score every call on communication, objection handling, script adherence, and closing — objectively, every time.',
  },
  {
    icon: Users,
    title: 'Customer insights',
    desc: 'Understand lead quality, engagement level, buying signals, and the objections your reps need to handle better.',
  },
  {
    icon: MessageSquare,
    title: 'Actionable coaching tips',
    desc: 'Get specific, timestamped coaching tips for each call so your reps know exactly what to improve.',
  },
];

const STEPS = [
  {
    icon: Upload,
    step: '1',
    title: 'Upload your call',
    desc: 'Drop in any audio file — MP3, WAV, or M4A.',
  },
  {
    icon: Zap,
    step: '2',
    title: 'AI analyzes it',
    desc: 'We transcribe the call, identify speakers, and run deep analysis.',
  },
  {
    icon: TrendingUp,
    step: '3',
    title: 'Get actionable results',
    desc: 'See scores, insights, and coaching tips in minutes.',
  },
];
