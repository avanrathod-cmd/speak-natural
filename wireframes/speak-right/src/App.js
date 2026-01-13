import React, { useState } from 'react';
import { PlayCircle, Mic, Upload, TrendingUp, MessageSquare, Volume2, CheckCircle, AlertCircle, Play, Pause, RotateCcw } from 'lucide-react';

export default function SpeechCoachWireframes() {
  const [activeView, setActiveView] = useState('analysis');
  const [expandedSection, setExpandedSection] = useState('feedback');
  const [playingSegment, setPlayingSegment] = useState(null);
  const [playingVersion, setPlayingVersion] = useState(null); // 'original' or 'improved'
  const [hoveredSegment, setHoveredSegment] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  const NavButton = ({ view, label }) => (
    <button
      onClick={() => setActiveView(view)}
      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
        activeView === view
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
    >
      {label}
    </button>
  );

  const handleStartRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      
      // Upload to your backend
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.wav');
      
      const response = await fetch('YOUR_API_URL/upload', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      // Handle response and navigate to analysis view
    };

    mediaRecorder.start();
    setIsRecording(true);
    setRecordingTime(0);
    
    // Store mediaRecorder in state to stop it later
    window.currentRecorder = mediaRecorder;
  } catch (error) {
    console.error('Microphone access denied:', error);
    alert('Please allow microphone access to record');
  }
};

const handleStopRecording = () => {
  if (window.currentRecorder) {
    window.currentRecorder.stop();
    setIsRecording(false);
  }
};

  // Simulate recording timer
  React.useEffect(() => {
    let interval;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const segments = [
    {
      id: 1,
      text: "Hi Sarah, thanks for taking the time today.",
      startTime: "0:00",
      endTime: "0:03",
      issue: null,
      score: "good"
    },
    {
      id: 2,
      text: "I wanted to walk you through our new analytics platform and show you how it can really transform your team's workflow.",
      startTime: "0:03",
      endTime: "0:09",
      issue: "too-fast",
      issueText: "Too fast (180 wpm) - Add pauses",
      score: "warning"
    },
    {
      id: 3,
      text: "We've been working with companies like yours for the past five years.",
      startTime: "0:09",
      endTime: "0:13",
      issue: "weak-ending",
      issueText: "Voice drops at end - maintain energy",
      score: "warning"
    },
    {
      id: 4,
      text: "What I'd love to do is show you a quick demo of how our dashboard works.",
      startTime: "0:13",
      endTime: "0:18",
      issue: null,
      score: "good"
    },
  ];

  const SegmentPlayer = ({ segment }) => {
    const isPlaying = playingSegment === segment.id;
    const isHovered = hoveredSegment === segment.id;
    
    const getBorderColor = () => {
      if (segment.score === 'warning') return 'border-l-yellow-500';
      if (segment.score === 'error') return 'border-l-red-500';
      return 'border-l-green-500';
    };

    const getBgColor = () => {
      if (isPlaying) return 'bg-blue-50';
      if (isHovered) return 'bg-gray-50';
      return 'bg-white';
    };

    return (
      <div 
        className={`${getBgColor()} border-l-4 ${getBorderColor()} p-4 rounded transition-colors cursor-pointer mb-3`}
        onMouseEnter={() => setHoveredSegment(segment.id)}
        onMouseLeave={() => setHoveredSegment(null)}
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 text-xs text-gray-500 font-mono mt-1 w-12">
            {segment.startTime}
          </div>
          
          <div className="flex-1">
            <p className="text-gray-900 mb-2 leading-relaxed">{segment.text}</p>
            
            {segment.issue && (
              <div className="flex items-center gap-2 text-sm text-yellow-700 bg-yellow-50 px-3 py-1.5 rounded mb-3">
                <AlertCircle className="w-4 h-4" />
                <span>{segment.issueText}</span>
              </div>
            )}

            <div className="flex gap-2">
              <button 
                onClick={() => {
                  setPlayingSegment(segment.id);
                  setPlayingVersion('original');
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  isPlaying && playingVersion === 'original'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {isPlaying && playingVersion === 'original' ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Your Version
              </button>
              
              <button 
                onClick={() => {
                  setPlayingSegment(segment.id);
                  setPlayingVersion('improved');
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  isPlaying && playingVersion === 'improved'
                    ? 'bg-green-600 text-white'
                    : 'bg-green-50 text-green-700 hover:bg-green-100'
                }`}
              >
                {isPlaying && playingVersion === 'improved' ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Improved Version
              </button>

              <button
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium bg-gray-50 text-gray-600 hover:bg-gray-100"
                title="Compare side by side"
              >
                <RotateCcw className="w-4 h-4" />
                Compare
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const WaveformView = () => {
    const waveformSegments = [
      { width: '15%', height: '60%', color: 'bg-green-500' },
      { width: '25%', height: '85%', color: 'bg-yellow-500' },
      { width: '20%', height: '70%', color: 'bg-yellow-500' },
      { width: '22%', height: '65%', color: 'bg-green-500' },
      { width: '18%', height: '55%', color: 'bg-green-500' },
    ];

    return (
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Audio Waveform (Click to Play Sections)</h3>
          <div className="flex gap-2">
            <button className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200">
              Full Recording
            </button>
            <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
              Segment View
            </button>
          </div>
        </div>
        
        <div className="relative bg-gray-50 rounded-lg p-4 h-32 flex items-end gap-1">
          {waveformSegments.map((seg, idx) => (
            <div 
              key={idx}
              className={`${seg.color} ${seg.width} rounded-t cursor-pointer hover:opacity-80 transition-opacity`}
              style={{ height: seg.height }}
              onClick={() => {
                setPlayingSegment(idx + 1);
                setPlayingVersion('original');
              }}
            />
          ))}
          
          <div className="absolute bottom-0 left-0 right-0 flex justify-between px-4 pb-2 text-xs text-gray-500 font-mono">
            <span>0:00</span>
            <span>0:05</span>
            <span>0:10</span>
            <span>0:15</span>
            <span>0:18</span>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span className="text-gray-600">Good delivery</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded"></div>
            <span className="text-gray-600">Needs improvement</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span className="text-gray-600">Critical issues</span>
          </div>
        </div>
      </div>
    );
  };

  const UploadView = () => (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-12 text-center">
        <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <h2 className="text-2xl font-semibold mb-2">Upload or Record Your Sales Call</h2>
        <p className="text-gray-600 mb-6">
          Upload an audio file or record directly from your microphone
        </p>
        
        {!isRecording ? (
          <div className="flex gap-4 justify-center">
            <button className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <Upload className="w-5 h-5" />
              Upload Audio
            </button>
            <button 
              onClick={handleStartRecording}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Mic className="w-5 h-5" />
              Start Recording
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3">
              <div className="relative">
                <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center animate-pulse">
                  <Mic className="w-8 h-8 text-white" />
                </div>
                <div className="absolute inset-0 w-16 h-16 bg-red-600 rounded-full animate-ping opacity-20"></div>
              </div>
              <div className="text-left">
                <div className="text-2xl font-bold text-red-600 font-mono">{formatTime(recordingTime)}</div>
                <div className="text-sm text-gray-600">Recording in progress...</div>
              </div>
            </div>
            
            <div className="flex gap-3 justify-center">
              <button 
                onClick={handleStopRecording}
                className="flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Pause className="w-5 h-5" />
                Stop & Analyze
              </button>
              <button 
                onClick={() => {
                  setIsRecording(false);
                  setRecordingTime(0);
                }}
                className="flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>

            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-900">
                💡 <strong>Tip:</strong> Speak naturally as if you're on a real sales call. We'll analyze your tone, pacing, and delivery.
              </p>
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-8 grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-6 rounded-lg">
          <MessageSquare className="w-8 h-8 text-blue-600 mb-3" />
          <h3 className="font-semibold mb-2">Transcript Analysis</h3>
          <p className="text-sm text-gray-600">AI-powered speech-to-text with timing</p>
        </div>
        <div className="bg-purple-50 p-6 rounded-lg">
          <TrendingUp className="w-8 h-8 text-purple-600 mb-3" />
          <h3 className="font-semibold mb-2">Vocal Patterns</h3>
          <p className="text-sm text-gray-600">Pitch, pace, and energy analysis</p>
        </div>
        <div className="bg-green-50 p-6 rounded-lg">
          <Volume2 className="w-8 h-8 text-green-600 mb-3" />
          <h3 className="font-semibold mb-2">AI Coaching</h3>
          <p className="text-sm text-gray-600">Personalized delivery improvements</p>
        </div>
      </div>
    </div>
  );

  const AnalysisView = () => (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-semibold">Sales Call Analysis</h2>
            <p className="text-gray-600">Client Demo Call - Jan 13, 2026 • 0:18 duration</p>
          </div>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
              <PlayCircle className="w-5 h-5" />
              Play Full Original
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <PlayCircle className="w-5 h-5" />
              Play Full Improved
            </button>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">Overall Score</div>
            <div className="text-3xl font-bold text-blue-600">7.2/10</div>
            <div className="text-xs text-gray-500 mt-1">Good progress!</div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">Pacing</div>
            <div className="text-3xl font-bold text-yellow-600">Too Fast</div>
            <div className="text-xs text-gray-500 mt-1">165 wpm avg</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">Pitch Variation</div>
            <div className="text-3xl font-bold text-green-600">Good</div>
            <div className="text-xs text-gray-500 mt-1">Natural range</div>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">Energy Level</div>
            <div className="text-3xl font-bold text-purple-600">Moderate</div>
            <div className="text-xs text-gray-500 mt-1">Could be higher</div>
          </div>
        </div>
      </div>

      <WaveformView />

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-blue-600" />
                Interactive Transcript
              </h3>
              <span className="text-sm text-gray-500">Click any segment to play & compare</span>
            </div>
            
            <div className="space-y-0">
              {segments.map(segment => (
                <SegmentPlayer key={segment.id} segment={segment} />
              ))}
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-start gap-3">
                <Volume2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-gray-700">
                  <strong className="text-blue-900">Pro Tip:</strong> Practice each yellow segment individually. 
                  Listen to the improved version, then record yourself mimicking it. Compare until you match the delivery.
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div 
              className="flex items-center justify-between mb-4 cursor-pointer"
              onClick={() => setExpandedSection(expandedSection === 'feedback' ? '' : 'feedback')}
            >
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-blue-600" />
                Detailed AI Coaching
              </h3>
              <span className="text-2xl text-gray-400">{expandedSection === 'feedback' ? '−' : '+'}</span>
            </div>
            
            {expandedSection === 'feedback' && (
              <div className="space-y-4">
                <div className="flex gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 mb-1">Speaking Too Quickly (Segment 2)</div>
                    <p className="text-sm text-gray-600 mb-2">
                      You're averaging 180 words per minute in this section. American listeners prefer 130-150 wpm 
                      for sales conversations. This makes you sound rushed and harder to follow.
                    </p>
                    <div className="text-sm font-medium text-blue-600">💡 Tip: Add a pause after "platform" and before "and show you"</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 mb-1">Weak Sentence Endings (Segment 3)</div>
                    <p className="text-sm text-gray-600 mb-2">
                      Your voice drops off at "five years", making you sound uncertain. 
                      Americans expect confident endings, especially on declarative statements.
                    </p>
                    <div className="text-sm font-medium text-blue-600">💡 Tip: Maintain energy through "years" - treat it like an important word</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 mb-1">Excellent Opening (Segment 1)</div>
                    <p className="text-sm text-gray-600">
                      Your greeting has perfect pacing and warm tone. This is exactly how American sales professionals 
                      open conversations. Keep doing this!
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              Key Metrics
            </h3>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Speaking Pace</span>
                  <span className="font-medium">165 wpm</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-yellow-500" style={{width: '85%'}}></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">Target: 130-150 wpm</div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Pitch Variety</span>
                  <span className="font-medium">Good</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{width: '75%'}}></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">Natural variation detected</div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Pause Distribution</span>
                  <span className="font-medium">Needs Work</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{width: '45%'}}></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">More pauses recommended</div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Energy Consistency</span>
                  <span className="font-medium">Moderate</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{width: '60%'}}></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">Voice drops at sentence ends</div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-100">
            <h3 className="text-lg font-semibold mb-3">📈 Practice Workflow</h3>
            <div className="space-y-2 text-sm text-gray-700">
              <div className="flex items-start gap-2">
                <span className="font-semibold text-blue-600">1.</span>
                <span>Play your version of a yellow segment</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-semibold text-blue-600">2.</span>
                <span>Listen to the improved version</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-semibold text-blue-600">3.</span>
                <span>Record yourself mimicking it</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-semibold text-blue-600">4.</span>
                <span>Compare until you match</span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6 border border-green-100">
            <h3 className="text-lg font-semibold mb-3">📊 Progress Tracker</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-700">This Week</span>
                <span className="font-semibold text-green-600">+0.8 points</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-700">Calls Analyzed</span>
                <span className="font-semibold">23</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-700">Segments Practiced</span>
                <span className="font-semibold text-blue-600">127</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Speech Coach AI</h1>
          <p className="text-gray-600">Master American English communication for sales success</p>
        </div>

        <div className="flex gap-3 mb-8">
          <NavButton view="upload" label="Upload/Record" />
          <NavButton view="analysis" label="Analysis & Coaching" />
        </div>

        {activeView === 'upload' && <UploadView />}
        {activeView === 'analysis' && <AnalysisView />}
      </div>
    </div>
  );
}