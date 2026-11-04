"""
Native App Control Panel
Adjust video positions and save to native_config.json
Run this alongside native_app.py
"""

import json
import os
import tkinter as tk
from tkinter import ttk

CONFIG_FILE = "config.json"
NATIVE_CONFIG_FILE = "native_config.json"

class ControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Native App Control Panel")
        self.root.geometry("400x700")
        
        # Load config
        self.config = self.load_config()
        self.frames = self.config.get("frames", [])
        
        # Current frame index
        self.current_frame = 0
        
        # Create UI
        self.create_ui()
        self.load_frame_values()
    
    def load_config(self):
        """Load config - prefer native_config if exists"""
        if os.path.exists(NATIVE_CONFIG_FILE):
            with open(NATIVE_CONFIG_FILE, "r") as f:
                return json.load(f)
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {"frames": [], "resolution": {"width": 3840, "height": 2160}}
    
    def save_config(self):
        """Save to native config file"""
        with open(NATIVE_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        print(f"Saved to {NATIVE_CONFIG_FILE}")
    
    def create_ui(self):
        # Frame selector
        selector_frame = ttk.Frame(self.root, padding=10)
        selector_frame.pack(fill=tk.X)
        
        ttk.Label(selector_frame, text="Frame:").pack(side=tk.LEFT)
        
        self.frame_var = tk.StringVar()
        frame_options = [f"{i}: {chr(65+i)} - {f.get('video', 'No video')[:20]}" 
                        for i, f in enumerate(self.frames)]
        self.frame_combo = ttk.Combobox(selector_frame, textvariable=self.frame_var,
                                        values=frame_options, state="readonly", width=35)
        self.frame_combo.pack(side=tk.LEFT, padx=5)
        self.frame_combo.bind("<<ComboboxSelected>>", self.on_frame_select)
        if frame_options:
            self.frame_combo.current(0)
        
        # Controls frame
        controls = ttk.LabelFrame(self.root, text="Position & Size", padding=10)
        controls.pack(fill=tk.X, padx=10, pady=5)
        
        # X, Y
        row1 = ttk.Frame(controls)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="X:", width=8).pack(side=tk.LEFT)
        self.x_var = tk.IntVar()
        self.x_entry = ttk.Entry(row1, textvariable=self.x_var, width=10)
        self.x_entry.pack(side=tk.LEFT)
        ttk.Label(row1, text="  Y:", width=8).pack(side=tk.LEFT)
        self.y_var = tk.IntVar()
        self.y_entry = ttk.Entry(row1, textvariable=self.y_var, width=10)
        self.y_entry.pack(side=tk.LEFT)
        
        # Width, Height
        row2 = ttk.Frame(controls)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Width:", width=8).pack(side=tk.LEFT)
        self.w_var = tk.IntVar()
        self.w_entry = ttk.Entry(row2, textvariable=self.w_var, width=10)
        self.w_entry.pack(side=tk.LEFT)
        ttk.Label(row2, text="  Height:", width=8).pack(side=tk.LEFT)
        self.h_var = tk.IntVar()
        self.h_entry = ttk.Entry(row2, textvariable=self.h_var, width=10)
        self.h_entry.pack(side=tk.LEFT)
        
        # Video crop controls
        crop_frame = ttk.LabelFrame(self.root, text="Video Crop/Pan", padding=10)
        crop_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Offset X, Y
        row3 = ttk.Frame(crop_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Pan X:", width=8).pack(side=tk.LEFT)
        self.ox_var = tk.IntVar()
        self.ox_entry = ttk.Entry(row3, textvariable=self.ox_var, width=10)
        self.ox_entry.pack(side=tk.LEFT)
        ttk.Label(row3, text="  Pan Y:", width=8).pack(side=tk.LEFT)
        self.oy_var = tk.IntVar()
        self.oy_entry = ttk.Entry(row3, textvariable=self.oy_var, width=10)
        self.oy_entry.pack(side=tk.LEFT)
        
        # Zoom
        row4 = ttk.Frame(crop_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="Zoom:", width=8).pack(side=tk.LEFT)
        self.zoom_var = tk.IntVar()
        self.zoom_scale = ttk.Scale(row4, from_=50, to=400, variable=self.zoom_var,
                                    orient=tk.HORIZONTAL, length=200)
        self.zoom_scale.pack(side=tk.LEFT)
        self.zoom_label = ttk.Label(row4, text="100%", width=6)
        self.zoom_label.pack(side=tk.LEFT)
        self.zoom_scale.bind("<Motion>", self.update_zoom_label)
        
        # Buttons
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Apply", command=self.apply_values).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset Crop", command=self.reset_crop).pack(side=tk.LEFT, padx=5)
        
        # Quick adjust buttons
        adjust_frame = ttk.LabelFrame(self.root, text="Quick Adjust", padding=10)
        adjust_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Pan buttons
        pan_row = ttk.Frame(adjust_frame)
        pan_row.pack(fill=tk.X, pady=2)
        ttk.Label(pan_row, text="Pan:").pack(side=tk.LEFT)
        ttk.Button(pan_row, text="←", width=3, command=lambda: self.quick_pan(-10, 0)).pack(side=tk.LEFT)
        ttk.Button(pan_row, text="→", width=3, command=lambda: self.quick_pan(10, 0)).pack(side=tk.LEFT)
        ttk.Button(pan_row, text="↑", width=3, command=lambda: self.quick_pan(0, -10)).pack(side=tk.LEFT)
        ttk.Button(pan_row, text="↓", width=3, command=lambda: self.quick_pan(0, 10)).pack(side=tk.LEFT)
        
        # Zoom buttons
        zoom_row = ttk.Frame(adjust_frame)
        zoom_row.pack(fill=tk.X, pady=2)
        ttk.Label(zoom_row, text="Zoom:").pack(side=tk.LEFT)
        ttk.Button(zoom_row, text="-10", width=5, command=lambda: self.quick_zoom(-10)).pack(side=tk.LEFT)
        ttk.Button(zoom_row, text="+10", width=5, command=lambda: self.quick_zoom(10)).pack(side=tk.LEFT)
        ttk.Button(zoom_row, text="-50", width=5, command=lambda: self.quick_zoom(-50)).pack(side=tk.LEFT)
        ttk.Button(zoom_row, text="+50", width=5, command=lambda: self.quick_zoom(50)).pack(side=tk.LEFT)
        
        # Info
        info_frame = ttk.LabelFrame(self.root, text="Info", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        self.info_label = ttk.Label(info_frame, text="Select a frame to edit")
        self.info_label.pack()
        
        # Instructions
        inst_frame = ttk.LabelFrame(self.root, text="Instructions", padding=10)
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(inst_frame, text="1. Select frame from dropdown").pack(anchor=tk.W)
        ttk.Label(inst_frame, text="2. Adjust values or use quick buttons").pack(anchor=tk.W)
        ttk.Label(inst_frame, text="3. Click Apply to see changes").pack(anchor=tk.W)
        ttk.Label(inst_frame, text="4. Click Save Config when done").pack(anchor=tk.W)
        ttk.Label(inst_frame, text="5. Restart native_app.py to load").pack(anchor=tk.W)
    
    def update_zoom_label(self, event=None):
        self.zoom_label.config(text=f"{int(self.zoom_var.get())}%")
    
    def on_frame_select(self, event=None):
        idx = self.frame_combo.current()
        if idx >= 0:
            self.current_frame = idx
            self.load_frame_values()
    
    def load_frame_values(self):
        if self.current_frame >= len(self.frames):
            return
        f = self.frames[self.current_frame]
        self.x_var.set(int(f.get("x", 0)))
        self.y_var.set(int(f.get("y", 0)))
        self.w_var.set(int(f.get("width", 200)))
        self.h_var.set(int(f.get("height", 200)))
        self.ox_var.set(int(f.get("videoOffsetX", 0)))
        self.oy_var.set(int(f.get("videoOffsetY", 0)))
        self.zoom_var.set(int(f.get("videoZoom", 100)))
        self.update_zoom_label()
        self.info_label.config(text=f"Frame {self.current_frame} ({chr(65+self.current_frame)}): {f.get('video', 'No video')}")
    
    def apply_values(self):
        if self.current_frame >= len(self.frames):
            return
        f = self.frames[self.current_frame]
        f["x"] = self.x_var.get()
        f["y"] = self.y_var.get()
        f["width"] = self.w_var.get()
        f["height"] = self.h_var.get()
        f["videoOffsetX"] = self.ox_var.get()
        f["videoOffsetY"] = self.oy_var.get()
        f["videoZoom"] = int(self.zoom_var.get())
        print(f"Applied: Frame {self.current_frame} - Zoom:{f['videoZoom']}%, Pan:({f['videoOffsetX']}, {f['videoOffsetY']})")
    
    def reset_crop(self):
        self.ox_var.set(0)
        self.oy_var.set(0)
        self.zoom_var.set(100)
        self.update_zoom_label()
        self.apply_values()
    
    def quick_pan(self, dx, dy):
        self.ox_var.set(self.ox_var.get() + dx)
        self.oy_var.set(self.oy_var.get() + dy)
        self.apply_values()
    
    def quick_zoom(self, dz):
        new_zoom = max(50, min(400, int(self.zoom_var.get()) + dz))
        self.zoom_var.set(new_zoom)
        self.update_zoom_label()
        self.apply_values()
    
    def run(self):
        self.root.mainloop()


def main():
    app = ControlPanel()
    app.run()


if __name__ == "__main__":
    main()
