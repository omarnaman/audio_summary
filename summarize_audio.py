#!/usr/bin/env python3
import os
import sys
import re
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai

def clean_filename(title_text):
    # Remove leading markdown header syntax like '#', '*', or whitespace
    title = re.sub(r'^[#*\s]+', '', title_text).strip()
    # Remove special characters, keeping letters, numbers, spaces, and hyphens/underscores
    title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces and hyphens with underscores, convert to lowercase
    title = re.sub(r'[\s-]+', '_', title).lower()
    return title if title else "audio_summary"

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and summarize an audio file using Gemini."
    )
    parser.add_argument(
        "audio_path",
        help="Path to the audio file to summarize (e.g., sample1.mp3)"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API Key. If not provided, GEMINI_API_KEY or GOOGLE_API_KEY environment variable will be used."
    )
    parser.add_argument(
        "--model", "-m",
        default="gemini-3.5-flash",
        help="Gemini model to use (default: gemini-3.5-flash)"
    )

    args = parser.parse_args()

    audio_path = args.audio_path
    if not os.path.exists(audio_path):
        print(f"Error: File not found at '{audio_path}'")
        sys.exit(1)

    load_dotenv()


    # Determine API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Gemini API Key is missing.")
        print("Please provide it using the --api-key flag, set the GEMINI_API_KEY/GOOGLE_API_KEY environment variable,")
        print("or define it in a '.env' file in the current directory.")
        print("\nExample in .env:")
        print("  GEMINI_API_KEY=your_api_key_here")
        print("\nExample usage:")
        print(f"  python summarize_audio.py {audio_path}")
        sys.exit(1)

    print("Initializing Gemini Client...")
    client = genai.Client(api_key=api_key)

    print(f"Uploading '{audio_path}' to Gemini Files API...")
    try:
        audio_file = client.files.upload(file=audio_path)
        print(f"Uploaded successfully. File URI: {audio_file.uri}")
    except Exception as e:
        print(f"Error uploading file: {e}")
        sys.exit(1)

    prompt = (
        "Please listen to the attached audio file. Write a comprehensive, well-structured summary of the audio in Markdown format.\n"
        "Ensure the very first line of your response is a top-level markdown heading containing a suitable title for this summary, for example:\n"
        "# Detailed Summary of the Discussion\n"
        "Do not put any other text before the title."
    )

    print(f"Generating summary using {args.model}...")
    start_time = time.time()
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[audio_file, prompt]
        )
    except Exception as e:
        print(f"Error generating content: {e}")
        # Clean up uploaded file
        try:
            client.files.delete(name=audio_file.name)
        except Exception:
            pass
        sys.exit(1)
    generation_time = time.time() - start_time

    # Clean up uploaded file from the API after processing
    print("Cleaning up file from Gemini Files API...")
    try:
        client.files.delete(name=audio_file.name)
    except Exception as e:
        print(f"Warning: Could not delete temporary file from Gemini: {e}")

    summary_text = response.text
    if not summary_text:
        print("Error: Gemini returned an empty response.")
        sys.exit(1)

    # Extract token usage statistics
    prompt_tokens = 0
    output_tokens = 0
    total_tokens = 0
    if response.usage_metadata:
        prompt_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0
        total_tokens = response.usage_metadata.total_token_count or 0

    # Append statistics to the markdown summary content
    stats_markdown = (
        f"\n\n---\n"
        f"### Generation Statistics\n"
        f"- **Conversion Time**: {generation_time:.2f} seconds\n"
        f"- **Prompt Tokens**: {prompt_tokens:,}\n"
        f"- **Output Tokens**: {output_tokens:,}\n"
        f"- **Total Tokens**: {total_tokens:,}\n"
    )
    summary_text += stats_markdown

    # Parse title from the first line
    lines = summary_text.strip().split('\n')
    title_line = ""
    for line in lines:
        if line.strip():
            title_line = line.strip()
            break

    filename_base = clean_filename(title_line)

    # Organize outputs into conversions/<YYYY-MM-DD>/ directory
    main_dir = "conversions"
    day_dir = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(main_dir, day_dir)
    os.makedirs(output_dir, exist_ok=True)

    output_filename = os.path.join(output_dir, f"{filename_base}.md")

    # Write summary to file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print(f"\nSummary successfully saved to: {output_filename}")
        print("--- Title of Summary ---")
        print(title_line)
        print("------------------------")
        print(f"Conversion Time: {generation_time:.2f} seconds")
        print(f"Prompt Tokens  : {prompt_tokens:,}")
        print(f"Output Tokens  : {output_tokens:,}")
        print(f"Total Tokens   : {total_tokens:,}")
        print("------------------------")
    except Exception as e:
        print(f"Error writing summary to file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
