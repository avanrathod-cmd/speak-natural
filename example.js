import SpeechAnalyzer from './speechAnalyzer.js';

// Example usage showing different analysis modes

async function examples() {
  const analyzer = new SpeechAnalyzer();
  const audioFile = './audio.wav'; // Your audio file

  console.log('=== SPEECH ANALYSIS EXAMPLES ===\n');

  // Example 1: Simple transcription
  console.log('Example 1: Basic Transcription');
  console.log('--------------------------------');
  try {
    const transcriptionResult = await analyzer.transcribe(audioFile);
    console.log('Transcription:', transcriptionResult.transcription);
    console.log('Confidence:', transcriptionResult.confidence);
    console.log('Words:', transcriptionResult.words.length);
  } catch (error) {
    console.error('Error:', error.message);
  }

  // Example 2: Pronunciation assessment with reference text
  console.log('\n\nExample 2: Pronunciation Assessment');
  console.log('------------------------------------');
  const referenceText = "Hello world, how are you today?";
  try {
    const pronunciationResult = await analyzer.analyzeWithPronunciation(
      audioFile,
      referenceText
    );

    console.log('Reference:', referenceText);
    console.log('Spoken:', pronunciationResult.transcription);

    if (pronunciationResult.pronunciationAssessment) {
      const pa = pronunciationResult.pronunciationAssessment;
      console.log('\nScores:');
      console.log('  Pronunciation:', pa.pronunciationScore?.toFixed(2));
      console.log('  Accuracy:', pa.accuracyScore?.toFixed(2));
      console.log('  Fluency:', pa.fluencyScore?.toFixed(2));
      console.log('  Completeness:', pa.completenessScore?.toFixed(2));
      console.log('  Prosody:', pa.prosodyScore?.toFixed(2));
    }

    // Show word errors
    const wordErrors = pronunciationResult.words.filter(
      w => w.errorType && w.errorType !== 'None'
    );
    if (wordErrors.length > 0) {
      console.log('\nWord Errors:');
      wordErrors.forEach(w => {
        console.log(`  - "${w.word}": ${w.errorType}`);
      });
    }
  } catch (error) {
    console.error('Error:', error.message);
  }

  // Example 3: Audio file information
  console.log('\n\nExample 3: Audio File Information');
  console.log('----------------------------------');
  try {
    const audioInfo = analyzer.analyzeAudioFile(audioFile);
    console.log('Duration:', audioInfo.duration, 'seconds');
    console.log('Sample Rate:', audioInfo.sampleRate, 'Hz');
    console.log('Channels:', audioInfo.channels);
    console.log('File Size:', audioInfo.fileSizeKB, 'KB');
  } catch (error) {
    console.error('Error:', error.message);
  }

  // Example 4: Comprehensive analysis (all features)
  console.log('\n\nExample 4: Comprehensive Analysis');
  console.log('----------------------------------');
  console.log('(Run with: node index.js audio.wav "reference text")');
}

examples();
