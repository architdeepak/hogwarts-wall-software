"""
Video Optimization Script for Photo Wall
Transcodes videos to web-optimized format for smooth multi-video playback.

Requirements: ffmpeg must be installed and in PATH
Install: winget install ffmpeg  OR  choco install ffmpeg
"""

import os
import subprocess
import sys
from pathlib import Path

VIDEOS_DIR = "videos"
OUTPUT_DIR = "videos_optimized"

# Target resolution - adjust based on your frame sizes
# For 8K display with small frames, 720p is often enough
TARGET_HEIGHT = 720

# Quality (lower = better quality, larger file. 23-28 is good for web)
CRF = 24

# Preset (faster = worse compression, ultrafast/superfast/veryfast/faster/fast/medium)
PRESET = "fast"

def get_video_info(filepath):
    """Get video resolution using ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            w, h = result.stdout.strip().split(',')
            return int(w), int(h)
    except:
        pass
    return None, None

def optimize_video(input_path, output_path, target_height=TARGET_HEIGHT):
    """Transcode video to optimized H.264 format"""
    
    # Scale to target height, keep aspect ratio, ensure even dimensions
    scale_filter = f"scale=-2:{target_height}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", PRESET,
        "-crf", str(CRF),
        "-vf", scale_filter,
        "-an",  # Remove audio (we're muting anyway)
        "-movflags", "+faststart",  # Enable streaming
        "-pix_fmt", "yuv420p",  # Maximum compatibility
        output_path
    ]
    
    print(f"  Transcoding: {os.path.basename(input_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        return False
    return True

def main():
    # Check ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
    except FileNotFoundError:
        print("ERROR: ffmpeg not found. Install it first:")
        print("  winget install ffmpeg")
        print("  OR")
        print("  choco install ffmpeg")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get list of videos
    video_extensions = (".mp4", ".webm", ".mov", ".avi", ".mkv")
    videos = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(video_extensions)]
    
    if not videos:
        print(f"No videos found in {VIDEOS_DIR}/")
        return
    
    print(f"Found {len(videos)} videos to optimize")
    print(f"Target: {TARGET_HEIGHT}p, CRF={CRF}, Preset={PRESET}")
    print("=" * 50)
    
    for i, video in enumerate(videos, 1):
        input_path = os.path.join(VIDEOS_DIR, video)
        output_name = Path(video).stem + "_opt.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        
        # Get original resolution
        w, h = get_video_info(input_path)
        if h and h <= TARGET_HEIGHT:
            print(f"[{i}/{len(videos)}] {video} - Already {h}p, copying...")
            # Just optimize without scaling
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
                "-an", "-movflags", "+faststart", "-pix_fmt", "yuv420p",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)
        else:
            print(f"[{i}/{len(videos)}] {video} ({w}x{h}) -> {TARGET_HEIGHT}p")
            optimize_video(input_path, output_path, TARGET_HEIGHT)
        
        # Show size reduction
        orig_size = os.path.getsize(input_path) / (1024*1024)
        new_size = os.path.getsize(output_path) / (1024*1024)
        print(f"    {orig_size:.1f} MB -> {new_size:.1f} MB ({100*new_size/orig_size:.0f}%)")
    
    print("=" * 50)
    print(f"Done! Optimized videos saved to {OUTPUT_DIR}/")
    print("\nTo use them, either:")
    print("  1. Replace videos in 'videos/' with the optimized ones")
    print("  2. Or update config.json to point to the new filenames")

if __name__ == "__main__":
    main()
