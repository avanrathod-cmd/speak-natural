import sys
from pathlib import Path

# Add parent directory to path if transcribe is located there
sys.path.insert(0, str(Path(__file__).parent.parent / "speach-to-text"))

from transcribe import read_transcription
from enhance_transcript import convert_to_script, enhance_with_chatgpt


def main():
    job_name = "my_job"
    file_uri = "s3://speach-analyzer/Conv with Avisha.webm"

    transcription_data = read_transcription(job_name, file_uri)
    conv_script = convert_to_script(transcription_data['results']['audio_segments'])    
    enhanced_transcript = enhance_with_chatgpt(conv_script)
    print (f"""\n\noriginal script = {conv_script} \n\n""")
    print(f"""\n\nenhanced transcript = {enhanced_transcript}\n\n""")
    segments = parse_enhanced_script_to_segments(enhanced_transcript)
    print(f"""\n\nparsed segments = {segments}\n\n""")


if __name__ == "__main__":
    main()
    