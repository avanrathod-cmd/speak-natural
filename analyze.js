import SpeechAnalyzer from './speechAnalyzer.js';
import { checkFFmpeg } from './convertAudio.js';
import {
  parseTimestamp,
  extractAudioSegment,
  generateOutputPath
} from './audioExtractor.js';
import fs from 'fs';

async function main() {
  // Parse command line arguments
  const audioFile = process.argv[2];
  const startTimestamp = process.argv[3];
  const endTimestamp = process.argv[4];

  // Validate arguments
  if (!audioFile || !startTimestamp || !endTimestamp) {
    console.error('❌ Missing required arguments!\n');
    console.log('Usage:');
    console.log('  node analyze.js <audio-file> <start-time> <end-time>');
    console.log('\nExamples:');
    console.log('  node analyze.js deven.webm 00:15 00:30');
    console.log('  node analyze.js audio.mp3 01:23 02:45');
    console.log('\nTime format: mm:ss');
    console.log('\nWorkflow:');
    console.log('  1. Extract audio segment from specified time range');
    console.log('  2. Convert to WAV format (16kHz mono)');
    console.log('  3. Transcribe the audio');
    console.log('  4. Perform pronunciation assessment using transcription as reference');
    console.log('  5. Save all files to output/<filename>/ directory');
    process.exit(1);
  }

  // Check if file exists
  if (!fs.existsSync(audioFile)) {
    console.error(`❌ Error: Audio file "${audioFile}" not found!`);
    process.exit(1);
  }

  try {
    // Check if ffmpeg is installed
    const hasFFmpeg = await checkFFmpeg();
    if (!hasFFmpeg) {
      console.error('\n❌ ffmpeg is not installed. Please install it:');
      console.error('  macOS: brew install ffmpeg');
      console.error('  Linux: sudo apt-get install ffmpeg');
      console.error('  Windows: Download from https://ffmpeg.org/download.html');
      process.exit(1);
    }

    // Parse timestamps
    console.log('\n📋 PARAMETERS:');
    console.log(`  Input File: ${audioFile}`);
    console.log(`  Start Time: ${startTimestamp}`);
    console.log(`  End Time: ${endTimestamp}`);

    const startSeconds = parseTimestamp(startTimestamp);
    const endSeconds = parseTimestamp(endTimestamp);

    if (endSeconds <= startSeconds) {
      console.error('\n❌ Error: End time must be after start time!');
      process.exit(1);
    }

    const duration = endSeconds - startSeconds;
    console.log(`  Duration: ${duration} seconds\n`);

    // Generate output paths
    const paths = generateOutputPath(audioFile, startTimestamp, endTimestamp);

    console.log('📁 OUTPUT STRUCTURE:');
    console.log(`  Directory: ${paths.outputDir}/`);
    console.log(`  WAV File: ${paths.wavFile}`);
    console.log(`  Analysis: ${paths.jsonFile}\n`);

    // Step 1: Extract audio segment to WAV
    console.log('=== STEP 1: EXTRACT AUDIO SEGMENT ===');
    const wavFile = await extractAudioSegment(
      audioFile,
      startSeconds,
      endSeconds,
      paths.wavFile
    );

    // Step 2: Initial transcription
    console.log('\n=== STEP 2: TRANSCRIBE AUDIO ===');
    const analyzer = new SpeechAnalyzer();

    console.log('🎤 Performing initial transcription...');
    const transcriptionResult = await analyzer.transcribe(wavFile);

    if (transcriptionResult.errors.length > 0) {
      console.error('❌ Transcription errors:');
      transcriptionResult.errors.forEach(error => console.error(`  - ${error}`));
      process.exit(1);
    }

    const transcription = transcriptionResult.transcription;

    if (!transcription || transcription.trim().length === 0) {
      console.error('❌ No speech detected in the audio segment!');
      console.error('   Try a different time range with speech content.');
      process.exit(1);
    }

    console.log('\n✅ TRANSCRIPTION:');
    console.log(`   "${transcription}"\n`);

    // Step 3: Pronunciation assessment using transcription as reference
    console.log('=== STEP 3: PRONUNCIATION ASSESSMENT ===');
    console.log('🔍 Analyzing pronunciation with transcription as reference...\n');

    const assessmentResult = await analyzer.comprehensiveAnalysis(wavFile, transcription);

    // Step 4: Save comprehensive results
    console.log('\n=== STEP 4: SAVE RESULTS ===');

    const finalResults = {
      metadata: {
        sourceFile: audioFile,
        startTime: startTimestamp,
        endTime: endTimestamp,
        durationSeconds: duration,
        extractedWavFile: paths.wavFile,
        timestamp: new Date().toISOString()
      },
      transcription: transcription,
      audioInfo: assessmentResult.audioInfo,
      speechAnalysis: assessmentResult.speechResults
    };

    fs.writeFileSync(paths.jsonFile, JSON.stringify(finalResults, null, 2));
    console.log(`✅ Analysis results saved: ${paths.jsonFile}`);
    console.log(`✅ WAV file preserved: ${paths.wavFile}`);

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log('ANALYSIS SUMMARY');
    console.log('='.repeat(60));

    console.log('\n📊 Audio Quality:');
    console.log(`  Sample Rate: ${finalResults.audioInfo.sampleRate} Hz`);
    console.log(`  Channels: ${finalResults.audioInfo.channels}`);
    console.log(`  File Size: ${finalResults.audioInfo.fileSizeKB} KB`);

    console.log('\n📝 Transcription:');
    console.log(`  "${transcription}"`);

    if (assessmentResult.speechResults.pronunciationAssessment) {
      const pa = assessmentResult.speechResults.pronunciationAssessment;
      console.log('\n🎯 Pronunciation Scores:');
      console.log(`  Overall: ${pa.pronunciationScore?.toFixed(1) || 'N/A'}`);
      console.log(`  Accuracy: ${pa.accuracyScore?.toFixed(1) || 'N/A'}`);
      console.log(`  Fluency: ${pa.fluencyScore?.toFixed(1) || 'N/A'}`);
      console.log(`  Completeness: ${pa.completenessScore?.toFixed(1) || 'N/A'}`);
      console.log(`  Prosody: ${pa.prosodyScore?.toFixed(1) || 'N/A'}`);
    }

    if (assessmentResult.speechResults.words.length > 0) {
      console.log(`\n📖 Word Count: ${assessmentResult.speechResults.words.length}`);

      // Show words with errors
      const errorWords = assessmentResult.speechResults.words.filter(
        w => w.errorType && w.errorType !== 'None'
      );

      if (errorWords.length > 0) {
        console.log(`\n⚠️  Words with Pronunciation Issues: ${errorWords.length}`);
        errorWords.forEach(w => {
          console.log(`  - "${w.word}": ${w.errorType} (Accuracy: ${w.accuracyScore?.toFixed(1) || 'N/A'})`);
        });
      } else {
        console.log('  ✅ No pronunciation errors detected!');
      }
    }

    console.log('\n' + '='.repeat(60));
    console.log(`✅ All files saved to: ${paths.outputDir}/`);
    console.log('='.repeat(60) + '\n');

  } catch (error) {
    console.error('\n❌ Analysis failed:', error.message);
    if (error.stack) {
      console.error('\nStack trace:', error.stack);
    }
    process.exit(1);
  }
}

main();
