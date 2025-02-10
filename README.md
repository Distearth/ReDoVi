# ReDoVi - Dolby Vision Video Processing Tool

ReDoVi is a Python-based GUI application designed to process Dolby Vision (DoVi) video files. It allows users to extract, re-encode, and remux Dolby Vision metadata while maintaining high-quality video and audio. The tool supports CUDA, QSV, and CPU encoding modes, making it versatile for different hardware configurations.

## Features

- **Dolby Vision Metadata Extraction**: Extracts RPU (Reference Processing Unit) metadata from HEVC streams.
- **Video Re-encoding**: Re-encodes video streams using CUDA, QSV, or CPU with customizable quality settings.
- **Audio Transcoding**: Converts audio streams to AAC format with configurable bitrate and channel options.
- **Dolby Vision Metadata Injection**: Injects extracted metadata back into the re-encoded video stream.
- **Batch Processing**: Supports processing multiple video files in a folder.
- **User-Friendly GUI**: Built with `tkinter`, providing an intuitive interface for selecting input/output paths, quality settings, and encoding modes.
- **Temporary File Management**: Automatically creates and cleans up temporary files during processing.

## Supported Encoding Modes

- **CUDA**: Utilizes NVIDIA's hardware acceleration for faster encoding.
- **QSV**: Uses Intel's Quick Sync Video for efficient encoding on supported hardware.
- **CPU**: Relies on software-based encoding using `libx265`.

## Usage

1. **Select Input**: Choose a single video file or a folder containing multiple video files.
2. **Set Output Folder**: Specify the output folder (defaults to the input folder if not specified).
3. **Configure Settings**:
   - **Quality**: Set the video quality (16-40, where lower values mean higher quality).
   - **Audio Channels**: Choose to convert audio to 2.0 Stereo, 5.1 Surround, or 7.1 Surround.
   - **Audio Bitrate**: Select the audio bitrate (128k, 192k, 256k, 384k, 480k, 640k).
   - **Encoding Mode**: Choose between CUDA, QSV, or CPU encoding.
   - **Quality Preset**: Select the encoding quality preset (e.g., slow, medium, fast).
4. **Process**: Click "Process Video" to start the conversion. The progress bar will update in real-time.
5. **Abort**: Use the "Abort" button to stop the process if needed.

## Requirements

- Python 3.x
- `tkinter` (usually included with Python)
- External tools:
  - `dovi_tool.exe` (for Dolby Vision metadata extraction/injection)
  - `ffmpeg.exe` (for video/audio processing)
  - `mkvmerge.exe` (for remuxing)

## Installation

1. Clone the repository or download the script.
2. Ensure the required tools (`dovi_tool.exe`, `ffmpeg.exe`, `mkvmerge.exe`) are placed in the `tools` folder.
3. Install Python dependencies (if any):
   ```bash
   pip install -r requirements.txt
