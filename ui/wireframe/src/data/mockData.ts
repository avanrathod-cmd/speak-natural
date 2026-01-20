import {
  TranscriptSegment,
  ProgressTrackerData,
  WaveformSegment,
  TranscriptSegmentAPI,
  WaveformResponse,
  QualitySegment
} from '../types';

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

// Helper function to convert API transcript segments to UI format
export const convertTranscriptSegmentsToUI = (apiSegments: TranscriptSegmentAPI[]): TranscriptSegment[] => {
  return apiSegments.map((seg) => ({
    id: seg.segment_id,
    text: seg.text,
    startTime: formatTime(seg.start_time),
    endTime: formatTime(seg.end_time),
    start_seconds: seg.start_time,
    end_seconds: seg.end_time,
    issue: seg.primary_issue?.type || null,
    issueText: seg.primary_issue?.description,
    score: seg.severity,
    tip: seg.primary_issue?.tip,
    pace_wpm: seg.metrics.pace_wpm,
    original_audio_url: seg.original_audio_url,
    improved_audio_url: seg.improved_audio_url,
  }));
};

// Helper function to convert waveform quality segments to UI format
export const convertWaveformToUI = (waveformData: WaveformResponse): {
  peaks: number[];
  qualitySegments: QualitySegment[];
  duration: number;
} => {
  return {
    peaks: waveformData.waveform_data.peaks,
    qualitySegments: waveformData.quality_segments,
    duration: waveformData.duration_seconds,
  };
};

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Practice themes for recording (will come from backend)
export interface PracticeTheme {
  id: string;
  name: string;
  description: string;
  icon: 'MessageSquare' | 'TrendingUp' | 'PlayCircle';
}

export const mockPracticeThemes: PracticeTheme[] = [
  {
    id: 'dialogue',
    name: 'Dialogue Practice',
    description: 'Practice natural conversation and interpersonal communication',
    icon: 'MessageSquare',
  },
  {
    id: 'sales_pitch',
    name: 'Sales Pitch',
    description: 'Deliver a compelling product or service pitch',
    icon: 'TrendingUp',
  },
  {
    id: 'presentation',
    name: 'Presentation',
    description: 'Present ideas clearly and professionally',
    icon: 'PlayCircle',
  },
];

// Practice dialogues with **bold** markers for emphasis words/phrases
// Will be fetched from backend API in production
export const mockPracticeDialogues: Record<string, string> = {
  dialogue: `"I've been thinking about what you said... about making each day count. You know, I used to think that money and status were **everything**. That if I just had enough of both, I'd finally be **happy**. But standing here with you, watching this sunset... I realize I had it all **wrong**.

It's not about what we **have**, it's about what we **feel**. The moments that take your breath away. The people who make you want to be **better**. I spent so long chasing the wrong things that I almost missed what was right in front of me.

**Promise** me something. Promise me that no matter what happens, you'll never let anyone tell you how to **live** your life. That you'll chase your **dreams**, even when they seem impossible. Because life is too **short** to live by someone else's rules.

When I'm with you, I feel like I can do **anything**. Like the whole world is just... **waiting** for us."`,

  sales_pitch: `"Good morning, everyone. Thank you for your time today. I'm here to introduce you to the **ProBook Elite X1** — a laptop that will **transform** how your teams work.

Let me ask you this: How much time does your team lose each day waiting for applications to load? With our **12th generation processor** and **32 gigabytes** of RAM, the ProBook Elite boots in under **eight seconds** and handles even the most demanding workflows **effortlessly**.

But here's what **really** sets us apart. Our **18-hour battery life** means your team stays productive on cross-country flights, client meetings, and everywhere in between. No more hunting for outlets. No more interruptions.

Security? We've got you covered. **Biometric fingerprint** scanning and **hardware-level encryption** protect your sensitive data from day one.

And the best part? We're offering a **30-day risk-free trial** for enterprise clients. Let your team experience the difference **firsthand**.

The ProBook Elite X1. **Power** meets **portability**. Let's discuss how we can equip your organization today."`,

  presentation: `"Good afternoon, board members and leadership team. I'm **pleased** to share our Q3 performance results with you today.

Let me start with the **highlights**. Revenue this quarter reached **47 million dollars**, representing a **23 percent increase** year-over-year. This is our **strongest** quarter in company history.

Our customer acquisition cost decreased by **18 percent**, while customer lifetime value increased by **31 percent**. This improved ratio demonstrates that our strategic investments in product quality are paying **dividends**.

Now, let me address our **challenges** transparently. Supply chain disruptions impacted our European operations, causing a **12 percent shortfall** against regional targets. We've already implemented **dual-sourcing strategies** to prevent future disruptions.

Looking ahead to Q4, our **priorities** are clear: First, expand our enterprise sales team by **40 percent**. Second, launch our new AI-powered analytics platform. Third, enter the **Southeast Asian** market.

The **investments** we make this quarter will position us for **sustained growth** in the coming fiscal year.

Thank you. I welcome your **questions**."`,
};

// Helper to render dialogue text with bold emphasis (use in React components)
// Converts **text** to <strong> elements
export const renderDialogueWithEmphasis = (text: string): { parts: Array<{ text: string; bold: boolean }> } => {
  const parts: Array<{ text: string; bold: boolean }> = [];
  const regex = /\*\*(.*?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push({ text: text.slice(lastIndex, match.index), bold: false });
    }
    // Add the bold text
    parts.push({ text: match[1], bold: true });
    lastIndex = regex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push({ text: text.slice(lastIndex), bold: false });
  }

  return { parts };
};

// Helper to count words excluding markdown syntax
export const countDialogueWords = (text: string): number => {
  const cleanText = text.replace(/\*\*/g, '');
  return cleanText.split(/\s+/).filter(word => word.length > 0).length;
};
