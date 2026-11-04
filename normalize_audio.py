"""
Normalize audio levels across all videos in orig_video folder
Uses ffmpeg loudnorm filter to match loudness levels

Usage: python normalize_audio.py [kd|sq]
"""

import os
import subprocess
import json
import sys

# Parse profile argument (kd or sq)
PROFILE = "kd"  # default
if len(sys.argv) > 1 and sys.argv[1].lower() in ("kd", "sq"):
    PROFILE = sys.argv[1].lower()

ORIG_DIR = f"orig_video_{PROFILE}"
TEMP_SUFFIX = "_normalized"

def get_loudness(video_path):
    """Analyze video and get loudness stats using ffmpeg"""
    cmd = [
        "ffmpeg", "-i", video_path, "-af", "loudnorm=print_format=json", 
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse JSON from stderr (ffmpeg outputs to stderr)
    output = result.stderr
    
    # Find JSON block in output
    try:
        json_start = output.rfind('{')
        json_end = output.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = output[json_start:json_end]
            data = json.loads(json_str)
            return float(data.get("input_i", -24))
    except:
        pass
    
    return -24  # Default if parsing fails

def normalize_video(input_path, output_path, target_loudness=-16):
    """Normalize video audio to target loudness (default -16 LUFS)"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "copy",  # Don't re-encode video
        "-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def main():
    print(f"Profile: {PROFILE} | Folder: {ORIG_DIR}")
    
    # Check folder exists
    if not os.path.exists(ORIG_DIR):
        print(f"ERROR: Folder '{ORIG_DIR}' not found")
        return
    
    # Get all video files
    video_files = []
    for f in os.listdir(ORIG_DIR):
        if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            video_files.append(f)
    
    if not video_files:
        print(f"No videos found in {ORIG_DIR}/")
        return
    
    print(f"Found {len(video_files)} videos to normalize")
    print("=" * 50)
    
    # First pass: analyze all videos
    print("\nPass 1: Analyzing loudness levels...")
    loudness_data = {}
    for f in video_files:
        path = os.path.join(ORIG_DIR, f)
        loudness = get_loudness(path)
        loudness_data[f] = loudness
        print(f"  {f}: {loudness:.1f} LUFS")
    
    # Find the loudest video
    max_loudness = max(loudness_data.values())
    print(f"\nLoudest video: {max_loudness:.1f} LUFS")
    print(f"Target: -16 LUFS (broadcast standard)")
    
    # Second pass: normalize all videos
    print("\n" + "=" * 50)
    print("Pass 2: Normalizing audio...")
    
    for i, f in enumerate(video_files, 1):
        input_path = os.path.join(ORIG_DIR, f)
        # Create temp file, then replace original
        temp_path = os.path.join(ORIG_DIR, f.rsplit('.', 1)[0] + "_temp.mp4")
        
        print(f"\n[{i}/{len(video_files)}] {f}")
        print(f"  Current: {loudness_data[f]:.1f} LUFS -> Target: -16 LUFS")
        
        if normalize_video(input_path, temp_path):
            # Replace original with normalized version
            os.remove(input_path)
            os.rename(temp_path, input_path)
            print(f"  Done!")
        else:
            print(f"  Failed to normalize!")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    print("\n" + "=" * 50)
    print("Audio normalization complete!")
    print("\nNext steps:")
    print("  1. Run: python downscale_videos.py")
    print("  2. Run: Remove-Item audio_cache\\*.ogg")
    print("  3. Restart native_app.py")

if __name__ == "__main__":
    main()
