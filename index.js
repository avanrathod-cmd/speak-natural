import SpeechAnalyzer from './speechAnalyzer.js';
import { convertToWav, checkFFmpeg } from './convertAudio.js';
import fs from 'fs';
import path from 'path';

async function main() {
  const analyzer = new SpeechAnalyzer();

  // Get audio file from command line or use default
  let audioFile = process.argv[2] || './audio.wav';
  const referenceText = process.argv[3] || null;

  // Check if file exists
  if (!fs.existsSync(audioFile)) {
    console.error(`❌ Error: Audio file "${audioFile}" not found!`);
    console.log('\nUsage:');
    console.log('  node index.js <audio-file> [reference-text]');
    console.log('\nExamples:');
    console.log('  node index.js audio.wav');
    console.log('  node index.js audio.webm');
    console.log('  node index.js audio.wav "Hello world, how are you?"');
    console.log('\nSupported formats: WAV, WEBM, MP3, M4A, etc.');
    console.log('Non-WAV files will be automatically converted using ffmpeg.');
    console.log('The reference text enables pronunciation assessment.');
    process.exit(1);
  }

  try {
    let wavFile = audioFile;
    let cleanupWav = false;

    // Check if file needs conversion
    const ext = path.extname(audioFile).toLowerCase();
    if (ext !== '.wav') {
      console.log(`📁 Detected ${ext} file. Conversion to WAV required.`);

      // Check if ffmpeg is installed
      const hasFFmpeg = await checkFFmpeg();
      if (!hasFFmpeg) {
        console.error('\n❌ ffmpeg is not installed. Please install it:');
        console.error('  macOS: brew install ffmpeg');
        console.error('  Linux: sudo apt-get install ffmpeg');
        console.error('  Windows: Download from https://ffmpeg.org/download.html');
        process.exit(1);
      }

      // Convert to WAV
      wavFile = await convertToWav(audioFile);
      cleanupWav = true;
    }

    // Perform comprehensive analysis
    const results = await analyzer.comprehensiveAnalysis(wavFile, referenceText);

    // Save results to JSON
    const originalExt = path.extname(audioFile);
    const outputFile = audioFile.replace(originalExt, '_analysis.json');
    fs.writeFileSync(outputFile, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved to: ${outputFile}`);

    // Cleanup converted WAV file if it was created
    if (cleanupWav && fs.existsSync(wavFile)) {
      fs.unlinkSync(wavFile);
      console.log(`🗑️  Temporary WAV file cleaned up`);
    }

  } catch (error) {
    console.error('❌ Analysis failed:', error.message);
    process.exit(1);
  }
}

main();
