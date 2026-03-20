# Changelog

## [1.0.0] - 2026-03-20

### Added
- Initial release
- Video encoding with 6 FPS and 1920x1080 resolution
- XOR encryption support
- SHA-256 checksum verification
- Triple redundancy for error resilience
- Metadata preservation (filename, size, checksum)
- Corner markers for frame alignment
- EOF marker for data boundary detection
- Guard frames for synchronization
- FFmpeg integration with OpenCV fallback
- Command-line interface with argparse

### Technical details
- 16-color palette (4-bit encoding)
- 80px corner markers
- 16x24 pixel blocks with 4px spacing
- 3 redundant regions per frame
- 5 guard frames at video end

## [1.0.0] - Initial Release Features

### Encoding
- Convert any binary file to MP4 video
- Optional encryption with user-provided key
- Automatic scaling to 1080p
- Metadata embedding

### Decoding
- Extract data from MP4 videos
- Automatic resolution handling
- Integrity verification
- Encryption decryption support
- Original filename restoration

### Error Handling
- Checksum validation
- Partial data recovery
- Frame alignment correction
- Redundant block recovery

### Performance
- Optimized color lookup with caching
- Precomputed block coordinates
- NumPy vectorized operations
- Efficient frame processing
