"""
Video Downscaling Script
Converts videos from orig_video/ to 720p and saves to videos/

Usage: python downscale_videos.py [kd|sq]
"""

import os
import subprocess
import sys
from pathlib import Path

# Parse profile argument (kd or sq)
PROFILE = "kd"  # default
if len(sys.argv) > 1 and sys.argv[1].lower() in ("kd", "sq"):
    PROFILE = sys.argv[1].lower()

INPUT_DIR = f"orig_video_{PROFILE}"
OUTPUT_DIR = f"videos_{PROFILE}"
TARGET_HEIGHT = 720

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".MOV", ".MP4")

def get_video_height(filepath):
    """Get video height using ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=height",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            # Take first line, first number
            line = result.stdout.strip().split('\n')[0]
            return int(line)
    except Exception as e:
        print(f"    ffprobe error: {e}")
    return None

def downscale_video(input_path, output_path, target_height=TARGET_HEIGHT):
    """Downscale video to target height, keep aspect ratio"""
    
    # Scale to target height, -2 ensures even width
    scale_filter = f"scale=-2:{target_height}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-vf", scale_filter,
        "-r", "30",  # 30fps for performance
        "-c:a", "aac", "-b:a", "128k",  # Keep audio
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def copy_video_optimized(input_path, output_path):
    """Re-encode without scaling (for videos already <= 480p)"""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "30",  # 30fps for performance
        "-c:a", "aac", "-b:a", "128k",  # Keep audio
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def main():
    print(f"Profile: {PROFILE} | Input: {INPUT_DIR} -> Output: {OUTPUT_DIR}")
    
    # Check ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
    except FileNotFoundError:
        print("ERROR: ffmpeg not found. Install with: winget install ffmpeg")
        sys.exit(1)
    
    # Check input dir exists
    if not os.path.exists(INPUT_DIR):
        print(f"ERROR: Input folder '{INPUT_DIR}' not found")
        sys.exit(1)
    
    # Create output dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get video files
    videos = [f for f in os.listdir(INPUT_DIR) if f.endswith(VIDEO_EXTENSIONS)]
    
    if not videos:
        print(f"No videos found in {INPUT_DIR}/")
        return
    
    print(f"Found {len(videos)} videos to process")
    print(f"Target: {TARGET_HEIGHT}p")
    print("=" * 50)
    
    skipped = 0
    for i, video in enumerate(videos, 1):
        input_path = os.path.join(INPUT_DIR, video)
        
        # Output as .mp4
        output_name = Path(video).stem + ".mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        
        # Get current height
        height = get_video_height(input_path)
        
        if height is None:
            print(f"[{i}/{len(videos)}] {video} - Could not read, skipping")
            continue
        
        if height <= TARGET_HEIGHT:
            print(f"[{i}/{len(videos)}] {video} ({height}p) - Already <= {TARGET_HEIGHT}p, optimizing...")
            success = copy_video_optimized(input_path, output_path)
        else:
            print(f"[{i}/{len(videos)}] {video} ({height}p) -> {TARGET_HEIGHT}p")
            success = downscale_video(input_path, output_path, TARGET_HEIGHT)
        
        if success:
            orig_size = os.path.getsize(input_path) / (1024*1024)
            new_size = os.path.getsize(output_path) / (1024*1024)
            print(f"    {orig_size:.1f} MB -> {new_size:.1f} MB")
        else:
            print(f"    ERROR processing {video}")
    
    print("=" * 50)
    print(f"Done! Videos saved to {OUTPUT_DIR}/")
    if skipped > 0:
        print(f"Skipped {skipped} already processed videos")

if __name__ == "__main__":
    main()
