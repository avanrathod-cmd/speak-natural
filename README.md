# Speak-Right: Speech Analysis Tool

A comprehensive speech analysis tool using Azure Cognitive Services that performs:
- Speech-to-text transcription
- Pronunciation assessment
- Word-level timing and accuracy
- Phoneme-level analysis
- Audio quality analysis

## Setup

1. Configure your Azure Speech API credentials in `.env`:
```
SPEECH_KEY=your-key-here
SPEECH_REGION=eastus
ENDPOINT=https://eastus.api.cognitive.microsoft.com/
```

2. Install dependencies:
```bash
npm install
```

## Usage

### Basic Transcription
```bash
node index.js audio.wav
```

### With Pronunciation Assessment
```bash
node index.js audio.wav "Hello world, how are you?"
```

The second argument is the reference text to compare against for pronunciation assessment.

## Features

### Audio File Analysis
- File size and format
- Sample rate and bit depth
- Number of channels
- Audio duration

### Speech Recognition
- Accurate transcription
- Overall confidence score
- Word-level timing
- Recognition quality

### Pronunciation Assessment (with reference text)
- Overall pronunciation score
- Accuracy score
- Fluency score
- Completeness score
- Prosody score (intonation and rhythm)

### Word-Level Analysis
- Individual word accuracy
- Timing information (offset and duration)
- Error type detection (omissions, insertions, mispronunciations)
- Confidence scores

### Phoneme-Level Analysis
- Individual phoneme accuracy
- Detailed pronunciation breakdown
- Identification of problematic sounds

## Output

Results are displayed in the console and saved to a JSON file:
- `audio_analysis.json` - Complete analysis results in JSON format

## Analysis Capabilities

The tool provides:
1. **Audio Characteristics**: Technical details about the audio file
2. **Speech Recognition**: Full transcription with confidence scores
3. **Pronunciation Scores**: Multiple metrics for pronunciation quality
4. **Word Analysis**: Timing and accuracy for each word
5. **Phoneme Analysis**: Detailed pronunciation at the sound level
6. **Summary Statistics**: Aggregate metrics and insights

## Example Output

```
=== COMPREHENSIVE SPEECH ANALYSIS ===

📊 AUDIO FILE CHARACTERISTICS:
  File: audio.wav
  Size: 245.32 KB
  Format: PCM
  Channels: 1
  Sample Rate: 16000 Hz
  Duration: 5.23 seconds

🎤 SPEECH RECOGNITION:
  Transcription: "Hello world, how are you?"
  Confidence: 95.23%

📝 PRONUNCIATION ASSESSMENT:
  Overall Pronunciation Score: 87.5
  Accuracy Score: 89.2
  Fluency Score: 85.6
  Completeness Score: 100.0
  Prosody Score: 88.3

📖 WORD-LEVEL ANALYSIS:
  1. "Hello" - Offset: 0.45s, Duration: 420ms, Accuracy: 92.3
  2. "world" - Offset: 0.92s, Duration: 380ms, Accuracy: 85.7
  ...

=== ANALYSIS COMPLETE ===
```
