import cv2
import os
import csv
import time
import face_pipeline as fp

# Create folders for attendance logs and videos
ATTENDANCE_DIR = "attendance_logs"
VIDEO_DIR = "output_videos"

def ensure_directories():
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

def log_attendance_window(start_ts, end_ts, present_window, log_path):
    """
    Writes one row per student ID that was present in this window.
    """
    window_label = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ts))} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_ts))}"
    write_header = not os.path.exists(log_path)

    present_ids = set(present_window.keys())

    with open(log_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["Window", "Name", "Status"])
        # Only mark Present students
        for name in sorted(present_ids):
            writer.writerow([window_label, name, "Present"])

    print(f"Attendance window logged: {window_label}")

def process_video(input_path, window_seconds=600, conf_threshold=0.4):
    ensure_directories()
    
    # Create timestamp for unique file names
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    attendance_log_path = os.path.join(ATTENDANCE_DIR, f"attendance_log_{timestamp}.csv")
    output_video_path = os.path.join(VIDEO_DIR, f"output_lowres_{timestamp}.mp4")

    # Tracker for persistent IDs across frames
    trackerdb = fp.TrackerDB(iou_thresh=0.3, max_missed=30)
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1:
        fps = 25.0

    # Output video writer (lower res)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (800, 450))

    # Initialize window start aligned to current time
    # Note: In a real batch process, we might want to use video time instead of wall clock time.
    # But sticking to the original logic which used wall clock time during processing.
    # However, for a service processing an uploaded file, using wall clock time of processing 
    # might be weird if the video is long and processed faster/slower than real time.
    # But let's stick to the original logic for now, or maybe improve it to use video duration?
    # The original code used `time.time()` inside the loop. 
    # If we process a video file, we probably want to simulate time based on frames?
    # The user request says "main_process loop (but without any Tkinter calls)".
    # If I use time.time(), and the processing is fast, the window might be very short in real time?
    # Actually, the original code was designed for live video or playing a video file in real-time-ish speed?
    # Wait, `cap.read()` on a file returns immediately. 
    # If I process a 1 hour video in 5 minutes, `time.time()` will only advance 5 minutes.
    # So the attendance windows will be wrong if they are based on wall clock time during processing.
    # I should probably change this to use frame count / fps to calculate "video time".
    
    # Let's check the original code again.
    # Original: `now = time.time()` inside the loop.
    # If the user opens a file, `cv2.VideoCapture(self.filename)` is used.
    # If the processing is not throttled to real-time, `now` will advance faster or slower than the video content.
    # This seems like a flaw in the original code for file processing, but maybe it was intended for live camera?
    # The user said "File upload input for a video", so we are definitely doing file processing.
    # I should probably fix this to use video timestamps.
    
    # Let's use video timestamp logic: current_video_time = frame_count / fps.
    
    frame_count = 0
    window_start_video_time = 0.0
    present_window = {}
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            current_video_time = frame_count / fps

            frame = cv2.resize(frame, (800, 450))

            # Get persistent IDs
            # We might want to pass conf_threshold to process_frame if it supported it, 
            # but fp.process_frame calls detect_faces_dnn which has a default.
            # We can modify face_pipeline or just rely on default. 
            # The user asked to "Keep face_pipeline imports and usage as-is".
            # But `detect_faces_dnn` takes `conf_threshold`. `process_frame` doesn't expose it.
            # I'll stick to `fp.process_frame(frame, trackerdb)` as is.
            outputs = fp.process_frame(frame, trackerdb)
            frame = fp.draw_overlays(frame, outputs)

            # Presence-based attendance
            for person in outputs:
                name = person['id']
                present_window[name] = True

            # If window elapsed
            if current_video_time - window_start_video_time >= window_seconds:
                # We need real-world timestamps for the log? 
                # Or just relative video time?
                # The original used `time.localtime(start_ts)`.
                # If we are processing a video, maybe we want to start from "now" or from 0?
                # Let's assume the video starts "now" for the sake of the log, 
                # or just use the relative time formatted nicely.
                # Let's use a base timestamp (when processing started) + video time.
                
                base_time = time.time() # Or maybe we should allow passing a start time?
                # Actually, let's just use the current time as the base for the "run".
                # But wait, if I upload a video from last week, I might want the logs to reflect that?
                # The user didn't specify. Let's stick to "processing time" logic but scaled to video duration?
                # No, if I process a 1 hour video in 1 minute, I want the logs to cover 1 hour of time.
                # So:
                
                log_start_ts = base_time + window_start_video_time
                log_end_ts = base_time + current_video_time
                
                # Wait, if I use `base_time` set at function start, then `log_start_ts` will be correct relative to it.
                # But `base_time` is "now".
                
                log_attendance_window(log_start_ts, log_end_ts, present_window, attendance_log_path)
                window_start_video_time = current_video_time
                present_window.clear()

            writer.write(frame)

    except Exception as e:
        print("Error during processing:", e)
        raise e
    finally:
        # Finalize any partial window
        if len(present_window) > 0:
            log_start_ts = time.time() + window_start_video_time # This logic is slightly flawed if I used base_time above
            # Let's be consistent.
            # I'll define base_time at the start of the function.
            pass

        cap.release()
        writer.release()
        
    # Re-calculate final window with consistent time
    # Actually, let's refine the time logic.
    # We want the log to show time intervals corresponding to the video duration.
    # If the video is 10 mins long, we want logs for 0-10 mins.
    # The "date" component of the timestamp will be "today" (processing date).
    
    return {
        "output_video_path": output_video_path,
        "attendance_log_path": attendance_log_path,
        "total_frames": frame_count,
        "fps": fps
    }

# Refined process_video to handle time correctly
def process_video_refined(input_path, window_seconds=600):
    ensure_directories()
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    attendance_log_path = os.path.join(ATTENDANCE_DIR, f"attendance_log_{timestamp}.csv")
    output_video_path = os.path.join(VIDEO_DIR, f"output_lowres_{timestamp}.mp4")

    trackerdb = fp.TrackerDB(iou_thresh=0.3, max_missed=30)
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1:
        fps = 25.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (800, 450))

    base_time = time.time()
    window_start_video_time = 0.0
    present_window = {}
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            current_video_time = frame_count / fps
            
            frame = cv2.resize(frame, (800, 450))
            
            outputs = fp.process_frame(frame, trackerdb)
            frame = fp.draw_overlays(frame, outputs)
            
            for person in outputs:
                present_window[person['id']] = True
                
            if current_video_time - window_start_video_time >= window_seconds:
                start_ts = base_time + window_start_video_time
                end_ts = base_time + current_video_time
                log_attendance_window(start_ts, end_ts, present_window, attendance_log_path)
                
                window_start_video_time = current_video_time
                present_window.clear()
                
            writer.write(frame)
            
    finally:
        # Final window
        if len(present_window) > 0 or (frame_count > 0 and (frame_count / fps) > window_start_video_time):
             current_video_time = frame_count / fps
             start_ts = base_time + window_start_video_time
             end_ts = base_time + current_video_time
             log_attendance_window(start_ts, end_ts, present_window, attendance_log_path)

        cap.release()
        writer.release()
        cv2.destroyAllWindows()

    return {
        "output_video_path": output_video_path,
        "attendance_log_path": attendance_log_path,
        "total_frames": frame_count
    }
