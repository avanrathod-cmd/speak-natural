import { Phone } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SECTIONS = [
  {
    title: '1. Agreement to Terms',
    body: 'By accessing or using YourSalesCoach AI ("Service"), you agree to be bound by these Terms of Service. If you disagree, do not use the Service.',
  },
  {
    title: '2. Use of Service',
    body: 'YourSalesCoach AI provides AI-powered sales call analysis and coaching. You may only use the Service for lawful business purposes.',
  },
  {
    title: '3. User Accounts',
    body: 'You are responsible for maintaining the confidentiality of your account and all activities that occur under it.',
  },
  {
    title: '4. Content',
    body: 'You retain ownership of all call recordings and content you upload. By uploading content, you grant us a limited license to process it solely to provide the Service.',
  },
  {
    title: '5. Subscriptions and Payments',
    body: 'Subscriptions are billed monthly. You may cancel at any time by contacting support@yoursalescoach.ai. No refunds for partial months unless required by law.',
  },
  {
    title: '6. Prohibited Activities',
    body: 'You may not use the Service to violate any laws, infringe on any rights, or upload content you do not have permission to share.',
  },
  {
    title: '7. Limitation of Liability',
    body: 'Our liability is limited to the amount you paid us in the 6 months prior to any claim.',
  },
  {
    title: '8. Dispute Resolution',
    body: 'Disputes will be resolved through informal negotiation first, then arbitration in India with one arbitrator.',
  },
  {
    title: '9. Changes to Terms',
    body: 'We may update these terms and will notify you by email at support@yoursalescoach.ai.',
  },
  {
    title: '10. Contact',
    body: 'Email: support@yoursalescoach.ai\nAvan Rathod, Mumbai, Maharashtra, India',
  },
];

export function TermsPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      <nav className="px-6 py-4 flex items-center border-b border-gray-100">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2"
        >
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Phone className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-gray-900">yoursalescoach.ai</span>
        </button>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Terms of Service
        </h1>
        <p className="text-sm text-gray-500 mb-10">
          Last updated: April 28, 2026
        </p>

        <div className="space-y-8">
          {SECTIONS.map(({ title, body }) => (
            <section key={title}>
              <h2 className="text-base font-semibold text-gray-900 mb-2">
                {title}
              </h2>
              <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
                {body}
              </p>
            </section>
          ))}
        </div>
      </main>

      <footer className="border-t border-gray-100 py-8 mt-16">
        <div className="max-w-3xl mx-auto px-6 flex flex-wrap gap-4 text-xs text-gray-400">
          <span>© 2026 yoursalescoach.ai</span>
          <button
            onClick={() => navigate('/privacy')}
            className="hover:text-gray-600"
          >
            Privacy Policy
          </button>
          <button
            onClick={() => navigate('/terms')}
            className="hover:text-gray-600"
          >
            Terms of Service
          </button>
          <button
            onClick={() => navigate('/cookies')}
            className="hover:text-gray-600"
          >
            Cookie Policy
          </button>
        </div>
      </footer>
    </div>
  );
}
