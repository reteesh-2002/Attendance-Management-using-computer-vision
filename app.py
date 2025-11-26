from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import attendance_service
import glob
import csv
from collections import defaultdict

app = Flask(__name__)

# Configure upload folder (temp)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure output directories exist (handled by service, but good to know)
ATTENDANCE_DIR = "attendance_logs"
VIDEO_DIR = "output_videos"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'video' not in request.files:
        return redirect(request.url)
    file = request.files['video']
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Get optional parameters
        try:
            window_seconds = int(request.form.get('window_seconds', 600))
        except ValueError:
            window_seconds = 600

        # Process video
        result = attendance_service.process_video_refined(filepath, window_seconds=window_seconds)
        
        # Result contains absolute paths or relative? 
        # The service uses "attendance_logs/..." which is relative to CWD.
        # We need to pass filenames to the template so we can link to them.
        
        video_filename = os.path.basename(result['output_video_path'])
        log_filename = os.path.basename(result['attendance_log_path'])
        
        return render_template('result.html', 
                               video_file=video_filename, 
                               log_file=log_filename,
                               stats=result)

@app.route('/download_video/<filename>')
def download_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

@app.route('/download_log/<filename>')
def download_log(filename):
    return send_from_directory(ATTENDANCE_DIR, filename)

# --- Attendance View Logic (Ported) ---

def parse_attendance_files():
    attendance_data = defaultdict(list)
    # Use absolute path or relative to CWD
    for file in glob.glob(os.path.join(ATTENDANCE_DIR, "attendance_log_*.csv")):
        basename = os.path.basename(file)
        try:
            # Expected format: attendance_log_YYYYMMDD_HHMMSS.csv
            parts = basename.split("_")
            if len(parts) >= 3:
                date_part = parts[2] # YYYYMMDD
                date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            else:
                continue
        except Exception:
            continue

        with open(file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                attendance_data[date_str].append(row)
    return attendance_data

@app.route('/attendance/')
def attendance_list():
    data = parse_attendance_files()
    dates = sorted(data.keys(), reverse=True)
    return render_template('attendance_list.html', dates=dates)

@app.route('/attendance/<date>')
def attendance_detail(date):
    data = parse_attendance_files()
    records = data.get(date, [])
    return render_template('attendance_detail.html', date=date, records=records)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
