/** Shared UI primitives used across sales analyzer views. */

export const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'bg-emerald-100 text-emerald-700',
  neutral: 'bg-gray-100 text-gray-600',
  negative: 'bg-red-100 text-red-700',
};

export const ENGAGEMENT_COLORS: Record<string, string> = {
  high: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-red-100 text-red-700',
};

export const MOMENT_COLORS: Record<string, string> = {
  objection_handled: 'bg-emerald-100 text-emerald-700',
  missed_opportunity: 'bg-red-100 text-red-700',
  strong_close: 'bg-blue-100 text-blue-700',
  rapport_built: 'bg-purple-100 text-purple-700',
};

export const scoreColor = (n: number) =>
  n >= 75 ? 'text-emerald-600' : n >= 50 ? 'text-amber-600' : 'text-red-500';

export const scoreBg = (n: number) =>
  n >= 75 ? 'bg-emerald-500' : n >= 50 ? 'bg-amber-500' : 'bg-red-500';

export function ScoreBar({
  score,
  label,
}: {
  score: number;
  label: string;
}) {
  const color =
    score >= 75
      ? 'bg-emerald-500'
      : score >= 50
      ? 'bg-amber-500'
      : 'bg-red-500';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold text-gray-800">{score}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

export function Badge({
  value,
  map,
}: {
  value: string;
  map: Record<string, string>;
}) {
  return (
    <span
      className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${
        map[value] ?? 'bg-gray-100 text-gray-600'
      }`}
    >
      {value}
    </span>
  );
}
