#!/usr/bin/env python3
import os
import sys
import hashlib
import json
import time
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()



app = Flask(__name__)
DB_FILE = "conversions.json"
CONVERSIONS_DIR = "conversions"

# Ensure conversions directory exists
os.makedirs(CONVERSIONS_DIR, exist_ok=True)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print(f"Error saving database: {e}")

def sync_existing_conversions():
    db = load_db()
    if not os.path.exists(CONVERSIONS_DIR):
        return
        
    for date_dir in os.listdir(CONVERSIONS_DIR):
        date_path = os.path.join(CONVERSIONS_DIR, date_dir)
        if not os.path.isdir(date_path):
            continue
            
        # Validate date format (YYYY-MM-DD)
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_dir):
            continue
            
        for file in os.listdir(date_path):
            if not file.endswith(".md"):
                continue
                
            file_path = os.path.join(date_path, file)
            filename_base = file[:-3]
            
            # Create a unique key for the db if it doesn't exist
            path_key = f"{date_dir}/{filename_base}"
            db_key = hashlib.sha256(path_key.encode('utf-8')).hexdigest()
            
            if db_key in db:
                continue
                
            # Parse the file to get title and stats
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Title parsing
                lines = content.strip().split('\n')
                title = "Detailed Summary"
                for line in lines:
                    if line.strip():
                        title = re.sub(r'^[#*\s]+', '', line).strip()
                        break
                        
                # Stats parsing
                stats = {
                    "conversion_time": 0.0,
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }
                
                time_match = re.search(r'\*\*Conversion Time\*\*:\s*([\d\.]+)', content)
                prompt_match = re.search(r'\*\*Prompt Tokens\*\*:\s*([\d,]+)', content)
                output_match = re.search(r'\*\*Output Tokens\*\*:\s*([\d,]+)', content)
                total_match = re.search(r'\*\*Total Tokens\*\*:\s*([\d,]+)', content)
                
                if time_match:
                    stats["conversion_time"] = float(time_match.group(1))
                if prompt_match:
                    stats["prompt_tokens"] = int(prompt_match.group(1).replace(",", ""))
                if output_match:
                    stats["output_tokens"] = int(output_match.group(1).replace(",", ""))
                if total_match:
                    stats["total_tokens"] = int(total_match.group(1).replace(",", ""))
                    
                # Add to DB
                db[db_key] = {
                    "hash": db_key,
                    "original_filename": f"{filename_base}.mp3",
                    "filename_base": filename_base,
                    "title": title,
                    "date": date_dir,
                    "timestamp": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "stats": stats
                }
                print(f"Synced existing conversion: {path_key}")
            except Exception as e:
                print(f"Failed to sync file {file_path}: {e}")
                
    save_db(db)


def calculate_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def clean_filename(title_text):
    import re
    title = re.sub(r'^[#*\s]+', '', title_text).strip()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[\s-]+', '_', title).lower()
    return title if title else "audio_summary"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/conversions", methods=["GET"])
def get_conversions():
    db = load_db()
    # Return list of conversions sorted by timestamp desc
    conversions_list = list(db.values())
    conversions_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(conversions_list)

@app.route("/api/conversions/<date>/<filename>", methods=["GET"])
def get_conversion_content(date, filename):
    # Safe path traversal prevention
    safe_date = os.path.basename(date)
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(CONVERSIONS_DIR, safe_date, safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/convert", methods=["POST"])
def convert_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
        
    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Ensure API Key is available
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"error": "Gemini API Key is missing. Please set GEMINI_API_KEY in your .env file."}), 500

    # Save uploaded file temporarily to compute hash and pass to Gemini API
    os.makedirs("tmp", exist_ok=True)
    temp_path = os.path.join("tmp", audio_file.filename)
    audio_file.save(temp_path)

    try:
        force_rerun = request.form.get("force_rerun", "false").lower() == "true"
        
        # Compute SHA-256 hash
        file_hash = calculate_sha256(temp_path)
        
        # Check history database
        db = load_db()
        existing = db.get(file_hash)

        if not force_rerun and existing:
            # Verify the file still exists on disk
            existing_path = os.path.join(CONVERSIONS_DIR, existing["date"], f"{existing['filename_base']}.md")
            if os.path.exists(existing_path):
                print(f"File found in history (hash matches). Reusing existing summary.")
                with open(existing_path, "r", encoding="utf-8") as f:
                    content = f.read()
                os.remove(temp_path)
                
                if 'reused' not in existing or not existing['reused']:
                    existing['reused'] = True
                    db[file_hash] = existing
                    save_db(db)

                return jsonify({
                    "title": existing["title"],
                    "date": existing["date"],
                    "filename_base": existing["filename_base"],
                    "content": content,
                    "stats": existing.get("stats", {}),
                    "reused": True
                })

        # Not in history or force_rerun=True: Process with Gemini
        print(f"Processing with Gemini... (force_rerun={force_rerun})")
        client = genai.Client(api_key=api_key)
        
        gemini_file = None
        # Try to reuse existing Gemini file if available
        if existing and 'gemini_file_name' in existing:
            try:
                print(f"Attempting to reuse existing Gemini file: {existing['gemini_file_name']}")
                gemini_file = client.files.get(name=existing['gemini_file_name'])
                print("Successfully retrieved existing Gemini file.")
            except Exception as e:
                print(f"Failed to retrieve existing Gemini file ({e}). Re-uploading is necessary.")

        # If not retrieved, upload it
        if not gemini_file:
            print("Uploading new file to Gemini Files API.")
            gemini_file = client.files.upload(file=temp_path)
            print(f"Uploaded to Gemini Files API. URI: {gemini_file.uri}, Name: {gemini_file.name}")

        prompt = (
            "Please listen to the attached audio file. Write a comprehensive, well-structured summary of the audio in Markdown format, including timestamps for key events or topics discussed.\n"
            "Ensure the very first line of your response is a top-level markdown heading containing a suitable title for this summary, for example:\n"
            "# Detailed Summary of the Discussion\n"
            "Do not put any other text before the title."
        )

        model_name = request.form.get("model", "gemini-3.5-flash")
        
        start_time = time.time()
        response = client.models.generate_content(
            model=model_name,
            contents=[gemini_file, prompt]
        )
        generation_time = time.time() - start_time

        # NOTE: We are NOT deleting the Gemini file, to allow for re-use.
        # Consider a cleanup policy for old files if storage is a concern.

        summary_text = response.text
        if not summary_text:
            return jsonify({"error": "Gemini returned empty response"}), 500

        # Extract token usage
        prompt_tokens = 0
        output_tokens = 0
        total_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0
            total_tokens = response.usage_metadata.total_token_count or 0

        # Append statistics to markdown summary
        stats_markdown = (
            f"\n\n---\n"
            f"### Generation Statistics\n"
            f"- **Conversion Time**: {generation_time:.2f} seconds\n"
            f"- **Prompt Tokens**: {prompt_tokens:,}\n"
            f"- **Output Tokens**: {output_tokens:,}\n"
            f"- **Total Tokens**: {total_tokens:,}\n"
        )
        summary_text += stats_markdown

        # Parse title
        user_title = request.form.get("title", "").strip()

        if user_title:
            clean_title_text = user_title
        else:
            lines = summary_text.strip().split('\n')
            title_line = "Detailed Summary"
            for line in lines:
                if line.strip():
                    title_line = line.strip()
                    break
            clean_title_text = re.sub(r'^[#*\s]+', '', title_line).strip()

        # Remove markdown heading symbols from title
        filename_base = clean_filename(clean_title_text)

        day_str = datetime.now().strftime("%Y-%m-%d")
        day_dir = os.path.join(CONVERSIONS_DIR, day_str)
        os.makedirs(day_dir, exist_ok=True)

        output_filename = f"{filename_base}.md"
        output_path = os.path.join(day_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)

        # Update database
        stats = {
            "conversion_time": round(generation_time, 2),
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }

        db[file_hash] = {
            "hash": file_hash,
            "original_filename": audio_file.filename,
            "filename_base": filename_base,
            "title": clean_title_text,
            "date": day_str,
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "reused": False,
            "gemini_file_name": gemini_file.name
        }
        save_db(db)

        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({
            "reused": False,
            "title": clean_title_text,
            "date": day_str,
            "filename_base": filename_base,
            "content": summary_text,
            "stats": stats
        })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error during conversion: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Syncing existing conversions...")
    sync_existing_conversions()
    app.run(host="127.0.0.1", port=5000, debug=True)

