import whisper
import os
import sys

def run_diagnostic(file_path):
    """
    A simple, focused test to see if Whisper and ffmpeg are working correctly.
    """
    print("--- STARTING WHISPER DIAGNOSTIC ---")

    # 1. Check if the audio file exists
    print(f"Checking for audio file at: {file_path}")
    if not os.path.exists(file_path):
        print("\n--- DIAGNOSTIC FAILED ---")
        print(f"Error: The audio file '{file_path}' was not found in the backend directory.")
        print("Please copy your test audio file into the 'backend' folder and try again.")
        print("---------------------------------")
        return
    print("Audio file found.")

    try:
        # 2. Load the Whisper model
        print("\nStep 1: Loading Whisper model (base)...")
        model = whisper.load_model("base")
        print("Step 1: Model loaded successfully.")

        # 3. Attempt to transcribe the file
        print(f"\nStep 2: Attempting to transcribe '{file_path}'...")
        result = model.transcribe(file_path, fp16=False)
        print("Step 2: Transcription call completed.")

        # 4. Check the result
        transcript_text = result.get("text", "").strip()

        if transcript_text:
            print("\n--- DIAGNOSTIC SUCCEEDED! ---")
            print("Whisper and ffmpeg are working correctly.")
            print("\nFull Transcript:")
            print(transcript_text)
            print("-----------------------------")
        else:
            print("\n--- DIAGNOSTIC FAILED ---")
            print("Whisper ran but produced an EMPTY transcript.")
            print("This can happen with silent audio files or corrupted media.")
            print("Please try a different audio file (e.g., a short MP3 you download from the internet).")
            print("-----------------------------")

    except Exception as e:
        print("\n--- DIAGNOSTIC FAILED ---")
        print("A critical error occurred during the process.")
        print("\nTHE ROOT CAUSE OF ALL YOUR PROBLEMS IS:")
        print("==========================================")
        print(str(e))
        print("==========================================")
        print("\nIf the error above mentions 'ffmpeg', it means Python cannot find it.")
        print("Even if it's installed, it might not be in the system's PATH.")
        print("If it mentions a file format or codec, the audio file may be incompatible.")
        print("---------------------------------")

if __name__ == "__main__":
    # Check if a filename was provided, otherwise use a default.
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        #
        # ACTION: CHANGE 'test.mp3' TO THE NAME OF YOUR AUDIO FILE
        #
        audio_file = "test.mp3" 
    
    run_diagnostic(audio_file)