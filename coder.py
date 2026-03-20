# youtube_storage.py
"""
YouTube File Storage System
Encodes binary data into video frames for cloud storage via YouTube
"""

import cv2
import numpy as np
import os
import math
import subprocess
import tempfile
import shutil
import sys
import re
import hashlib
import json
import argparse
from collections import Counter
from typing import Optional, Tuple, List, Dict, Any

class YouTubeEncoder:
    """Encodes binary files into video format suitable for YouTube upload"""
    
    def __init__(self, key: Optional[str] = None):
        self.width = 1920
        self.height = 1080
        self.fps = 6
        
        # Block dimensions
        self.block_height = 16
        self.block_width = 24
        self.spacing = 4
        
        # Encryption key
        self.key = key
        self.use_encryption = key is not None
        
        # Color palette for 4-bit encoding (16 colors)
        self.colors = {
            '0000': (255, 0, 0),      # Blue
            '0001': (0, 255, 0),      # Green
            '0010': (0, 0, 255),      # Red
            '0011': (255, 255, 0),    # Yellow
            '0100': (255, 0, 255),    # Magenta
            '0101': (0, 255, 255),    # Cyan
            '0110': (255, 128, 0),    # Orange
            '0111': (128, 0, 255),    # Purple
            '1000': (0, 128, 128),    # Teal
            '1001': (128, 128, 0),    # Olive
            '1010': (128, 0, 128),    # Dark magenta
            '1011': (0, 128, 0),      # Dark green
            '1100': (128, 0, 0),      # Maroon
            '1101': (0, 0, 128),      # Navy
            '1110': (192, 192, 192),  # Light gray
            '1111': (255, 255, 255)   # White
        }
        
        # Corner markers for frame alignment
        self.marker_size = 80
        
        # Calculate grid dimensions
        self.blocks_x = (self.width - 2 * self.marker_size) // (self.block_width + self.spacing)
        self.blocks_y = (self.height - 2 * self.marker_size) // (self.block_height + self.spacing)
        self.blocks_per_region = self.blocks_x * self.blocks_y
        self.blocks_per_frame = self.blocks_per_region * 3
        
        # End of file marker
        self.eof_marker = "█" * 64
        self.eof_bytes = self.eof_marker.encode('utf-8')
        
        print(f"YouTube Encoder initialized")
        print(f"  Grid: {self.blocks_x}x{self.blocks_y} blocks per region")
        print(f"  FPS: {self.fps}")
        print(f"  Encryption: {'Enabled' if self.use_encryption else 'Disabled'}")
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """XOR encryption with provided key"""
        if not self.use_encryption:
            return data
        
        key_bytes = self.key.encode()
        result = bytearray()
        
        for i, byte in enumerate(data):
            key_byte = key_bytes[i % len(key_bytes)]
            result.append(byte ^ key_byte)
        
        return bytes(result)
    
    def _draw_markers(self, frame: np.ndarray) -> np.ndarray:
        """Draw corner markers for frame alignment during decoding"""
        # White squares
        cv2.rectangle(frame, (0, 0), (self.marker_size, self.marker_size), (255, 255, 255), -1)
        cv2.rectangle(frame, (self.width - self.marker_size, 0), 
                     (self.width, self.marker_size), (255, 255, 255), -1)
        cv2.rectangle(frame, (0, self.height - self.marker_size), 
                     (self.marker_size, self.height), (255, 255, 255), -1)
        cv2.rectangle(frame, (self.width - self.marker_size, self.height - self.marker_size), 
                     (self.width, self.height), (255, 255, 255), -1)
        
        # Borders
        cv2.rectangle(frame, (0, 0), (self.marker_size, self.marker_size), (0, 0, 0), 2)
        cv2.rectangle(frame, (self.width - self.marker_size, 0), 
                     (self.width, self.marker_size), (0, 0, 0), 2)
        cv2.rectangle(frame, (0, self.height - self.marker_size), 
                     (self.marker_size, self.height), (0, 0, 0), 2)
        cv2.rectangle(frame, (self.width - self.marker_size, self.height - self.marker_size), 
                     (self.width, self.height), (0, 0, 0), 2)
        
        return frame
    
    def _draw_block(self, frame: np.ndarray, x: int, y: int, color: Tuple[int, int, int]) -> bool:
        """Draw a single data block at specified grid position"""
        x1 = self.marker_size + x * (self.block_width + self.spacing)
        y1 = self.marker_size + y * (self.block_height + self.spacing)
        x2 = x1 + self.block_width
        y2 = y1 + self.block_height
        
        if x2 > self.width - self.marker_size or y2 > self.height - self.marker_size:
            return False
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 1)
        return True
    
    def _bits_to_color(self, bits: str) -> Tuple[int, int, int]:
        """Convert 4-bit binary string to RGB color"""
        while len(bits) < 4:
            bits = '0' + bits
        return self.colors.get(bits, (255, 0, 0))
    
    def _data_to_blocks(self, data: bytes) -> List[str]:
        """Convert bytes to 4-bit blocks"""
        all_bits = []
        for byte in data:
            for i in range(7, -1, -1):
                all_bits.append(str((byte >> i) & 1))
        
        # Pad to multiple of 4
        while len(all_bits) % 4 != 0:
            all_bits.append('0')
        
        blocks = [''.join(all_bits[i:i+4]) for i in range(0, len(all_bits), 4)]
        return blocks
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum for integrity verification"""
        return hashlib.sha256(data).hexdigest()
    
    def encode(self, input_file: str, output_file: str) -> bool:
        """Encode file into video with encryption and integrity checks"""
        
        print(f"\nEncoding file: {input_file}")
        
        # Read input file
        with open(input_file, 'rb') as f:
            original_data = f.read()
        
        print(f"  Original size: {len(original_data)} bytes")
        
        # Calculate checksum
        checksum = self._calculate_checksum(original_data)
        print(f"  SHA-256 checksum: {checksum[:16]}...")
        
        # Encrypt if needed
        if self.use_encryption:
            data = self._encrypt_data(original_data)
            print(f"  Encryption applied")
        else:
            data = original_data
        
        # Create metadata header
        metadata = {
            'filename': os.path.basename(input_file),
            'size': len(original_data),
            'checksum': checksum,
            'encrypted': self.use_encryption
        }
        
        header = f"FILE:{json.dumps(metadata)}|"
        header_bytes = header.encode('latin-1')
        
        print(f"  Metadata: {metadata['filename']} ({metadata['size']} bytes)")
        
        # Convert to blocks
        header_blocks = self._data_to_blocks(header_bytes)
        data_blocks = self._data_to_blocks(data)
        eof_blocks = self._data_to_blocks(self.eof_bytes)
        all_blocks = header_blocks + data_blocks + eof_blocks
        
        print(f"  Total blocks: {len(all_blocks)}")
        
        # Calculate frames needed
        frames_needed = math.ceil(len(all_blocks) / self.blocks_per_region)
        frames_needed += 5  # Guard frames
        print(f"  Required frames: {frames_needed}")
        print(f"  Video duration: {frames_needed / self.fps:.1f} seconds")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Generate frames
            for frame_num in range(frames_needed - 5):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                frame = self._draw_markers(frame)
                
                start_idx = frame_num * self.blocks_per_region
                end_idx = min(start_idx + self.blocks_per_region, len(all_blocks))
                frame_blocks = all_blocks[start_idx:end_idx]
                
                # Primary region
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x
                    x = idx % self.blocks_x
                    if y < self.blocks_y:
                        color = self._bits_to_color(bits)
                        self._draw_block(frame, x, y, color)
                
                # Redundancy region 1
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x
                    x = idx % self.blocks_x + self.blocks_x
                    if x < self.blocks_x * 2 and y < self.blocks_y:
                        color = self._bits_to_color(bits)
                        self._draw_block(frame, x, y, color)
                
                # Redundancy region 2
                for idx, bits in enumerate(frame_blocks):
                    y = idx // self.blocks_x + self.blocks_y
                    x = idx % self.blocks_x
                    if x < self.blocks_x and y < self.blocks_y * 2:
                        color = self._bits_to_color(bits)
                        self._draw_block(frame, x, y, color)
                
                frame_file = os.path.join(temp_dir, f"frame_{frame_num:05d}.png")
                cv2.imwrite(frame_file, frame)
            
            # Generate guard frames (solid blue)
            for i in range(5):
                frame_num = frames_needed - 5 + i
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                frame = self._draw_markers(frame)
                for y in range(self.blocks_y * 2):
                    for x in range(self.blocks_x * 2):
                        self._draw_block(frame, x, y, (255, 0, 0))
                frame_file = os.path.join(temp_dir, f"frame_{frame_num:05d}.png")
                cv2.imwrite(frame_file, frame)
            
            # Convert to MP4
            print("  Converting to MP4...")
            
            try:
                # Try using ffmpeg first
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                
                cmd = [
                    'ffmpeg',
                    '-framerate', str(self.fps),
                    '-i', os.path.join(temp_dir, 'frame_%05d.png'),
                    '-c:v', 'libx264',
                    '-preset', 'slow',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-an',
                    '-movflags', '+faststart',
                    '-y',
                    output_file
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to OpenCV
                print("  FFmpeg not available, using OpenCV fallback")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_file, fourcc, self.fps, (self.width, self.height))
                
                for frame_num in range(frames_needed):
                    frame_file = os.path.join(temp_dir, f"frame_{frame_num:05d}.png")
                    frame = cv2.imread(frame_file)
                    if frame is not None:
                        out.write(frame)
                out.release()
            
            print(f"  Video saved: {output_file}")
            print(f"  File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
            return True
            
        finally:
            # Clean up temporary files
            shutil.rmtree(temp_dir)


class YouTubeDecoder:
    """Decodes video back to original file with integrity verification"""
    
    def __init__(self, key: Optional[str] = None):
        self.width = 1920
        self.height = 1080
        self.block_height = 16
        self.block_width = 24
        self.spacing = 4
        self.marker_size = 80
        
        self.key = key
        
        # Color mapping
        self.colors = {
            '0000': (255, 0, 0),
            '0001': (0, 255, 0),
            '0010': (0, 0, 255),
            '0011': (255, 255, 0),
            '0100': (255, 0, 255),
            '0101': (0, 255, 255),
            '0110': (255, 128, 0),
            '0111': (128, 0, 255),
            '1000': (0, 128, 128),
            '1001': (128, 128, 0),
            '1010': (128, 0, 128),
            '1011': (0, 128, 0),
            '1100': (128, 0, 0),
            '1101': (0, 0, 128),
            '1110': (192, 192, 192),
            '1111': (255, 255, 255)
        }
        
        # Optimization structures
        self.color_values = np.array(list(self.colors.values()), dtype=np.int32)
        self.color_keys = list(self.colors.keys())
        self.color_cache = {}
        
        # Grid calculation
        self.blocks_x = (self.width - 2 * self.marker_size) // (self.block_width + self.spacing)
        self.blocks_y = (self.height - 2 * self.marker_size) // (self.block_height + self.spacing)
        self.blocks_per_region = self.blocks_x * self.blocks_y
        
        # Precompute coordinates for faster decoding
        self._precompute_coordinates()
        
        print(f"YouTube Decoder initialized")
        print(f"  Grid: {self.blocks_x}x{self.blocks_y} blocks")
        print(f"  Encryption key: {'Present' if self.key else 'Not set'}")
    
    def _precompute_coordinates(self):
        """Precompute block center coordinates for faster access"""
        self.block_coords = []
        for idx in range(self.blocks_per_region):
            y = idx // self.blocks_x
            x = idx % self.blocks_x
            if y < self.blocks_y:
                cx = self.marker_size + x * (self.block_width + self.spacing) + self.block_width // 2
                cy = self.marker_size + y * (self.block_height + self.spacing) + self.block_height // 2
                self.block_coords.append((cx, cy))
    
    def _decrypt_data(self, data: bytes) -> bytes:
        """XOR decryption with provided key"""
        if not self.key:
            return data
        
        key_bytes = self.key.encode()
        result = bytearray()
        
        for i, byte in enumerate(data):
            key_byte = key_bytes[i % len(key_bytes)]
            result.append(byte ^ key_byte)
        
        return bytes(result)
    
    def _color_to_bits(self, color: Tuple[int, int, int]) -> str:
        """Convert RGB color to 4-bit binary string with caching"""
        color_key = (color[0], color[1], color[2])
        
        if color_key in self.color_cache:
            return self.color_cache[color_key]
        
        # Quick check for blue background (guard frames)
        if color[0] > 200 and color[1] < 50 and color[2] < 50:
            self.color_cache[color_key] = '0000'
            return '0000'
        
        # Find closest color using Euclidean distance
        color_arr = np.array([color[0], color[1], color[2]], dtype=np.int32)
        distances = np.sum((self.color_values - color_arr) ** 2, axis=1)
        best_idx = np.argmin(distances)
        result = self.color_keys[best_idx]
        
        self.color_cache[color_key] = result
        return result
    
    def decode_frame(self, frame: np.ndarray) -> List[str]:
        """Decode a single frame into 4-bit blocks"""
        # Resize to target dimensions if needed
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height), 
                              interpolation=cv2.INTER_NEAREST)
        
        blocks = []
        h, w = frame.shape[:2]
        
        for cx, cy in self.block_coords:
            if cx < w and cy < h:
                color = frame[cy, cx]
                bits = self._color_to_bits(color)
                blocks.append(bits)
            else:
                blocks.append('0000')
        
        return blocks
    
    def _blocks_to_bytes(self, blocks: List[str]) -> bytes:
        """Convert 4-bit blocks to bytes"""
        all_bits = ''.join(blocks)
        bytes_data = bytearray()
        
        for i in range(0, len(all_bits) - 7, 8):
            byte_str = all_bits[i:i+8]
            if len(byte_str) == 8:
                try:
                    byte = int(byte_str, 2)
                    bytes_data.append(byte)
                except ValueError:
                    bytes_data.append(0)
        
        return bytes(bytes_data)
    
    def _find_eof_marker(self, data: bytes) -> int:
        """Find end-of-file marker position"""
        eof_bytes = b'\xe2\x96\x88' * 64  # UTF-8 encoding of '█'
        
        for i in range(len(data) - len(eof_bytes)):
            if data[i:i+len(eof_bytes)] == eof_bytes:
                return i
        return -1
    
    def _verify_checksum(self, data: bytes, expected_checksum: str) -> bool:
        """Verify data integrity using SHA-256"""
        actual_checksum = hashlib.sha256(data).hexdigest()
        return actual_checksum == expected_checksum
    
    def decode(self, video_file: str, output_dir: str = '.') -> bool:
        """Decode video file and restore original data with integrity verification"""
        
        print(f"\nDecoding video: {video_file}")
        
        if not os.path.exists(video_file):
            print(f"Error: File not found - {video_file}")
            return False
        
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            print("Error: Cannot open video file")
            return False
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"  Total frames: {total_frames}")
        print(f"  FPS: {fps:.2f}")
        
        # Collect all blocks from video
        all_blocks = []
        frames_processed = 0
        
        for frame_num in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            frames_processed += 1
            
            if frame_num % 100 == 0:
                print(f"  Processing: {frame_num}/{total_frames} frames")
            
            frame_blocks = self.decode_frame(frame)
            all_blocks.extend(frame_blocks)
        
        cap.release()
        
        print(f"  Processed {frames_processed} frames")
        print(f"  Total blocks collected: {len(all_blocks)}")
        
        # Convert blocks to bytes
        bytes_data = self._blocks_to_bytes(all_blocks)
        print(f"  Raw data size: {len(bytes_data)} bytes")
        
        # Find EOF marker
        eof_pos = self._find_eof_marker(bytes_data)
        if eof_pos > 0:
            bytes_data = bytes_data[:eof_pos]
            print(f"  EOF marker found at position {eof_pos}")
        else:
            print("  Warning: EOF marker not found")
        
        # Extract and parse metadata
        data_str = bytes_data[:5000].decode('latin-1', errors='ignore')
        header_pattern = r'FILE:(\{.*?\})\|'
        match = re.search(header_pattern, data_str)
        
        if not match:
            print("Error: Metadata header not found")
            # Save raw data as fallback
            fallback_path = os.path.join(output_dir, "decoded_data.bin")
            with open(fallback_path, 'wb') as f:
                f.write(bytes_data)
            print(f"  Raw data saved to: {fallback_path}")
            return False
        
        try:
            metadata = json.loads(match.group(1))
            filename = metadata['filename']
            original_size = metadata['size']
            expected_checksum = metadata['checksum']
            encrypted = metadata.get('encrypted', False)
            
            print(f"\nMetadata extracted:")
            print(f"  Filename: {filename}")
            print(f"  Size: {original_size} bytes")
            print(f"  Checksum: {expected_checksum[:16]}...")
            print(f"  Encrypted: {encrypted}")
            
            # Extract data section
            header_str = match.group(0)
            header_bytes = header_str.encode('latin-1')
            header_pos = bytes_data.find(header_bytes)
            
            if header_pos < 0:
                print("Error: Cannot locate data section")
                return False
            
            encrypted_data = bytes_data[header_pos + len(header_bytes):
                                        header_pos + len(header_bytes) + original_size]
            
            # Decrypt if necessary
            if encrypted:
                if not self.key:
                    print("Error: File is encrypted but no key provided")
                    return False
                file_data = self._decrypt_data(encrypted_data)
                print("  Decryption applied")
            else:
                file_data = encrypted_data
            
            # Verify integrity
            if self._verify_checksum(file_data, expected_checksum):
                print("  Integrity check: PASSED")
            else:
                print("  Integrity check: FAILED - File may be corrupted")
                # Optionally save anyway
                response = input("  Save anyway? (y/N): ")
                if response.lower() != 'y':
                    return False
            
            # Save file
            output_path = os.path.join(output_dir, filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(output_path):
                output_path = os.path.join(output_dir, f"{base}_{counter}{ext}")
                counter += 1
            
            with open(output_path, 'wb') as f:
                f.write(file_data)
            
            print(f"\nFile restored successfully:")
            print(f"  Path: {output_path}")
            print(f"  Size: {len(file_data)} bytes")
            print(f"  Integrity: {'Verified' if self._verify_checksum(file_data, expected_checksum) else 'Not verified'}")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse metadata - {e}")
            return False
        except Exception as e:
            print(f"Error during decoding: {e}")
            return False


def read_key_from_file(key_file: str = 'key.txt') -> Optional[str]:
    """Read encryption key from file"""
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    print(f"Encryption key loaded from {key_file}")
                    return key
                else:
                    print(f"Warning: {key_file} is empty")
        else:
            print(f"Info: {key_file} not found, encryption disabled")
    except Exception as e:
        print(f"Warning: Failed to read key file - {e}")
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='YouTube File Storage System - Encode files into video for cloud storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s encode document.pdf output.mp4
  %(prog)s decode video.mp4 restored_files/
  %(prog)s --key mysecretkey encode sensitive.zip secure_video.mp4
        """
    )
    
    parser.add_argument('command', choices=['encode', 'decode'],
                       help='Operation to perform')
    parser.add_argument('input', help='Input file (for encode) or video (for decode)')
    parser.add_argument('output', nargs='?', default=None,
                       help='Output file or directory')
    parser.add_argument('--key', default=None,
                       help='Encryption key (overrides key.txt)')
    parser.add_argument('--no-key', action='store_true',
                       help='Disable encryption even if key.txt exists')
    
    args = parser.parse_args()
    
    # Determine encryption key
    if args.no_key:
        key = None
        print("Encryption explicitly disabled")
    elif args.key:
        key = args.key
        print(f"Using provided encryption key")
    else:
        key = read_key_from_file()
    
    if args.command == 'encode':
        encoder = YouTubeEncoder(key)
        output_file = args.output if args.output else 'output.mp4'
        encoder.encode(args.input, output_file)
    
    elif args.command == 'decode':
        decoder = YouTubeDecoder(key)
        output_dir = args.output if args.output else '.'
        decoder.decode(args.input, output_dir)


if __name__ == "__main__":
    main()
