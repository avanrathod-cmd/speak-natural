import { TranscriptSegment, ProgressTrackerData, WaveformSegment } from '../types';

// Mock data for Interactive Transcript (not available from backend yet)
export const mockTranscriptSegments: TranscriptSegment[] = [
  {
    id: 1,
    text: "Hi Sarah, thanks for taking the time today.",
    startTime: "0:00",
    endTime: "0:03",
    start_seconds: 0,
    end_seconds: 3,
    issue: null,
    score: "good"
  },
  {
    id: 2,
    text: "I wanted to walk you through our new analytics platform and show you how it can really transform your team's workflow.",
    startTime: "0:03",
    endTime: "0:09",
    start_seconds: 3,
    end_seconds: 9,
    issue: "too-fast",
    issueText: "Too fast (180 wpm) - Add pauses",
    score: "warning",
    tip: 'Add a pause after "platform" and before "and show you"',
    pace_wpm: 180
  },
  {
    id: 3,
    text: "We've been working with companies like yours for the past five years.",
    startTime: "0:09",
    endTime: "0:13",
    start_seconds: 9,
    end_seconds: 13,
    issue: "weak-ending",
    issueText: "Voice drops at end - maintain energy",
    score: "warning",
    tip: 'Maintain energy through "years" - treat it like an important word'
  },
  {
    id: 4,
    text: "What I'd love to do is show you a quick demo of how our dashboard works.",
    startTime: "0:13",
    endTime: "0:18",
    start_seconds: 13,
    end_seconds: 18,
    issue: null,
    score: "good"
  },
];

// Mock data for Progress Tracker (not available from backend yet)
export const mockProgressData: ProgressTrackerData = {
  thisWeekScore: 0.8,
  callsAnalyzed: 23,
  segmentsPracticed: 127,
  weeklyTrend: [
    { week: 'Week 1', score: 6.2 },
    { week: 'Week 2', score: 6.5 },
    { week: 'Week 3', score: 6.9 },
    { week: 'Week 4', score: 7.2 },
  ],
};

// Mock waveform segments for visualization
export const mockWaveformSegments: WaveformSegment[] = [
  { width: '15%', height: '60%', color: 'bg-green-500', startTime: 0, endTime: 3 },
  { width: '25%', height: '85%', color: 'bg-yellow-500', startTime: 3, endTime: 9 },
  { width: '20%', height: '70%', color: 'bg-yellow-500', startTime: 9, endTime: 13 },
  { width: '22%', height: '65%', color: 'bg-green-500', startTime: 13, endTime: 18 },
  { width: '18%', height: '55%', color: 'bg-green-500', startTime: 18, endTime: 22 },
];

// Helper function to convert backend feedback to transcript segments when API is ready
export const convertFeedbackToSegments = (feedback: any): TranscriptSegment[] => {
  // This will be used once the backend provides segment-level feedback
  return feedback.segments?.map((seg: any, index: number) => ({
    id: seg.segment_id || index + 1,
    text: seg.text,
    startTime: formatTime(seg.start_time),
    endTime: formatTime(seg.end_time),
    start_seconds: seg.start_time,
    end_seconds: seg.end_time,
    issue: seg.issue_type || null,
    issueText: seg.issue_description,
    score: seg.severity as 'good' | 'warning' | 'error',
    tip: seg.tip,
    pace_wpm: seg.pace_wpm,
  })) || [];
};

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
