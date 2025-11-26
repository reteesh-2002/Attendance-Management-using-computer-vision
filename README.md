# GPU Face Attendance System - Flask Web Application

## Overview

This project has been refactored from a Tkinter desktop application to a modern Flask web application. It processes video files to detect faces, track individuals across frames, and generate attendance logs based on configurable time windows.

## Project Structure

```
project_root/
├── app.py                          # Flask application entry point
├── attendance_service.py           # Core video processing logic (UI-agnostic)
├── face_pipeline.py                # Face detection and tracking module
├── requirements.txt                # Python dependencies
├── res10_300x300_ssd_iter_140000.caffemodel  # Face detection model
├── deploy.prototxt                 # Model configuration
├── templates/                      # HTML templates
│   ├── layout.html                 # Base template
│   ├── index.html                  # Upload form
│   ├── result.html                 # Processing results
│   ├── attendance_list.html        # List of attendance logs by date
│   └── attendance_detail.html      # Detailed attendance view
├── static/
│   └── style.css                   # Styling
├── uploads/                        # Temporary uploaded videos
├── attendance_logs/                # Generated CSV attendance logs
└── output_videos/                  # Processed output videos
```

## Features

### Core Functionality
- **Video Upload**: Upload video files through a web interface
- **Face Detection**: Uses OpenCV DNN-based face detector (SSD)
- **Face Tracking**: Persistent ID tracking across frames using IoU-based tracking
- **Attendance Logging**: Presence-based attendance with configurable time windows
- **Output Video**: Generates annotated video with bounding boxes and IDs
- **Web-based Viewing**: Browse attendance logs by date

### Configurable Parameters
- **Window Duration**: Customize attendance window length (default: 600 seconds / 10 minutes)
- **Confidence Threshold**: Face detection confidence (in face_pipeline.py)
- **IoU Threshold**: Tracking overlap threshold (default: 0.3)
- **Max Missed Frames**: Maximum frames before dropping a track (default: 30)

## Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd /home/redark/Documents/Project
   ```

2. **Create and activate virtual environment** (if not already done)
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure model files are present**
   - `res10_300x300_ssd_iter_140000.caffemodel`
   - `deploy.prototxt`
   
   These should already be in the project directory.

## Usage

### Running the Flask Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### Web Interface

1. **Home Page** (`/`)
   - Upload a video file
   - Set attendance window duration (optional)
   - Click "Start Processing"

2. **Results Page** (`/process`)
   - View processing statistics
   - Download processed video
   - Download attendance CSV log
   - Link to view attendance logs

3. **Attendance Logs** (`/attendance/`)
   - Browse all attendance logs by date
   - Click on a date to view detailed records

4. **Attendance Detail** (`/attendance/<date>`)
   - View all attendance records for a specific date
   - Shows: Window, Student Name, Status

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Upload form |
| `/process` | POST | Process uploaded video |
| `/download_video/<filename>` | GET | Download processed video |
| `/download_log/<filename>` | GET | Download attendance CSV |
| `/attendance/` | GET | List all attendance dates |
| `/attendance/<date>` | GET | View attendance for specific date |

## Architecture

### Separation of Concerns

1. **`attendance_service.py`**: Pure Python module
   - No UI dependencies
   - Function-based API: `process_video_refined(input_path, window_seconds)`
   - Returns: output paths and statistics
   - Can be tested independently or used in other contexts

2. **`face_pipeline.py`**: Computer vision module
   - Face detection using OpenCV DNN
   - IoU-based tracking
   - Drawing utilities
   - Device detection (CUDA/CPU)

3. **`app.py`**: Flask web application
   - Route handlers
   - File upload management
   - Template rendering
   - Integrates attendance_service

### Data Flow

```
User uploads video → Flask saves to /uploads
                  ↓
Flask calls attendance_service.process_video_refined()
                  ↓
Service processes video frame-by-frame:
  - Detect faces (face_pipeline)
  - Track IDs across frames
  - Log attendance per window
  - Write annotated output video
                  ↓
Service returns paths and stats
                  ↓
Flask renders result page with download links
```

## Attendance Logic

- **Time Windows**: Video is divided into configurable time windows (default: 10 minutes)
- **Presence-Based**: If a person is detected at least once in a window, they are marked "Present"
- **Persistent IDs**: Each tracked face gets a unique ID (e.g., `Student_1`, `Student_2`)
- **CSV Format**: `Window | Name | Status`

### Example CSV Output

```csv
Window,Name,Status
2025-11-26 16:00:00 - 2025-11-26 16:10:00,Student_1,Present
2025-11-26 16:00:00 - 2025-11-26 16:10:00,Student_3,Present
2025-11-26 16:10:00 - 2025-11-26 16:20:00,Student_1,Present
```

## Legacy Files

- **`Project-GUI-upgraded.py`**: Original Tkinter application (can be retired)
- **`view_attendance.py`**: Standalone Flask viewer (functionality integrated into app.py)

## Future Enhancements

### Suggested Improvements

1. **Identity Mapping**
   - Upload CSV mapping `Student_N` → Real Name
   - Display real names in logs and UI

2. **Advanced Filtering**
   - Filter by date range
   - Filter by student name
   - Export filtered results

3. **REST API**
   - JSON endpoints for programmatic access
   - Example: `/api/attendance?date=2025-11-26`

4. **Live Streaming**
   - Stream processed frames to browser during processing
   - Use multipart/x-mixed-replace or WebSockets

5. **Device Summary Page**
   - Show CUDA availability
   - Display torch version
   - System diagnostics

6. **Improved Time Handling**
   - Allow specifying video start time
   - Better handling of video vs. wall-clock time

7. **Authentication**
   - User login system
   - Role-based access control

## Troubleshooting

### Model Files Not Found
If you get an error about missing model files:
```bash
# Copy from Downloads or another location
cp /path/to/res10_300x300_ssd_iter_140000.caffemodel .
cp /path/to/deploy.prototxt .
```

### CUDA Not Available
The system will automatically fall back to CPU if CUDA is not available. Check with:
```python
import torch
print(torch.cuda.is_available())
```

### Video Processing Slow
- Ensure you're using GPU if available
- Reduce video resolution (currently hardcoded to 800x450)
- Increase detection confidence threshold to reduce false positives

## Development

### Testing the Service Layer
```python
from attendance_service import process_video_refined

result = process_video_refined("path/to/video.mp4", window_seconds=300)
print(result)
# {'output_video_path': '...', 'attendance_log_path': '...', 'total_frames': 1500}
```

### Running in Debug Mode
Flask debug mode is enabled by default in `app.py`:
```python
app.run(debug=True, port=5000)
```

## License

[Specify your license here]

## Contributors

[Add contributors here]
