import os
import re
import subprocess
import shutil
import threading
import webbrowser
import json
from tkinter import Tk, filedialog, messagebox, Label, Button, Entry, StringVar, DoubleVar, OptionMenu, IntVar
from tkinter import ttk

# Define paths to the tools in the "tools" folder
tools_dir = os.path.join(os.path.dirname(__file__), "tools")
dovi_tool_path = os.path.join(tools_dir, "dovi_tool.exe")
ffmpeg_path = os.path.join(tools_dir, "ffmpeg.exe")
mkvmerge_path = os.path.join(tools_dir, "mkvmerge.exe")

# Configuration file path
config_file = os.path.join(os.path.dirname(__file__), "config.json")

# Global variable to track if the process should be aborted
abort_process = False

# Load settings from the configuration file
def load_settings():
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    return {}

# Save settings to the configuration file
def save_settings(settings):
    with open(config_file, "w") as f:
        json.dump(settings, f)

def extract_hevc_stream(input_file, hevc_file):
    command = [
        ffmpeg_path,
        '-hwaccel', 'cuda',
        '-hwaccel_output_format', 'cuda',
        '-c:v', 'hevc_cuvid',
        '-i', input_file,
        '-c:v', 'copy',
        '-an', '-sn', '-dn',
        hevc_file
    ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

def extract_dovi_metadata(hevc_file, metadata_file):
    # Use -m 4 for RPU extraction
    command = [
        dovi_tool_path,
        '-m', '4',
        'extract-rpu',
        '-i', hevc_file,
        '-o', metadata_file
    ]
    result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # Check if RPU was found
    if "Found no RPU" in result.stderr:
        raise ValueError("No Dolby Vision metadata found in the source file")

    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

def reencode_video(input_file, output_file, quality, encoding_mode, encoding_quality_preset, progress_callback):
    cmd_duration = [ffmpeg_path, '-i', input_file]
    result = subprocess.run(cmd_duration, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    duration_match = re.search(r"Duration: (\d{2}:\d{2}:\d{2}\.\d{2})", result.stderr)
    total_duration = 0
    if duration_match:
        time_str = duration_match.group(1)
        hours, minutes, seconds = map(float, time_str.split(':'))
        total_duration = hours * 3600 + minutes * 60 + seconds

    if encoding_mode == "CUDA":
        cmd = [
            ffmpeg_path,
            '-hwaccel', 'cuda',
            '-hwaccel_output_format', 'cuda',
            '-c:v', 'hevc_cuvid',
            '-i', input_file,
            '-c:v', 'hevc_nvenc',
            '-preset', encoding_quality_preset,
            '-tune', 'hq',
            '-rc', 'vbr',
            '-cq', str(quality),
            '-b:v', '0',
            '-c:a', 'copy',
            '-y', output_file
        ]
    elif encoding_mode == "QSV":
        cmd = [
            ffmpeg_path,
            '-init_hw_device', 'qsv=hw',  # Initialize QSV device
            '-filter_hw_device', 'hw',
            '-hwaccel', 'qsv',
            '-hwaccel_output_format', 'qsv',
            '-c:v', 'hevc_qsv',  # Use QSV for decoding
            '-i', input_file,
            '-c:v', 'hevc_qsv',  # Use QSV for encoding
            '-preset', encoding_quality_preset,
            '-global_quality', str(quality),  # Correct parameter for QSV
            '-c:a', 'copy',
            '-y', output_file
        ]
    else:
        cmd = [
            ffmpeg_path,
            '-i', input_file,
            '-c:v', 'libx265',
            '-crf', str(quality),
            '-preset', encoding_quality_preset, # Using preset here for CPU as well
            '-c:a', 'copy',
            '-y', output_file
        ]

    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)
    while True:
        if abort_process:
            process.terminate()
            break
        line = process.stderr.readline()
        if not line:
            break
        if 'time=' in line:
            time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
            if time_match and total_duration > 0:
                current_time = time_match.group(1)
                hours, minutes, seconds = map(float, current_time.split(':'))
                current_seconds = hours * 3600 + minutes * 60 + seconds
                progress = (current_seconds / total_duration) * 100
                progress_callback(progress)
    process.wait()

def transcode_audio(input_file, output_file, channels, bitrate):
    if channels == "No":
        return input_file
    channel_map = {"2.0 Stereo": "2", "5.1 Surround": "6", "7.1 Surround": "8"}
    command = [
        ffmpeg_path,
        '-i', input_file,
        '-map', '0:a',
        '-c:a', 'aac',
        '-b:a', bitrate,
        '-ac', channel_map[channels],
        output_file
    ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return output_file

def inject_dovi_metadata(video_file, metadata_file, output_file):
    command = [
        dovi_tool_path,
        '-m', '4',
        'inject-rpu',
        '-i', video_file,
        '--rpu-in', metadata_file,
        '-o', output_file
    ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

def remux_video(video_file, audio_file, original_file, output_file, keep_original_audio):
    if audio_file == original_file:
        if keep_original_audio == "Keep":
            command = [
                mkvmerge_path,
                '-o', output_file,
                video_file,
                '--no-video', original_file,
                '--no-track-tags',
                '--no-global-tags'
            ]
        else:
            command = [
                mkvmerge_path,
                '-o', output_file,
                video_file,
                '--no-audio',
                '--no-track-tags',
                '--no-global-tags'
            ]
    else:
        if keep_original_audio == "Keep":
            command = [
                mkvmerge_path,
                '-o', output_file,
                video_file,
                audio_file,
                '--no-video', original_file,
                '--no-track-tags',
                '--no-global-tags'
            ]
        else:
            command = [
                mkvmerge_path,
                '-o', output_file,
                video_file,
                audio_file,
                '--no-audio',
                '--no-track-tags',
                '--no-global-tags'
            ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ReDoVi")

        # Load saved settings
        self.settings = load_settings()

        # Initialize variables with saved settings or defaults
        self.input_file_var = StringVar()
        self.output_folder_var = StringVar()
        self.quality_var = IntVar(value=self.settings.get("quality", 23))
        self.audio_channels_var = StringVar(value=self.settings.get("audio_channels", "No"))
        self.encoding_mode_var = StringVar(value=self.settings.get("encoding_mode", "CUDA"))
        self.progress_value_var = DoubleVar(value=0.0)
        self.audio_bitrate_var = StringVar(value=self.settings.get("audio_bitrate", "640k"))
        self.keep_original_audio_var = StringVar(value=self.settings.get("keep_original_audio", "Keep"))
        self.encoding_quality_var = StringVar(value=self.settings.get("encoding_quality", "slow"))
        self.is_folder_input = False # Track if folder input is selected

        # Define quality presets for each encoding mode
        self.quality_presets = {
            "CUDA": ["slow", "medium", "fast", "hp", "hq"], # Added more CUDA presets
            "QSV": ["slow", "medium", "fast", "faster", "veryfast"], # Added more QSV presets
            "CPU": ["ultrafast", "faster", "fast", "medium", "slow", "veryslow", "slower", "placebo"] # Added more CPU presets
        }
        # Make sure default preset is valid, if not, set to first available
        default_preset = self.settings.get("encoding_quality", "medium")
        if default_preset not in self.quality_presets.get(self.settings.get("encoding_mode", "CUDA"), ["slow", "medium", "fast"]): # Default fallback if no mode or preset is saved, use original defaults.
            self.encoding_quality_var.set(self.quality_presets.get(self.settings.get("encoding_mode", "CUDA"), ["slow", "medium", "fast"])[0]) # Set to first preset of current or default mode

        self.setup_gui()
        self.update_quality_presets() # Initial setup of quality presets based on default encoding mode

        # Save settings when the application closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_gui(self):
        Label(self.root, text="ReDoVi", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=10)
        Label(self.root, text="by DistEarth", font=("Arial", 8)).grid(row=1, column=0, columnspan=4) # Subtitle

        # Input Path (can be File or Folder)
        Label(self.root, text="Source Path:").grid(row=2, column=0, padx=5, pady=5) # Changed label to Source Path
        self.input_file_entry = Entry(self.root, textvariable=self.input_file_var, width=50, fg="grey")
        self.input_file_entry.grid(row=2, column=1, padx=5, pady=5)
        self.input_file_entry.insert(0, "Choose your DV source video or folder") # Updated placeholder
        self.input_file_entry.bind("<FocusIn>", self.clear_input_placeholder)
        self.input_file_entry.bind("<FocusOut>", self.set_input_placeholder)
        Button(self.root, text="Browse File", command=self.browse_input_file).grid(row=2, column=2, padx=5, pady=5) # Renamed button
        Button(self.root, text="Browse Folder", command=self.browse_input_folder).grid(row=2, column=3, padx=5, pady=5) # Added Browse Folder button

        # Output Folder
        Label(self.root, text="Output Folder:").grid(row=3, column=0, padx=5, pady=5)
        self.output_folder_entry = Entry(self.root, textvariable=self.output_folder_var, width=50, fg="grey")
        self.output_folder_entry.grid(row=3, column=1, padx=5, pady=5)
        self.output_folder_entry.insert(0, "Same as input unless changed")
        self.output_folder_entry.bind("<FocusIn>", self.clear_output_placeholder)
        self.output_folder_entry.bind("<FocusOut>", self.set_output_placeholder)
        Button(self.root, text="Browse", command=self.browse_output).grid(row=3, column=2, padx=5, pady=5)

        # Quality
        Label(self.root, text="Quality (16-40):").grid(row=4, column=0, padx=5, pady=5)
        ttk.Combobox(self.root, textvariable=self.quality_var, values=list(range(16, 41)), width=7).grid(row=4, column=1, padx=5, pady=5)

        # Audio
        Label(self.root, text="Convert Audio:").grid(row=5, column=0, padx=5, pady=5)
        OptionMenu(self.root, self.audio_channels_var, *["No", "2.0 Stereo", "5.1 Surround", "7.1 Surround"]).grid(row=5, column=1, padx=5, pady=5)
        Label(self.root, text="Audio Bitrate:").grid(row=6, column=0, padx=5, pady=5)
        OptionMenu(self.root, self.audio_bitrate_var, *["128k", "192k", "256k", "384k", "480k", "640k"]).grid(row=6, column=1, padx=5, pady=5)
        Label(self.root, text="Keep Original Audio:").grid(row=5, column=2, padx=5, pady=5)
        OptionMenu(self.root, self.keep_original_audio_var, *["Keep", "Remove"]).grid(row=5, column=3, padx=5, pady=5)

        # Encoding
        Label(self.root, text="Encoding Mode:").grid(row=7, column=0, padx=5, pady=5)
        self.encoding_mode_optionmenu = OptionMenu(self.root, self.encoding_mode_var, *["CUDA", "QSV", "CPU"], command=self.update_quality_presets) # Added command to update presets
        self.encoding_mode_optionmenu.grid(row=7, column=1, padx=5, pady=5)
        Label(self.root, text="Quality Preset:").grid(row=7, column=2, padx=5, pady=5)
        self.encoding_quality_optionmenu_var = self.encoding_quality_var # Keep a reference to StringVar for OptionMenu update
        self.encoding_quality_optionmenu = OptionMenu(self.root, self.encoding_quality_var, *self.quality_presets["CUDA"]) # Initialize with CUDA presets. Will be updated.
        self.encoding_quality_optionmenu.grid(row=7, column=3, padx=5, pady=5)


        # Progress
        self.progress_text_var = StringVar(value="Waiting to start...")
        Label(self.root, textvariable=self.progress_text_var).grid(row=8, column=0, columnspan=4, padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_value_var, maximum=100)
        self.progress_bar.grid(row=9, column=0, columnspan=4, padx=5, pady=5, sticky='we')

        # Buttons
        self.process_button = Button(self.root, text="Process Video", command=self.start_processing)
        self.process_button.grid(row=10, column=1, padx=5, pady=20)
        self.abort_button = Button(self.root, text="Abort", command=self.abort_processing, state='disabled')
        self.abort_button.grid(row=10, column=2, padx=5, pady=20)

        # Support Button
        Button(self.root, text="Support This Project", command=self.open_donation_link, bg="lightblue").grid(row=11, column=3, padx=10, pady=10, sticky="se")

        # Credits
        credit = Label(self.root, text="Special thanks to quietvoid", fg="blue", cursor="hand2", font=("Arial", 8))
        credit.grid(row=11, column=0, padx=10, pady=10, sticky="sw")
        credit.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/quietvoid/dovi_tool"))

        # Bottom Text
        bottom_text = "A temp folder will be created in the Output Folder. \nAround four files the size of the transcoded file \nwill be created and deleted when the process \nis complete"
        Label(self.root, text=bottom_text, font=("Arial", 8), justify='center').grid(row=12, column=0, columnspan=4, pady=10)


    def update_quality_presets(self, *args):
        selected_mode = self.encoding_mode_var.get()
        presets = self.quality_presets.get(selected_mode, ["slow", "medium", "fast"]) # Default presets if mode not found.
        menu = self.encoding_quality_optionmenu["menu"]
        menu.delete(0, "end") # Clear old options
        for preset in presets:
            menu.add_command(label=preset, command=lambda value=preset: self.encoding_quality_var.set(value))
        # If current preset is not in new options, reset to first one.
        if self.encoding_quality_var.get() not in presets:
            self.encoding_quality_var.set(presets[0])


    def clear_input_placeholder(self, event):
        if self.input_file_entry.get() == "Choose your DV source video or folder":
            self.input_file_entry.delete(0, "end")
            self.input_file_entry.config(fg="black")

    def set_input_placeholder(self, event):
        if not self.input_file_var.get():
            self.input_file_entry.delete(0, "end")
            self.input_file_entry.insert(0, "Choose your DV source video or folder")
            self.input_file_entry.config(fg="grey")

    def clear_output_placeholder(self, event):
        if self.output_folder_entry.get() == "Same as input unless changed":
            self.output_folder_entry.delete(0, "end")
            self.output_folder_entry.config(fg="black")

    def set_output_placeholder(self, event):
        if not self.output_folder_var.get():
            self.output_folder_entry.delete(0, "end")
            self.output_folder_entry.insert(0, "Same as input unless changed")
            self.output_folder_entry.config(fg="grey")

    def browse_input_file(self):
        file = filedialog.askopenfilename(title="Select video file", filetypes=[("Video Files", "*.mkv *.mp4")])
        if file:
            self.input_file_var.set(file)
            self.input_file_entry.config(fg="black")
            self.is_folder_input = False # Set to file input mode
        else:
            if not self.input_file_var.get():
                self.set_input_placeholder(None)

    def browse_input_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing video files")
        if folder:
            self.input_file_var.set(folder)
            self.input_file_entry.config(fg="black")
            self.is_folder_input = True # Set to folder input mode
        else:
            if not self.input_file_var.get():
                self.set_input_placeholder(None)


    def browse_input(self): # Keep browse_input for backward compatibility if needed, but use specific browse_input_file and browse_input_folder
        self.browse_input_file() # Default to browse file if just 'Browse' is used

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder_var.set(folder)
            self.output_folder_entry.config(fg="black")
        else:
            if not self.output_folder_var.get():
                self.set_output_placeholder(None)

    def update_progress(self, value, text):
        self.progress_text_var.set(text)
        self.progress_value_var.set(value)
        self.root.update_idletasks()

    def open_donation_link(self):
        webbrowser.open("https://www.paypal.com/donate/?hosted_button_id=A38KG42PKBBBY")

    def start_processing(self):
        global abort_process
        abort_process = False  # Reset abort flag

        input_path = self.input_file_var.get() # Get input path which can be file or folder
        output_folder = self.output_folder_var.get()

        if not input_path or input_path == "Choose your DV source video or folder": # Updated placeholder check
            messagebox.showerror("Error", "Please select an input file or folder")
            return

        if output_folder == "Same as input unless changed" or not output_folder:
            output_folder = None # Determine output folder dynamically inside processing function


        try:
            if self.quality_var.get() < 16 or self.quality_var.get() > 40:
                messagebox.showerror("Error", "Quality must be between 16-40")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid quality value")
            return

        self.process_button.config(state='disabled')
        self.abort_button.config(state='normal')

        if self.is_folder_input:
            threading.Thread(
                target=self.process_folder, # Call process_folder if folder input
                args=(input_path, output_folder),
                daemon=True
            ).start()
        else:
            threading.Thread(
                target=self.process_video, # Call process_video for single file
                args=(input_path, output_folder),
                daemon=True
            ).start()


    def abort_processing(self):
        global abort_process
        abort_process = True
        self.process_button.config(state='normal')
        self.abort_button.config(state='disabled')
        messagebox.showinfo("Abort", "Process aborted.")

    def process_folder(self, input_folder, output_folder):
     
     video_extensions = ('.mkv', '.mp4')
     files_to_process = [f for f in os.listdir(input_folder) if f.lower().endswith(video_extensions)]

     
     if not files_to_process:
         self.root.after(0, lambda: messagebox.showinfo("Info", "No video files found in the selected folder."))
         self.root.after(0, lambda: self.process_button.config(state='normal'))
         self.root.after(0, lambda: self.abort_button.config(state='disabled'))
         return # This return is CORRECT and should stay

     processed_count = 0
     total_files = len(files_to_process)

     for filename in files_to_process:
         if abort_process:
             break

         input_file_path = os.path.join(input_folder, filename)
         current_output_folder = output_folder if output_folder else input_folder

         try:
             # Bind current filename and processed_count to the lambda
             self.root.after(0, lambda f=filename, pc=processed_count: self.update_progress(0, f"Processing file {pc + 1}/{total_files}: {f}"))
             self.process_video_file(input_file_path, current_output_folder)
             processed_count += 1
         except Exception as e:
             error_msg = str(e)
             self.root.after(0, lambda msg=error_msg, f=filename: messagebox.showerror("Error", f"Error processing {f}: {msg}"))

     if abort_process:
         self.root.after(0, lambda: messagebox.showinfo("Abort", "Folder process aborted by user."))
     else:
         self.root.after(0, lambda: messagebox.showinfo("Success", f"Processed {processed_count} of {total_files} files successfully!\nSupport Your Devs!"))

     self.root.after(0, lambda: self.process_button.config(state='normal'))
     self.root.after(0, lambda: self.abort_button.config(state='disabled'))


    def process_video(self, input_file, output_folder): # Renamed to process_video_file and this function will be folder/single dispatch
        if output_folder is None: # Default output to same folder as input file
            current_output_folder = os.path.dirname(input_file)
        else:
            current_output_folder = output_folder

        self.process_video_file(input_file, current_output_folder) # Call actual file processing


    def process_video_file(self, input_file, output_folder): # Actual file processing logic (formerly process_video)
        global abort_process
        temp_folder = os.path.join(output_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)

        try:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            paths = {
                'hevc': os.path.join(temp_folder, f"{base_name}_temp.hevc"),
                'metadata': os.path.join(temp_folder, f"{base_name}_rpu.bin"),
                'reencoded': os.path.join(temp_folder, f"{base_name}_reencoded.mkv"),
                'reencoded_hevc': os.path.join(temp_folder, f"{base_name}_reencoded.hevc"),
                'final_hevc': os.path.join(temp_folder, f"{base_name}_final.hevc"),
                'audio': os.path.join(temp_folder, f"{base_name}_audio.aac"),
                'output': os.path.join(output_folder, f"{base_name}_ReDoVi.mkv")
            }

            self.root.after(0, lambda: self.update_progress(0, "Demuxing DoVi RPU..."))
            extract_hevc_stream(input_file, paths['hevc'])

            self.root.after(0, lambda: self.update_progress(10, "Extracting metadata..."))
            try:
                extract_dovi_metadata(paths['hevc'], paths['metadata'])
            except ValueError as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                raise e # Re-raise to be caught in folder processing loop

            self.root.after(0, lambda: self.update_progress(20, "Transcoding video..."))
            reencode_video(
                input_file,
                paths['reencoded'],
                self.quality_var.get(),
                self.encoding_mode_var.get(),
                self.encoding_quality_var.get(),
                lambda p: self.root.after(0, lambda: self.update_progress(20 + p * 0.8, "Transcoding..."))
            )

            if abort_process:
                raise Exception("Process aborted by user")

            self.root.after(0, lambda: self.update_progress(90, "Extracting HEVC..."))
            extract_hevc_stream(paths['reencoded'], paths['reencoded_hevc'])

            self.root.after(0, lambda: self.update_progress(95, "Injecting metadata..."))
            inject_dovi_metadata(paths['reencoded_hevc'], paths['metadata'], paths['final_hevc'])

            self.root.after(0, lambda: self.update_progress(97, "Processing audio..."))
            audio_file = transcode_audio(
                input_file,
                paths['audio'],
                self.audio_channels_var.get(),
                self.audio_bitrate_var.get()
            )

            self.root.after(0, lambda: self.update_progress(98, "Remuxing..."))
            remux_video(
                paths['final_hevc'],
                audio_file,
                input_file,
                paths['output'],
                self.keep_original_audio_var.get()
            )

            self.root.after(0, lambda: messagebox.showinfo("Success", "Process completed successfully!\nSupport Your Devs!"))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Process failed: {error_msg}"))
            raise e # Re-raise to be caught in folder processing loop
        finally:
            if os.path.exists(temp_folder):
                shutil.rmtree(temp_folder) # Cleanup temp folder after each file processing


    def on_close(self):
        # Save settings before closing
        settings = {
            "quality": self.quality_var.get(),
            "audio_channels": self.audio_channels_var.get(),
            "encoding_mode": self.encoding_mode_var.get(),
            "audio_bitrate": self.audio_bitrate_var.get(),
            "keep_original_audio": self.keep_original_audio_var.get(),
            "encoding_quality": self.encoding_quality_var.get()
        }
        save_settings(settings)
        self.root.destroy()

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()