#!/usr/bin/env python3
"""
Convert MP4 video file to GIF format.
Uses ffmpeg for efficient conversion with quality control options.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def convert_mp4_to_gif(input_mp4: str, output_gif: str = None, fps: int = 30, 
                       scale: int = None):
    """
    Convert MP4 video file to GIF using ffmpeg.
    
    Args:
        input_mp4: Input MP4 file path
        output_gif: Output GIF file path (default: same as input with .gif extension)
        fps: Frame rate for output GIF (default: 30)
        scale: Maximum width in pixels (maintains aspect ratio, default: None = original size)
    """
    input_path = Path(input_mp4)
    
    # Validate input file
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_mp4}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.mp4':
        print(f"Warning: Input file does not have .mp4 extension: {input_mp4}")
    
    # Determine output path
    if output_gif is None:
        output_path = input_path.with_suffix('.gif')
    else:
        output_path = Path(output_gif)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Converting {input_path} to {output_path}")
    print(f"Settings: fps={fps}, scale={scale or 'original'}")
    
    # Build ffmpeg command
    # Using two-pass approach for better quality and file size
    # First pass: generate palette from video
    # Second pass: use palette to create optimized GIF
    
    temp_palette = output_path.parent / f"{output_path.stem}_palette.png"
    
    try:
        # Step 1: Generate palette
        print("Step 1: Generating color palette...")
        if scale is None:
            palette_filter = f'fps={fps},palettegen=max_colors=256:reserve_transparent=0'
        else:
            palette_filter = f'fps={fps},scale={scale}:-1:flags=lanczos,palettegen=max_colors=256:reserve_transparent=0'
        
        palette_cmd = [
            'ffmpeg', '-y',  # Overwrite output
            '-i', str(input_path),
            '-vf', palette_filter,
            str(temp_palette)
        ]
        
        subprocess.run(palette_cmd, check=True, capture_output=True)
        
        # Step 2: Create GIF using palette
        print("Step 2: Creating GIF with palette...")
        if scale is None:
            gif_filter = f'fps={fps}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle'
        else:
            gif_filter = f'fps={fps},scale={scale}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle'
        
        gif_cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-i', str(temp_palette),
            '-lavfi', gif_filter,
            str(output_path)
        ]
        
        subprocess.run(gif_cmd, check=True, capture_output=True)
        
        # Clean up temporary palette file
        if temp_palette.exists():
            temp_palette.unlink()
        
        print(f"\nSuccess! GIF saved to: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: ffmpeg conversion failed")
        if e.stderr:
            print(f"Error message: {e.stderr.decode()}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Or download from https://ffmpeg.org/")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert MP4 video file to GIF format",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input_mp4', type=str, 
                       help='Input MP4 file path')
    parser.add_argument('output_gif', type=str, nargs='?', default=None,
                       help='Output GIF file path (default: same as input with .gif extension)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Frame rate for output GIF (default: 30)')
    parser.add_argument('--scale', type=int, default=None,
                       help='Maximum width in pixels, maintains aspect ratio (default: original size)')
    
    args = parser.parse_args()
    
    convert_mp4_to_gif(
        input_mp4=args.input_mp4,
        output_gif=args.output_gif,
        fps=args.fps,
        scale=args.scale
    )


if __name__ == "__main__":
    main()

