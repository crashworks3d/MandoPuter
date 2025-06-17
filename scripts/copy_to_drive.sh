#!/bin/bash

# Script to copy ESP32-S2-LolinBeskar contents to a specified drive
# Usage: ./copy_to_drive.sh [DRIVE_NAME]
# Default drive name: S2MINIBOOT

# Set default drive name - Use CIRCUITPY for CircuitPython mode, not S2MINIBOOT (bootloader mode)
DEFAULT_DRIVE="CIRCUITPY"
DRIVE_NAME="${1:-$DEFAULT_DRIVE}"

# Source directory (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$PROJECT_ROOT/Releases/ESP32-S3Beskar"

# Determine the mount point based on the operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    MOUNT_POINT="/Volumes/$DRIVE_NAME"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    MOUNT_POINT="/media/$USER/$DRIVE_NAME"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash/Cygwin)
    MOUNT_POINT="/mnt/$DRIVE_NAME"
else
    echo "Error: Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "ESP32-S2-LolinBeskar Drive Copy Script"
echo "======================================"
echo "Source directory: $SOURCE_DIR"
echo "Target drive: $DRIVE_NAME"
echo "Mount point: $MOUNT_POINT"
echo ""

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory '$SOURCE_DIR' does not exist!"
    echo "Please ensure the ESP32-S2-LolinBeskar folder is present in the Releases directory."
    exit 1
fi

# Check if the drive is mounted
if [ ! -d "$MOUNT_POINT" ]; then
    echo "Error: Drive '$DRIVE_NAME' is not mounted or not found at '$MOUNT_POINT'"
    echo ""
    echo "Please ensure:"
    echo "1. The drive is properly connected"
    echo "2. The drive is formatted and accessible"
    echo "3. The drive name matches '$DRIVE_NAME'"
    echo ""
    echo "Available drives/volumes:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        ls -la /Volumes/ 2>/dev/null || echo "No volumes found"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ls -la /media/$USER/ 2>/dev/null || echo "No media found"
    fi
    exit 1
fi

# Check if the mount point is writable
if [ ! -w "$MOUNT_POINT" ]; then
    echo "Error: Drive '$DRIVE_NAME' is not writable!"
    echo "Please check drive permissions or if the drive is write-protected."
    exit 1
fi

# Display source directory contents
echo "Source directory contents:"
ls -la "$SOURCE_DIR"
echo ""

# Calculate total size of source directory
SOURCE_SIZE=$(du -sh "$SOURCE_DIR" 2>/dev/null | cut -f1)
echo "Total size to copy: $SOURCE_SIZE"

# Check available space on target drive
if command -v df >/dev/null 2>&1; then
    AVAILABLE_SPACE=$(df -h "$MOUNT_POINT" | awk 'NR==2 {print $4}')
    echo "Available space on drive: $AVAILABLE_SPACE"
fi

echo ""
read -p "Do you want to proceed with copying? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Copy operation cancelled."
    exit 0
fi

echo ""
echo "Starting operation..."
echo "Source: $SOURCE_DIR"
echo "Target: $MOUNT_POINT"
echo ""

# Identify files and folders to preserve
echo "Identifying files and folders to preserve..."
PRESERVE_FILES=()

# Check for sd folder
if [ -d "$MOUNT_POINT/sd" ]; then
    echo "Found sd folder - will preserve"
    PRESERVE_FILES+=("$MOUNT_POINT/sd")
fi

# Create a temporary directory for preserved files
PRESERVE_DIR=$(mktemp -d)
echo "Created temporary directory for preserved files: $PRESERVE_DIR"

# Copy preserved files to temporary directory
for file in "${PRESERVE_FILES[@]}"; do
    if [ -e "$file" ]; then
        rel_path=${file#$MOUNT_POINT/}
        target_path="$PRESERVE_DIR/$rel_path"
        target_dir=$(dirname "$target_path")
        
        # Create target directory if it doesn't exist
        mkdir -p "$target_dir"
        
        echo "Preserving: $rel_path"
        if [ -d "$file" ]; then
            cp -R "$file" "$target_dir/"
        else
            cp "$file" "$target_path"
        fi
    fi
done

# Clean the drive (remove everything)
echo "Cleaning target drive..."
# Use find to delete all files and directories, but skip the mount point itself
find "$MOUNT_POINT" -mindepth 1 -delete 2>/dev/null
echo "Target drive cleaned."

# Restore preserved files
echo "Restoring preserved files..."
if [ ${#PRESERVE_FILES[@]} -gt 0 ]; then
    cp -R "$PRESERVE_DIR/"* "$MOUNT_POINT/" 2>/dev/null
    echo "Preserved files restored."
fi

# Clean up temporary directory
rm -rf "$PRESERVE_DIR"

# Perform the copy operation with progress
echo "Copying new files..."
if command -v rsync >/dev/null 2>&1; then
    # Use rsync if available (shows progress)
    echo "Using rsync for copy operation..."
    echo "Excluding docs/ directory and hidden files..."
    # Don't exclude sd/ anymore since we've already preserved it if it existed
    # Add --exclude=".*" to exclude hidden files and directories
    rsync -av --progress --exclude="docs/" --exclude=".*" "$SOURCE_DIR/" "$MOUNT_POINT/"
    COPY_EXIT_CODE=$?
else
    # Fallback to cp
    echo "Using cp for copy operation..."
    echo "Excluding docs/ directory and hidden files..."
    # Create a temporary directory for the operation
    TMP_DIR=$(mktemp -d)
    
    # Copy only non-hidden files and directories to the temp directory
    # First, copy all regular files that don't start with a dot
    find "$SOURCE_DIR" -type f -not -path "*/\.*" -not -path "*/docs/*" -exec cp --parents {} "$TMP_DIR/" \;
    
    # Then, copy all directories that don't start with a dot
    find "$SOURCE_DIR" -type d -not -path "*/\.*" -not -path "*/docs/*" -not -path "$SOURCE_DIR/docs" | while read dir; do
        if [ "$dir" != "$SOURCE_DIR" ]; then
            rel_dir=${dir#$SOURCE_DIR/}
            mkdir -p "$TMP_DIR/$rel_dir"
        fi
    done
    
    # Copy from temp to destination
    cp -R "$TMP_DIR/"* "$MOUNT_POINT/" 2>/dev/null
    COPY_EXIT_CODE=$?
    
    # Clean up
    rm -rf "$TMP_DIR"
fi

# Check if copy was successful
if [ $COPY_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Copy operation completed successfully!"
    echo ""
    echo "Files copied to: $MOUNT_POINT"
    echo "Drive contents:"
    ls -la "$MOUNT_POINT"
    
    # Sync to ensure all data is written
    echo ""
    echo "Syncing data to drive..."
    sync
    echo "✅ Sync completed."
    
    # Run dot_clean on macOS to remove extraneous files/folders
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Running dot_clean on macOS to remove extraneous files..."
        dot_clean "$MOUNT_POINT"
        echo "✅ dot_clean completed."
    fi
    
    echo "It's now safe to eject the drive."
else
    echo ""
    echo "❌ Copy operation failed with exit code: $COPY_EXIT_CODE"
    echo "Please check the error messages above and try again."
    exit 1
fi

echo ""
echo "Script completed successfully!"