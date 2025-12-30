import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import dotenv from 'dotenv';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

dotenv.config();

class SpeechAnalyzer {
  constructor() {
    this.speechKey = process.env.SPEECH_KEY;
    this.speechRegion = process.env.SPEECH_REGION;

    if (!this.speechKey || !this.speechRegion) {
      throw new Error('SPEECH_KEY and SPEECH_REGION must be set in .env file');
    }
  }

  /**
   * Perform comprehensive speech analysis including transcription and pronunciation assessment
   */
  async analyzeWithPronunciation(audioFile, referenceText = null) {
    return new Promise((resolve, reject) => {
      const audioConfig = sdk.AudioConfig.fromWavFileInput(fs.readFileSync(audioFile));
      const speechConfig = sdk.SpeechConfig.fromSubscription(this.speechKey, this.speechRegion);

      speechConfig.speechRecognitionLanguage = 'en-US';

      let recognizer;

      if (referenceText) {
        // Pronunciation assessment mode
        const pronunciationConfig = new sdk.PronunciationAssessmentConfig(
          referenceText,
          sdk.PronunciationAssessmentGradingSystem.HundredMark,
          sdk.PronunciationAssessmentGranularity.Phoneme,
          true
        );

        pronunciationConfig.enableProsodyAssessment = true;

        recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
        pronunciationConfig.applyTo(recognizer);
      } else {
        // Regular speech recognition
        recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
      }

      const results = {
        transcription: '',
        confidence: null,
        duration: null,
        pronunciationAssessment: null,
        words: [],
        phonemes: [],
        errors: []
      };

      recognizer.recognized = (s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech) {
          results.transcription = e.result.text;

          // Get pronunciation assessment if available
          if (referenceText) {
            const pronunciationResult = sdk.PronunciationAssessmentResult.fromResult(e.result);

            results.pronunciationAssessment = {
              accuracyScore: pronunciationResult.accuracyScore,
              fluencyScore: pronunciationResult.fluencyScore,
              completenessScore: pronunciationResult.completenessScore,
              prosodyScore: pronunciationResult.prosodyScore,
              pronunciationScore: pronunciationResult.pronunciationScore
            };

            // Get word-level details
            const detailResult = JSON.parse(e.result.properties.getProperty(
              sdk.PropertyId.SpeechServiceResponse_JsonResult
            ));

            if (detailResult.NBest && detailResult.NBest[0]) {
              results.confidence = detailResult.NBest[0].Confidence;

              if (detailResult.NBest[0].Words) {
                results.words = detailResult.NBest[0].Words.map(word => ({
                  word: word.Word,
                  accuracyScore: word.PronunciationAssessment?.AccuracyScore,
                  errorType: word.PronunciationAssessment?.ErrorType,
                  offset: word.Offset,
                  duration: word.Duration
                }));

                // Extract phonemes
                detailResult.NBest[0].Words.forEach(word => {
                  if (word.PronunciationAssessment?.Phonemes) {
                    word.PronunciationAssessment.Phonemes.forEach(phoneme => {
                      results.phonemes.push({
                        word: word.Word,
                        phoneme: phoneme.Phoneme,
                        accuracyScore: phoneme.AccuracyScore
                      });
                    });
                  }
                });
              }
            }
          } else {
            // Regular recognition - extract confidence and timing
            const detailResult = JSON.parse(e.result.properties.getProperty(
              sdk.PropertyId.SpeechServiceResponse_JsonResult
            ));

            if (detailResult.NBest && detailResult.NBest[0]) {
              results.confidence = detailResult.NBest[0].Confidence;

              if (detailResult.NBest[0].Words) {
                results.words = detailResult.NBest[0].Words.map(word => ({
                  word: word.Word,
                  offset: word.Offset,
                  duration: word.Duration,
                  confidence: word.Confidence
                }));
              }
            }

            if (e.result.duration) {
              results.duration = e.result.duration / 10000000; // Convert to seconds
            }
          }
        } else if (e.result.reason === sdk.ResultReason.NoMatch) {
          results.errors.push('No speech could be recognized');
        }
      };

      recognizer.canceled = (s, e) => {
        if (e.reason === sdk.CancellationReason.Error) {
          results.errors.push(`Error: ${e.errorDetails}`);
        }
        recognizer.close();
        resolve(results);
      };

      recognizer.sessionStopped = (s, e) => {
        recognizer.close();
        resolve(results);
      };

      recognizer.recognizeOnceAsync(
        result => {
          recognizer.close();
        },
        error => {
          recognizer.close();
          reject(error);
        }
      );
    });
  }

  /**
   * Simple speech-to-text transcription
   */
  async transcribe(audioFile) {
    return this.analyzeWithPronunciation(audioFile, null);
  }

  /**
   * Analyze audio quality and characteristics
   */
  analyzeAudioFile(audioFile) {
    const stats = fs.statSync(audioFile);
    const buffer = fs.readFileSync(audioFile);

    // Parse WAV header
    const audioFormat = buffer.readUInt16LE(20);
    const numChannels = buffer.readUInt16LE(22);
    const sampleRate = buffer.readUInt32LE(24);
    const byteRate = buffer.readUInt32LE(28);
    const bitsPerSample = buffer.readUInt16LE(34);
    const dataSize = buffer.readUInt32LE(40);

    const durationSeconds = dataSize / byteRate;

    return {
      fileSize: stats.size,
      fileSizeKB: (stats.size / 1024).toFixed(2),
      audioFormat: audioFormat === 1 ? 'PCM' : 'Compressed',
      channels: numChannels,
      sampleRate: sampleRate,
      bitRate: byteRate * 8,
      bitsPerSample: bitsPerSample,
      duration: durationSeconds.toFixed(2),
      dataSize: dataSize
    };
  }

  /**
   * Comprehensive analysis combining all features
   */
  async comprehensiveAnalysis(audioFile, referenceText = null) {
    console.log('\n=== COMPREHENSIVE SPEECH ANALYSIS ===\n');

    // Audio file analysis
    console.log('📊 AUDIO FILE CHARACTERISTICS:');
    const audioInfo = this.analyzeAudioFile(audioFile);
    console.log(`  File: ${audioFile}`);
    console.log(`  Size: ${audioInfo.fileSizeKB} KB`);
    console.log(`  Format: ${audioInfo.audioFormat}`);
    console.log(`  Channels: ${audioInfo.channels}`);
    console.log(`  Sample Rate: ${audioInfo.sampleRate} Hz`);
    console.log(`  Bit Rate: ${audioInfo.bitRate} bps`);
    console.log(`  Bits Per Sample: ${audioInfo.bitsPerSample}`);
    console.log(`  Duration: ${audioInfo.duration} seconds`);

    // Speech recognition and analysis
    console.log('\n🎤 SPEECH RECOGNITION:');
    const speechResults = await this.analyzeWithPronunciation(audioFile, referenceText);

    if (speechResults.errors.length > 0) {
      console.log('  ❌ Errors:');
      speechResults.errors.forEach(error => console.log(`    - ${error}`));
    }

    console.log(`  Transcription: "${speechResults.transcription}"`);

    if (speechResults.confidence !== null) {
      console.log(`  Confidence: ${(speechResults.confidence * 100).toFixed(2)}%`);
    }

    // Pronunciation assessment (if reference text provided)
    if (referenceText && speechResults.pronunciationAssessment) {
      console.log('\n📝 PRONUNCIATION ASSESSMENT:');
      console.log(`  Reference Text: "${referenceText}"`);
      const pa = speechResults.pronunciationAssessment;
      console.log(`  Overall Pronunciation Score: ${pa.pronunciationScore?.toFixed(2) || 'N/A'}`);
      console.log(`  Accuracy Score: ${pa.accuracyScore?.toFixed(2) || 'N/A'}`);
      console.log(`  Fluency Score: ${pa.fluencyScore?.toFixed(2) || 'N/A'}`);
      console.log(`  Completeness Score: ${pa.completenessScore?.toFixed(2) || 'N/A'}`);
      console.log(`  Prosody Score: ${pa.prosodyScore?.toFixed(2) || 'N/A'}`);
    }

    // Word-level analysis
    if (speechResults.words.length > 0) {
      console.log('\n📖 WORD-LEVEL ANALYSIS:');
      speechResults.words.forEach((word, idx) => {
        const offsetSec = word.offset ? (word.offset / 10000000).toFixed(2) : 'N/A';
        const durationMs = word.duration ? (word.duration / 10000).toFixed(0) : 'N/A';

        let output = `  ${idx + 1}. "${word.word}" - Offset: ${offsetSec}s, Duration: ${durationMs}ms`;

        if (word.accuracyScore !== undefined) {
          output += `, Accuracy: ${word.accuracyScore.toFixed(2)}`;
        }

        if (word.confidence !== undefined) {
          output += `, Confidence: ${(word.confidence * 100).toFixed(2)}%`;
        }

        if (word.errorType && word.errorType !== 'None') {
          output += ` ⚠️ Error: ${word.errorType}`;
        }

        console.log(output);
      });
    }

    // Phoneme-level analysis
    if (speechResults.phonemes.length > 0) {
      console.log('\n🔤 PHONEME-LEVEL ANALYSIS:');
      const phonemesByWord = {};
      speechResults.phonemes.forEach(p => {
        if (!phonemesByWord[p.word]) {
          phonemesByWord[p.word] = [];
        }
        phonemesByWord[p.word].push(p);
      });

      Object.entries(phonemesByWord).forEach(([word, phonemes]) => {
        console.log(`  "${word}":`);
        phonemes.forEach(p => {
          console.log(`    /${p.phoneme}/ - Accuracy: ${p.accuracyScore.toFixed(2)}`);
        });
      });
    }

    // Summary statistics
    console.log('\n📈 SUMMARY STATISTICS:');
    if (speechResults.words.length > 0) {
      const wordCount = speechResults.words.length;
      const avgWordDuration = speechResults.words
        .filter(w => w.duration)
        .reduce((sum, w) => sum + w.duration, 0) / wordCount / 10000;

      console.log(`  Total Words: ${wordCount}`);
      console.log(`  Average Word Duration: ${avgWordDuration.toFixed(0)}ms`);

      if (speechResults.words[0].accuracyScore !== undefined) {
        const avgAccuracy = speechResults.words
          .reduce((sum, w) => sum + (w.accuracyScore || 0), 0) / wordCount;
        console.log(`  Average Word Accuracy: ${avgAccuracy.toFixed(2)}`);

        const errorCount = speechResults.words.filter(w => w.errorType && w.errorType !== 'None').length;
        if (errorCount > 0) {
          console.log(`  Words with Errors: ${errorCount}`);
        }
      }
    }

    console.log('\n=== ANALYSIS COMPLETE ===\n');

    return {
      audioInfo,
      speechResults
    };
  }
}

export default SpeechAnalyzer;
