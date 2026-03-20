# YouTube File Storage System

A system for encoding binary files into video format suitable for storage on YouTube, with encryption and integrity verification.

## Features

- Data encoding: Converts any binary file into a video format
- Encryption: XOR-based encryption with custom keys
- Integrity verification: SHA-256 checksums for data validation
- Error resilience: Triple redundancy with multiple block regions
- Automatic scaling: Handles videos of any resolution
- Metadata preservation: Stores filename, size, and checksum information

## Requirements

System dependencies:
- Python 3.8 or higher
- FFmpeg (recommended for better video encoding)

Python packages:
```
pip install opencv-python numpy
```

## Installation

1. Download the script:
```bash
git clone https://github.com/yourusername/youtube-storage.git
cd youtube-storage
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Optional - Install FFmpeg:
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Download from ffmpeg.org

## Usage

### Basic encoding
```bash
python youtube_storage.py encode document.pdf output.mp4
```

### Basic decoding
```bash
python youtube_storage.py decode video.mp4 restored_files/
```

### With encryption
Create a key.txt file:
```bash
echo "mysecretkey" > key.txt
python youtube_storage.py encode confidential.zip secure_video.mp4
```

Or specify key directly:
```bash
python youtube_storage.py --key "mysecretkey" encode data.bin output.mp4
```

### Disable encryption
```bash
python youtube_storage.py --no-key encode public.pdf video.mp4
```

## Technical Specifications

Video format:
- Resolution: 1920x1080 (1080p)
- Frame rate: 6 FPS
- Codec: H.264 (libx264) or MP4v fallback
- Color depth: 16 colors (4-bit encoding)

Data capacity:
- Blocks per frame: ~9,600 (3 redundant regions)
- Raw capacity: ~4,800 bytes per frame
- Effective capacity: ~1,600 bytes per frame after redundancy

Security:
- Encryption: XOR cipher with variable-length key
- Key storage: Plain text file (user managed)
- Integrity: SHA-256 checksum verification

Limitations:
- Maximum file size: Limited by video duration (YouTube's 12-hour limit)
- Encoding time: ~30 seconds per MB on modern hardware
- Decoding speed: ~10 MB per minute
- Quality loss: Minimal with H.264 encoding at CRF 23

## How It Works

### Encoding process
1. File is read and SHA-256 checksum is calculated
2. Data is optionally encrypted with XOR cipher
3. Metadata (filename, size, checksum, encryption flag) is prepended
4. Data is converted to 4-bit binary blocks
5. Blocks are drawn as colored squares in video frames
6. Each block appears in 3 regions per frame for redundancy
7. Guard frames are added for synchronization
8. Frames are compiled into an MP4 video

### Decoding process
1. Video is read frame by frame
2. Corner markers ensure proper frame alignment
3. Colors are mapped back to 4-bit binary values
4. Blocks are reassembled into bytes
5. Metadata header is extracted and parsed
6. Data is decrypted if encryption was used
7. SHA-256 checksum validates data integrity
8. Original file is restored

## Performance Considerations

- Encoding speed: 1-2 MB per minute (CPU dependent)
- Decoding speed: 5-10 MB per minute (GPU accelerated if available)
- Storage efficiency: 0.5 MB per second of video (1080p, 6 FPS)
- Error recovery: Redundant blocks allow recovery of up to 33% data loss

## Security Notes

- Encryption keys are not embedded in the video
- YouTube may re-encode videos, potentially causing data loss
- Recommended to use error correction for critical data
- Keep encryption keys separate from uploaded videos
- XOR encryption is lightweight but not military-grade; use for obfuscation only

## Error Handling

The system includes several error recovery mechanisms:

1. Triple redundancy: Each block appears in three separate regions
2. Checksum verification: SHA-256 ensures data integrity
3. Guard frames: Help detect video start and end
4. Corner markers: Ensure proper frame alignment even after scaling
5. EOF marker: Clearly marks the end of valid data

## Troubleshooting

FFmpeg not found:
The system falls back to OpenCV encoding, but quality may be lower. Install FFmpeg for best results.

Decoding fails:
- Ensure video hasn't been re-encoded by YouTube
- Check that the video resolution wasn't changed
- Verify encryption key matches the one used for encoding
- Try with the --no-key flag if the file wasn't encrypted

Checksum mismatch:
- Video may have been corrupted during upload/download
- Try re-downloading from YouTube
- Partial data may still be recoverable

Memory issues:
- Large files require significant memory during encoding/decoding
- Consider splitting files into smaller chunks
- The system processes videos sequentially, not loading all frames at once

## Limitations and Warnings

- Not for production use: This is a proof-of-concept with experimental error handling
- YouTube TOS: Uploading encoded data may violate YouTube's terms of service
- Quality loss: YouTube's re-encoding may corrupt data
- Speed: Not optimized for large files
- Recovery: No forward error correction beyond redundancy

## Disclaimer

This software is provided for educational and research purposes only. Users are solely responsible for ensuring compliance with YouTube's Terms of Service and all applicable laws and regulations regarding data storage and encryption. The authors assume no liability for any misuse or damages arising from the use of this software.
