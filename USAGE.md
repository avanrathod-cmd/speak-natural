# Speak-Right Usage Guide

## New Workflow: Extract, Transcribe, and Assess

The `analyze.js` script provides a complete workflow for analyzing audio segments:

### Command Format

```bash
node analyze.js <audio-file> <start-time> <end-time>
```

**Time format:** `mm:ss` (minutes:seconds)

### Examples

```bash
# Analyze first 15 seconds of audio
node analyze.js deven.webm 00:00 00:15

# Analyze a middle segment (1:30 to 2:45)
node analyze.js deven.webm 01:30 02:45

# Works with any audio format
node analyze.js audio.mp3 00:10 00:30
node analyze.js recording.m4a 02:15 03:00
```

### What It Does

1. **Extract Segment** - Cuts out the specified time range from your audio file
2. **Convert to WAV** - Converts to 16kHz mono WAV (optimal for speech recognition)
3. **Transcribe** - Uses Azure Speech to transcribe the audio
4. **Assess Pronunciation** - Uses the transcription as reference text to analyze:
   - Overall pronunciation score
   - Accuracy, fluency, completeness, prosody scores
   - Word-level accuracy and timing
   - Phoneme-level pronunciation details
   - Identifies mispronunciations
5. **Save Results** - Everything organized in `output/` folder

### Output Structure

```
output/
└── <filename>/
    ├── <start>_<end>.wav           # Extracted audio segment
    └── <start>_<end>_analysis.json # Complete analysis results
```

Example:
```
output/
└── deven/
    ├── 00-00_00-15.wav
    └── 00-00_00-15_analysis.json
```

### Analysis Results Include

- **Audio Info**: Sample rate, channels, file size, duration
- **Transcription**: Full text of what was spoken
- **Pronunciation Scores**:
  - Overall pronunciation score (0-100)
  - Accuracy, fluency, completeness, prosody
- **Word Analysis**:
  - Timing for each word (offset and duration)
  - Accuracy score per word
  - Error detection (mispronunciations, omissions, etc.)
- **Phoneme Analysis**: Pronunciation accuracy at sound level
- **Summary Statistics**: Word count, average accuracy, error count

### Requirements

- **ffmpeg** must be installed (for audio extraction)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`
  - Windows: Download from https://ffmpeg.org

- **Azure Speech API** credentials in `.env`

### Tips

- Use shorter segments (10-30 seconds) for focused analysis
- The WAV files are preserved for future reference
- JSON files contain complete detailed results
- Check pronunciation scores to identify areas for improvement
- Words with scores below 70 typically need attention

### Example Output

```
============================================================
ANALYSIS SUMMARY
============================================================

📊 Audio Quality:
  Sample Rate: 16000 Hz
  Channels: 1
  File Size: 468.61 KB

📝 Transcription:
  "If you're starting, this is actually a goldmine for you..."

🎯 Pronunciation Scores:
  Overall: 89.7
  Accuracy: 94.0
  Fluency: 97.0
  Completeness: 98.0
  Prosody: 79.8

📖 Word Count: 46

⚠️  Words with Pronunciation Issues: 1
  - "product": Mispronunciation (Accuracy: 45.0)

============================================================
✅ All files saved to: output/deven/
============================================================
```

## Old Workflow (Full File Analysis)

If you want to analyze an entire audio file without extraction:

```bash
# Basic transcription
node index.js audio.wav

# With custom reference text for pronunciation assessment
node index.js audio.wav "Your reference text here"
```

This will convert non-WAV files automatically and analyze the entire file.
