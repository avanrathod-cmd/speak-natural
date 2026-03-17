/** Step-by-step processing animation shown while a call is being analyzed. */

import React from 'react';
import { Mic, CheckCircle } from 'lucide-react';

const STEPS = [
  'Uploading audio',
  'Transcribing call',
  'Analyzing performance',
];

export function ProcessingView({ step }: { step: number }) {
  return (
    <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-gray-100">
      <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <Mic className="w-8 h-8 text-blue-600 animate-pulse" />
      </div>
      <h2 className="text-xl font-semibold text-gray-800 mb-8">
        Analyzing your call…
      </h2>
      <div className="space-y-4 max-w-xs mx-auto text-left">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-3">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${
                i < step
                  ? 'bg-emerald-500'
                  : i === step
                  ? 'bg-blue-500 animate-pulse'
                  : 'bg-gray-200'
              }`}
            >
              {i < step ? (
                <CheckCircle className="w-4 h-4 text-white" />
              ) : (
                <span className="w-2 h-2 rounded-full bg-white block" />
              )}
            </div>
            <span
              className={`text-sm ${
                i <= step ? 'text-gray-800' : 'text-gray-400'
              }`}
            >
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
