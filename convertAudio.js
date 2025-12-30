import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * Convert webm (or other audio formats) to WAV format required by Azure Speech SDK
 */
export async function convertToWav(inputFile, outputFile = null) {
  return new Promise((resolve, reject) => {
    // Generate output filename if not provided
    if (!outputFile) {
      const ext = path.extname(inputFile);
      outputFile = inputFile.replace(ext, '.wav');
    }

    // Check if input file exists
    if (!fs.existsSync(inputFile)) {
      reject(new Error(`Input file not found: ${inputFile}`));
      return;
    }

    console.log(`🔄 Converting ${inputFile} to WAV format...`);

    // Use ffmpeg to convert to WAV with optimal settings for speech recognition
    // 16kHz mono is ideal for Azure Speech SDK
    const ffmpeg = spawn('ffmpeg', [
      '-i', inputFile,
      '-acodec', 'pcm_s16le',  // PCM 16-bit little-endian
      '-ar', '16000',           // 16kHz sample rate
      '-ac', '1',               // Mono channel
      '-y',                     // Overwrite output file
      outputFile
    ]);

    let errorOutput = '';

    ffmpeg.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`✅ Conversion complete: ${outputFile}`);
        resolve(outputFile);
      } else {
        reject(new Error(`ffmpeg conversion failed with code ${code}\n${errorOutput}`));
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
 * Check if ffmpeg is installed
 */
export async function checkFFmpeg() {
  return new Promise((resolve) => {
    const ffmpeg = spawn('ffmpeg', ['-version']);

    ffmpeg.on('close', (code) => {
      resolve(code === 0);
    });

    ffmpeg.on('error', () => {
      resolve(false);
    });
  });
}

export default { convertToWav, checkFFmpeg };
