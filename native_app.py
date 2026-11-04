"""
Native Photo Wall Video App
Uses Pygame + OpenCV for hardware-accelerated video playback
Decodes videos in parallel threads for smooth playback

Controls:
  A-Q: Unmute audio for that frame (A=1, B=2, etc.)
  0: Mute all audio
  1: Toggle debug overlay
  3: Toggle fullscreen
  ESC: Exit

Requirements:
  pip install pygame opencv-python pygame-ce
"""

import sys
import os
import json
import threading
import time
import subprocess
import tempfile
import cv2
import pygame
from pygame import mixer

# Parse profile argument (kd or sq)
PROFILE = "sq"  # default
if len(sys.argv) > 1 and sys.argv[1].lower() in ("kd", "sq"):
    PROFILE = sys.argv[1].lower()

# Profile-specific paths
CONFIG_FILE = f"config_{PROFILE}.json"
NATIVE_CONFIG_FILE = f"native_config_{PROFILE}.json"
VIDEOS_DIR = f"videos_{PROFILE}"
AUDIO_CACHE_DIR = f"audio_cache_{PROFILE}"


def extract_audio(video_path):
    """Extract audio from video file using ffmpeg, cache it as OGG (supports seeking)"""
    if not video_path or not os.path.exists(video_path):
        return None
    
    # Create cache dir
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    
    # Generate cache filename - use OGG for better seeking support
    video_name = os.path.basename(video_path)
    audio_path = os.path.join(AUDIO_CACHE_DIR, video_name.rsplit('.', 1)[0] + '.ogg')
    
    # Skip if already cached
    if os.path.exists(audio_path):
        return audio_path
    
    # Extract audio with ffmpeg as OGG (vorbis)
    try:
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'libvorbis', '-ar', '44100', '-ac', '2', '-q:a', '5',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(audio_path):
            return audio_path
    except Exception as e:
        print(f"  Audio extraction failed for {video_path}: {e}")
    
    return None


class VideoPlayer:
    """Threaded video player using OpenCV"""
    
    def __init__(self, video_path, target_fps=30):
        self.video_path = video_path
        self.target_fps = target_fps
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.cap = None
        self.width = 0
        self.height = 0
        self.fps = 30
        self.total_frames = 0
        self.current_frame_num = 0
        
        if video_path and os.path.exists(video_path):
            self.cap = cv2.VideoCapture(video_path, cv2.CAP_ANY)
            # Try to enable hardware acceleration
            self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def get_position_seconds(self):
        """Get current playback position in seconds"""
        if self.fps > 0:
            return self.current_frame_num / self.fps
        return 0
    
    def get_duration_seconds(self):
        """Get total video duration in seconds"""
        if self.fps > 0 and self.total_frames > 0:
            return self.total_frames / self.fps
        return 0
    
    def start(self):
        """Start video playback thread"""
        if self.cap is None:
            return
        self.running = True
        self.thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.thread.start()
    
    def _playback_loop(self):
        """Main playback loop running in thread"""
        frame_time = 1.0 / self.fps
        
        while self.running:
            start = time.perf_counter()
            
            ret, frame = self.cap.read()
            if not ret:
                # Loop video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame_num = 0
                ret, frame = self.cap.read()
                if not ret:
                    continue
            
            # Track current frame
            self.current_frame_num = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            with self.lock:
                self.frame = frame
            
            # Maintain frame rate
            elapsed = time.perf_counter() - start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def get_frame(self):
        """Get current frame (thread-safe)"""
        with self.lock:
            return self.frame
    
    def stop(self):
        """Stop playback"""
        self.running = False
        if self.cap:
            self.cap.release()


class VideoFrame:
    """A video frame with position and display properties"""
    
    def __init__(self, frame_id, video_path, x, y, width, height,
                 video_offset_x=0, video_offset_y=0, video_zoom=100, scale=1.0, volume=100):
        self.frame_id = frame_id
        self.key_letter = chr(65 + frame_id)
        self.x = x
        self.y = y
        self.width = max(1, width)
        self.height = max(1, height)
        # Store original config values (before scaling)
        self.video_offset_x = video_offset_x
        self.video_offset_y = video_offset_y
        self.video_zoom = video_zoom
        self.volume = volume  # Volume 0-200 (100 = normal)
        self.scale = scale
        self.muted = True
        self.audio_active = False
        self.video_path = video_path
        
        # Create video player
        self.player = VideoPlayer(video_path)
        self.surface = None
        
        # Audio - extract and load
        self.audio_path = None
        self.audio_sound = None
        if video_path and os.path.exists(video_path):
            self.audio_path = extract_audio(video_path)
            if self.audio_path and os.path.exists(self.audio_path):
                try:
                    self.audio_sound = pygame.mixer.Sound(self.audio_path)
                except Exception as e:
                    print(f"  Could not load audio for frame {frame_id}: {e}")
    
    def start(self):
        """Start video playback"""
        self.player.start()
    
    def play_audio(self):
        """Start playing audio synced with video position"""
        if self.audio_path and os.path.exists(self.audio_path):
            try:
                # Get current video position
                video_pos = self.player.get_position_seconds()
                video_duration = self.player.get_duration_seconds()
                
                # Stop any currently playing music first
                pygame.mixer.music.stop()
                
                # Load and play
                pygame.mixer.music.load(self.audio_path)
                
                # Apply volume (0-200 maps to 0.0-2.0, but pygame max is 1.0)
                # So we use volume/100 capped at 1.0, and boost via gain if needed
                vol = min(1.0, self.volume / 100.0)
                pygame.mixer.music.set_volume(vol)
                
                # Calculate seek position (modulo duration for looping)
                seek_pos = 0
                if video_duration > 0:
                    seek_pos = video_pos % video_duration
                
                # Start playing from the seek position
                pygame.mixer.music.play(loops=-1, start=seek_pos)
                
                self.audio_active = True
                print(f"  Playing audio from {seek_pos:.1f}s (vol: {self.volume}%)")
            except Exception as e:
                print(f"  Audio play error: {e}")
        else:
            print(f"  No audio file for this frame")
    
    def stop_audio(self):
        """Stop playing audio"""
        try:
            pygame.mixer.music.stop()
        except:
            pass
        self.audio_active = False
    
    def stop(self):
        """Stop video playback"""
        self.player.stop()
    
    def update(self):
        """Update surface from current video frame with proper zoom/pan
        
        Browser logic (from index.html):
        - video.style.width = (100 * zoom)% - video is zoom% of frame width
        - video.style.height = (100 * zoom)% - video is zoom% of frame height  
        - video.style.left = calc(50% + offsetX px) - center + offset
        - video.style.transform = translate(-50%, -50%) - centers video
        
        So: video covers frame, then scaled by zoom, centered, then offset
        """
        frame = self.player.get_frame()
        if frame is not None:
            try:
                src_h, src_w = frame.shape[:2]
                
                # Zoom factor from config
                zoom = self.video_zoom / 100.0
                
                # First: scale video to COVER the frame (like object-fit: cover)
                # Calculate scale needed to cover frame
                scale_to_cover_w = self.width / src_w
                scale_to_cover_h = self.height / src_h
                cover_scale = max(scale_to_cover_w, scale_to_cover_h)
                
                # Apply zoom on top of cover scale
                total_scale = cover_scale * zoom
                
                # Final video size
                video_w = int(src_w * total_scale)
                video_h = int(src_h * total_scale)
                
                # Resize video
                frame_scaled = cv2.resize(frame, (video_w, video_h))
                
                # Calculate crop region
                # Video is centered, then offset applied
                # Offset is in original config pixels, scale it for display
                offset_x = int(self.video_offset_x * self.scale)
                offset_y = int(self.video_offset_y * self.scale)
                
                # Center of video + offset
                center_x = video_w // 2 + offset_x
                center_y = video_h // 2 + offset_y
                
                # Crop from center
                crop_x1 = center_x - self.width // 2
                crop_y1 = center_y - self.height // 2
                
                # Clamp to valid range
                crop_x1 = max(0, min(crop_x1, video_w - self.width))
                crop_y1 = max(0, min(crop_y1, video_h - self.height))
                crop_x2 = min(crop_x1 + self.width, video_w)
                crop_y2 = min(crop_y1 + self.height, video_h)
                
                # Crop
                frame_cropped = frame_scaled[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # Ensure correct size
                if frame_cropped.shape[1] != self.width or frame_cropped.shape[0] != self.height:
                    frame_cropped = cv2.resize(frame_cropped, (self.width, self.height))
                
                # Convert to pygame surface
                self.surface = pygame.surfarray.make_surface(
                    frame_cropped.swapaxes(0, 1)
                )
            except Exception as e:
                pass
    
    def draw(self, screen, debug_mode=False, is_editing=False):
        """Draw video frame to screen"""
        if self.surface:
            screen.blit(self.surface, (self.x, self.y))
        else:
            # Draw black rectangle if no video
            pygame.draw.rect(screen, (0, 0, 0), 
                           (self.x, self.y, self.width, self.height))
        
        # Highlight if being edited
        if is_editing:
            pygame.draw.rect(screen, (255, 255, 0), 
                           (self.x, self.y, self.width, self.height), 4)
        
        # Draw key label
        font_size = max(10, min(self.width, self.height) // 10)
        font = pygame.font.Font(None, font_size)
        
        if is_editing:
            label_bg = (255, 255, 0)  # Yellow when editing
        elif self.audio_active:
            label_bg = (0, 200, 0)
        else:
            label_bg = (30, 30, 30)
        
        label = font.render(self.key_letter, True, (0, 0, 0) if is_editing else (255, 255, 255))
        label_rect = label.get_rect()
        label_rect.bottomright = (self.x + self.width - 5, 
                                  self.y + self.height - 5)
        
        # Draw label background
        bg_rect = label_rect.inflate(6, 4)
        pygame.draw.rect(screen, label_bg, bg_rect, border_radius=3)
        screen.blit(label, label_rect)
        
        # Debug overlay
        if debug_mode:
            # Green border
            pygame.draw.rect(screen, (0, 255, 0), 
                           (self.x, self.y, self.width, self.height), 2)
            # Frame number in center
            big_font = pygame.font.Font(None, 48)
            num_label = big_font.render(str(self.frame_id + 1), True, (0, 255, 0))
            num_rect = num_label.get_rect(center=(self.x + self.width // 2,
                                                   self.y + self.height // 2))
            screen.blit(num_label, num_rect)


class PhotoWallApp:
    """Main application"""
    
    def __init__(self):
        pygame.init()
        mixer.init()
        
        # Load config
        self.config = self.load_config()
        self.resolution = self.config.get("resolution", 
                                          {"width": 3840, "height": 2160})
        
        # Get display info
        display_info = pygame.display.Info()
        self.screen_width = display_info.current_w
        self.screen_height = display_info.current_h
        
        # Calculate scale
        self.scale_x = self.screen_width / self.resolution["width"]
        self.scale_y = self.screen_height / self.resolution["height"]
        self.scale = min(self.scale_x, self.scale_y)
        
        # Create window
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Photo Wall - Native App")
        
        # State
        self.running = True
        self.debug_mode = False
        self.fullscreen = False
        self.edit_mode = False
        self.edit_frame_idx = 0  # Which frame we're editing
        self.video_frames = []
        
        # Load videos
        self.setup_videos()
        
        # Start all videos
        for vf in self.video_frames:
            vf.start()
        
        print("\n" + "=" * 50)
        print(f"Photo Wall Native App [{PROFILE.upper()}]")
        print("=" * 50)
        print(f"Profile: {PROFILE} | Videos: {VIDEOS_DIR}")
        print(f"Loaded {len(self.video_frames)} videos")
        print("Controls:")
        print("  A-Q: Unmute audio for that frame")
        print("  0: Mute all audio")
        print("  1: Toggle debug overlay")
        print("  2: Toggle EDIT MODE (live adjust)")
        print("  3: Toggle fullscreen")
        print("  ESC: Exit")
        print("\nEDIT MODE controls:")
        print("  Tab: Cycle to next frame")
        print("  Arrow keys: Pan video")
        print("  +/-: Zoom in/out")
        print("  V: Cycle volume (50/100/150/200%)")
        print("  Shift +/-: Fine volume adjust")
        print("  R: Reset crop for current frame")
        print("  S: Save config to native_config.json")
        print("=" * 50 + "\n")
    
    def load_config(self):
        """Load configuration from JSON - prefer native_config.json if exists"""
        if os.path.exists(NATIVE_CONFIG_FILE):
            print(f"Loading from {NATIVE_CONFIG_FILE}")
            with open(NATIVE_CONFIG_FILE, "r") as f:
                return json.load(f)
        if os.path.exists(CONFIG_FILE):
            print(f"Loading from {CONFIG_FILE}")
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {"frames": [], "resolution": {"width": 3840, "height": 2160}}
    
    def setup_videos(self):
        """Create video frames from config"""
        frames = self.config.get("frames", [])
        
        for frame_config in frames:
            if not frame_config.get("visible", True):
                continue
            
            video_name = frame_config.get("video", "")
            video_path = os.path.join(VIDEOS_DIR, video_name) if video_name else ""
            
            # Scale coordinates
            x = int(frame_config.get("x", 0) * self.scale)
            y = int(frame_config.get("y", 0) * self.scale)
            w = int(frame_config.get("width", 200) * self.scale)
            h = int(frame_config.get("height", 200) * self.scale)
            
            vf = VideoFrame(
                frame_id=frame_config.get("id", len(self.video_frames)),
                video_path=video_path,
                x=x, y=y, width=w, height=h,
                video_offset_x=frame_config.get("videoOffsetX", 0),
                video_offset_y=frame_config.get("videoOffsetY", 0),
                video_zoom=frame_config.get("videoZoom", 100),
                scale=self.scale,
                volume=frame_config.get("volume", 100)
            )
            self.video_frames.append(vf)
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                key = event.key
                
                # ESC - exit
                if key == pygame.K_ESCAPE:
                    self.running = False
                
                # 0 - mute all
                elif key == pygame.K_0:
                    self.mute_all()
                    print("All audio muted")
                
                # 1 - toggle debug
                elif key == pygame.K_1:
                    self.debug_mode = not self.debug_mode
                    print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                
                # 2 - toggle edit mode
                elif key == pygame.K_2:
                    self.edit_mode = not self.edit_mode
                    print(f"Edit mode: {'ON' if self.edit_mode else 'OFF'}")
                    if self.edit_mode and self.video_frames:
                        vf = self.video_frames[self.edit_frame_idx]
                        print(f"  Editing frame {self.edit_frame_idx} ({vf.key_letter})")
                
                # 3 - toggle fullscreen
                elif key == pygame.K_3:
                    self.toggle_fullscreen()
                
                # Edit mode controls
                elif self.edit_mode and self.video_frames:
                    vf = self.video_frames[self.edit_frame_idx]
                    cfg = self.config["frames"][self.edit_frame_idx]
                    
                    # Tab - next frame
                    if key == pygame.K_TAB:
                        self.edit_frame_idx = (self.edit_frame_idx + 1) % len(self.video_frames)
                        vf = self.video_frames[self.edit_frame_idx]
                        print(f"  Now editing frame {self.edit_frame_idx} ({vf.key_letter})")
                    
                    # Arrow keys - pan
                    elif key == pygame.K_LEFT:
                        cfg["videoOffsetX"] = cfg.get("videoOffsetX", 0) - 10
                        vf.video_offset_x = cfg["videoOffsetX"]
                        print(f"  Pan: ({cfg['videoOffsetX']}, {cfg.get('videoOffsetY', 0)})")
                    elif key == pygame.K_RIGHT:
                        cfg["videoOffsetX"] = cfg.get("videoOffsetX", 0) + 10
                        vf.video_offset_x = cfg["videoOffsetX"]
                        print(f"  Pan: ({cfg['videoOffsetX']}, {cfg.get('videoOffsetY', 0)})")
                    elif key == pygame.K_UP:
                        cfg["videoOffsetY"] = cfg.get("videoOffsetY", 0) - 10
                        vf.video_offset_y = cfg["videoOffsetY"]
                        print(f"  Pan: ({cfg.get('videoOffsetX', 0)}, {cfg['videoOffsetY']})")
                    elif key == pygame.K_DOWN:
                        cfg["videoOffsetY"] = cfg.get("videoOffsetY", 0) + 10
                        vf.video_offset_y = cfg["videoOffsetY"]
                        print(f"  Pan: ({cfg.get('videoOffsetX', 0)}, {cfg['videoOffsetY']})")
                    
                    # +/- or =/- for zoom (no modifier)
                    elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        mods = pygame.key.get_mods()
                        if mods & pygame.KMOD_SHIFT:
                            # Shift+Plus = volume up
                            cfg["volume"] = min(400, cfg.get("volume", 100) + 10)
                            vf.volume = cfg["volume"]
                            print(f"  Volume: {cfg['volume']}%")
                        else:
                            cfg["videoZoom"] = min(400, cfg.get("videoZoom", 100) + 10)
                            vf.video_zoom = cfg["videoZoom"]
                            print(f"  Zoom: {cfg['videoZoom']}%")
                    elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        mods = pygame.key.get_mods()
                        if mods & pygame.KMOD_SHIFT:
                            # Shift+Minus = volume down
                            cfg["volume"] = max(0, cfg.get("volume", 100) - 10)
                            vf.volume = cfg["volume"]
                            print(f"  Volume: {cfg['volume']}%")
                        else:
                            cfg["videoZoom"] = max(50, cfg.get("videoZoom", 100) - 10)
                            vf.video_zoom = cfg["videoZoom"]
                            print(f"  Zoom: {cfg['videoZoom']}%")
                    
                    # V - quick volume presets
                    elif key == pygame.K_v:
                        # Cycle through volume presets: 100 -> 150 -> 200 -> 50 -> 100
                        current = cfg.get("volume", 100)
                        if current < 100:
                            cfg["volume"] = 100
                        elif current < 150:
                            cfg["volume"] = 150
                        elif current < 200:
                            cfg["volume"] = 200
                        else:
                            cfg["volume"] = 50
                        vf.volume = cfg["volume"]
                        print(f"  Volume: {cfg['volume']}%")
                    
                    # R - reset crop
                    elif key == pygame.K_r:
                        cfg["videoOffsetX"] = 0
                        cfg["videoOffsetY"] = 0
                        cfg["videoZoom"] = 100
                        vf.video_offset_x = 0
                        vf.video_offset_y = 0
                        vf.video_zoom = 100
                        print(f"  Reset frame {self.edit_frame_idx}")
                    
                    # S - save config
                    elif key == pygame.K_s:
                        self.save_config()
                
                # A-Q - unmute specific frame (only when not in edit mode)
                elif not self.edit_mode and pygame.K_a <= key <= pygame.K_q:
                    idx = key - pygame.K_a
                    if idx < len(self.video_frames):
                        self.unmute_frame(idx)
                        print(f"Audio ON for frame {idx + 1} ({chr(65 + idx)})")
    
    def mute_all(self):
        """Mute all frames"""
        for vf in self.video_frames:
            vf.muted = True
            vf.stop_audio()
    
    def unmute_frame(self, idx):
        """Unmute specific frame"""
        # First: stop all audio and mark all as muted
        for vf in self.video_frames:
            vf.muted = True
            vf.audio_active = False
        
        # Stop global music
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        # Then: play audio for the selected frame
        if idx < len(self.video_frames):
            vf = self.video_frames[idx]
            vf.muted = False
            vf.play_audio()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                (0, 0), pygame.FULLSCREEN
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.RESIZABLE
            )
    
    def save_config(self):
        """Save config to native_config.json"""
        with open(NATIVE_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        print(f"Saved to {NATIVE_CONFIG_FILE}")
    
    def update(self):
        """Update all video frames"""
        for vf in self.video_frames:
            vf.update()
    
    def draw(self):
        """Draw everything"""
        self.screen.fill((0, 0, 0))
        
        for i, vf in enumerate(self.video_frames):
            # Highlight currently edited frame
            is_editing = self.edit_mode and i == self.edit_frame_idx
            vf.draw(self.screen, self.debug_mode, is_editing)
        
        # Draw edit mode overlay
        if self.edit_mode and self.video_frames:
            self.draw_edit_overlay()
        
        pygame.display.flip()
    
    def draw_edit_overlay(self):
        """Draw edit mode info overlay"""
        vf = self.video_frames[self.edit_frame_idx]
        cfg = self.config["frames"][self.edit_frame_idx]
        
        # Background panel
        panel_w, panel_h = 320, 145
        panel_x, panel_y = 10, 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        self.screen.blit(panel, (panel_x, panel_y))
        
        # Text
        font = pygame.font.Font(None, 28)
        lines = [
            f"EDIT MODE - Frame {self.edit_frame_idx} ({vf.key_letter})",
            f"Video: {cfg.get('video', 'None')[:25]}",
            f"Pan: ({cfg.get('videoOffsetX', 0)}, {cfg.get('videoOffsetY', 0)})",
            f"Zoom: {cfg.get('videoZoom', 100)}%  |  Volume: {cfg.get('volume', 100)}%",
            "Tab=next  Arrows=pan  +/-=zoom",
            "V=volume cycle  Shift+/-=vol  S=save"
        ]
        
        y = panel_y + 8
        for line in lines:
            text = font.render(line, True, (0, 255, 0))
            self.screen.blit(text, (panel_x + 10, y))
            y += 22
    
    def run(self):
        """Main loop"""
        clock = pygame.time.Clock()
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            clock.tick(30)  # 30 FPS display refresh
        
        # Cleanup
        for vf in self.video_frames:
            vf.stop()
        
        pygame.quit()


def main():
    app = PhotoWallApp()
    app.run()


if __name__ == "__main__":
    main()
