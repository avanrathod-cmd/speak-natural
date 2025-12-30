import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * Parse mm:ss timestamp to seconds
 */
export function parseTimestamp(timestamp) {
  const parts = timestamp.split(':');
  if (parts.length !== 2) {
    throw new Error(`Invalid timestamp format: ${timestamp}. Expected mm:ss format.`);
  }

  const minutes = parseInt(parts[0], 10);
  const seconds = parseInt(parts[1], 10);

  if (isNaN(minutes) || isNaN(seconds)) {
    throw new Error(`Invalid timestamp format: ${timestamp}. Minutes and seconds must be numbers.`);
  }

  if (seconds >= 60) {
    throw new Error(`Invalid seconds in timestamp: ${timestamp}. Seconds must be less than 60.`);
  }

  return minutes * 60 + seconds;
}

/**
 * Format seconds to mm:ss
 */
export function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Extract a segment from audio file and convert to WAV
 */
export async function extractAudioSegment(inputFile, startTime, endTime, outputFile) {
  return new Promise((resolve, reject) => {
    // Check if input file exists
    if (!fs.existsSync(inputFile)) {
      reject(new Error(`Input file not found: ${inputFile}`));
      return;
    }

    // Create output directory if it doesn't exist
    const outputDir = path.dirname(outputFile);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    console.log(`🔄 Extracting segment ${startTime} to ${endTime} from ${inputFile}...`);

    const duration = endTime - startTime;

    // Use ffmpeg to extract segment and convert to WAV
    // -ss: start time
    // -t: duration
    // -acodec pcm_s16le: PCM 16-bit little-endian
    // -ar 16000: 16kHz sample rate (optimal for Azure Speech SDK)
    // -ac 1: mono channel
    const ffmpeg = spawn('ffmpeg', [
      '-ss', startTime.toString(),
      '-t', duration.toString(),
      '-i', inputFile,
      '-acodec', 'pcm_s16le',
      '-ar', '16000',
      '-ac', '1',
      '-y',
      outputFile
    ]);

    let errorOutput = '';

    ffmpeg.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        const stats = fs.statSync(outputFile);
        const sizeKB = (stats.size / 1024).toFixed(2);
        console.log(`✅ Segment extracted: ${outputFile} (${sizeKB} KB)`);
        resolve(outputFile);
      } else {
        reject(new Error(`ffmpeg extraction failed with code ${code}\n${errorOutput}`));
      }
    });

    ffmpeg.on('error', (err) => {
      if (err.code === 'ENOENT') {
        reject(new Error(
          'ffmpeg not found. Please install it:\n' +
          '  macOS: brew install ffmpeg\n' +
          '  Linux: sudo apt-get install ffmpeg\n' +
          '  Windows: Download from https://ffmpeg.org/download.html'
        ));
      } else {
        reject(err);
      }
    });
  });
}

/**
 * Generate output filename for extracted segment
 */
export function generateOutputPath(inputFile, startTimestamp, endTimestamp, baseDir = 'output') {
  const baseName = path.basename(inputFile, path.extname(inputFile));
  const outputDir = path.join(baseDir, baseName);

  // Create safe filename from timestamps
  const safeStart = startTimestamp.replace(':', '-');
  const safeEnd = endTimestamp.replace(':', '-');

  const wavFile = path.join(outputDir, `${safeStart}_${safeEnd}.wav`);
  const jsonFile = path.join(outputDir, `${safeStart}_${safeEnd}_analysis.json`);

  return {
    outputDir,
    wavFile,
    jsonFile,
    baseName,
    startLabel: safeStart,
    endLabel: safeEnd
  };
}

export default {
  parseTimestamp,
  formatTimestamp,
  extractAudioSegment,
  generateOutputPath
};
