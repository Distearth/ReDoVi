# ReDoVi - Dolby Vision Video Processing Tool

ReDoVi is a Windows-based GUI application designed to process Dolby Vision (DoVi) HDR video files. It will extract, re-encode (Based on quality choice), and remux Dolby Vision metadata while maintaining high-quality video and audio. The tool supports CUDA, QSV, and CPU encoding modes, making it versatile for different hardware configurations. Should convert to Profile 8 if it is not.

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

### Standalone Executable (No Python Installation Required)

ReDoVi is distributed as a standalone Windows executable (`.exe`) that includes Python, all required tools, and dependencies. You can run the `.exe` file from anywhere on your computer without needing to install Python or additional software.

1. **Download the Executable**: Obtain the `ReDoVi.exe` file from the releases section.
2. **Run the Executable**: Double-click the `ReDoVi.exe` file to launch the application.
3. **Select Input**: Choose a single video file or a folder containing multiple video files.
4. **Set Output Folder**: Specify the output folder (defaults to the input folder if not specified).
5. **Configure Settings**:
   - **Quality**: Set the video quality (16-40, where lower values mean higher quality).
   - **Audio Channels**: Choose to convert audio to 2.0 Stereo, 5.1 Surround, or 7.1 Surround.
   - **Audio Bitrate**: Select the audio bitrate (128k, 192k, 256k, 384k, 480k, 640k).
   - **Encoding Mode**: Choose between CUDA, QSV, or CPU encoding.
   - **Quality Preset**: Select the encoding quality preset (e.g., slow, medium, fast).
6. **Process**: Click "Process Video" to start the conversion. The progress bar will update in real-time.
7. **Abort**: Use the "Abort" button to stop the process if needed.

## Requirements

- **Windows OS**: The executable is designed for Windows systems.
- **Hardware Acceleration** (Optional):
  - **CUDA**: Requires an NVIDIA GPU with CUDA support.
  - **QSV**: Requires an Intel CPU with Quick Sync Video support.

## Included Tools

The `.exe` file contains all necessary tools bundled within it:
- `dovi_tool.exe` (for Dolby Vision metadata extraction/injection)
- `ffmpeg.exe` (for video/audio processing)
- `mkvmerge.exe` (for remuxing)

No additional downloads or installations are required.

## Configuration

Settings are saved in `config.json` and include:
- Quality
- Audio Channels
- Encoding Mode
- Audio Bitrate
- Keep Original Audio
- Encoding Quality Preset

## Support

If you find this tool useful, consider supporting the developer:
[Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=A38KG42PKBBBY)

## Credits

Special thanks to [quietvoid](https://github.com/quietvoid/dovi_tool) for the `dovi_tool` used in this project.

## Notes

- A temporary folder is created in the output directory during processing. It will be deleted automatically after the process completes.
- The tool creates intermediate files during processing, so ensure sufficient disk space is available.

## License

This project is open-source and available under the MIT License. Feel free to modify and distribute it as needed.
