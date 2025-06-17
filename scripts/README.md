# Scripts Directory

This directory contains utility scripts for the MandoPuter project.

## copy_to_drive.sh

A bash script that copies all contents of the `ESP32-S3Beskar` folder to a specified drive.

### Usage

```bash
# Copy to default drive (CIRCUITPY)
./scripts/copy_to_drive.sh

# Copy to a custom drive name
./scripts/copy_to_drive.sh MYDRIVE
```

### Features

- **Cross-platform support**: Works on macOS, Linux, and Windows (Git Bash/Cygwin)
- **Error handling**: Checks for drive availability, source directory existence, and write permissions
- **Progress display**: Shows copy progress when rsync is available
- **Safety checks**: Displays source contents and asks for confirmation before copying
- **Space verification**: Shows available space on target drive
- **Sync operation**: Ensures all data is written to drive before completion

### Parameters

- `DRIVE_NAME` (optional): Name of the target drive. Defaults to `CIRCUITPY` if not specified.

### Error Handling

The script handles the following error conditions:

1. **Source directory not found**: Checks if the ESP32-S2-LolinBeskar folder exists
2. **Drive not mounted**: Verifies the target drive is connected and accessible
3. **Write permissions**: Ensures the drive is writable
4. **Unsupported OS**: Provides appropriate error message for unsupported operating systems

### Examples

```bash
# Basic usage with default drive name
cd /path/to/MandoPuter
./scripts/copy_to_drive.sh

# Specify custom drive name
./scripts/copy_to_drive.sh CIRCUITPY

# Make script executable (if needed)
chmod +x scripts/copy_to_drive.sh
```

### Requirements

- Bash shell
- Source directory: `Releases/ESP32-S3Beskar/`
- Target drive must be mounted and accessible
- Optional: `rsync` for progress display (falls back to `cp` if not available)