#!/usr/bin/env python3
"""
Generate optimization video showing two stroke versions side by side.

Takes images from group_images folder:
- iter_XXXX_<left_strokes>s.png (left side)
- iter_XXXX_<right_strokes>s.png (right side)

Automatically detects available stroke numbers and animates through iterations.
"""

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Set
from PIL import Image, ImageDraw, ImageFont
import numpy as np


def detect_stroke_numbers(group_images_dir: str) -> List[int]:
    """
    Detect all available stroke numbers from filenames in group_images directory.
    
    Returns:
        Sorted list of stroke numbers (e.g., [16, 32] or [32, 64])
    """
    stroke_pattern = re.compile(r'iter_\d+_(\d+)s\.png')
    stroke_numbers: Set[int] = set()
    
    files = os.listdir(group_images_dir)
    for f in files:
        match = stroke_pattern.match(f)
        if match:
            stroke_numbers.add(int(match.group(1)))
    
    return sorted(stroke_numbers)


def find_iteration_pairs(group_images_dir: str, left_strokes: int, right_strokes: int) -> List[Tuple[int, str, str]]:
    """
    Find all iteration pairs for given stroke numbers in the group_images directory.
    
    Args:
        group_images_dir: Path to group_images directory
        left_strokes: Stroke number for left side (e.g., 16)
        right_strokes: Stroke number for right side (e.g., 32)
    
    Returns:
        List of tuples: (iteration_number, left_path, right_path)
    """
    pairs = []
    
    left_key = f"{left_strokes}s"
    right_key = f"{right_strokes}s"
    
    # Find all iteration files
    iter_pattern = re.compile(r'iter_(\d+)_(\d+s)\.png')
    
    files = os.listdir(group_images_dir)
    iterations = {}
    
    for f in files:
        match = iter_pattern.match(f)
        if match:
            iter_num = int(match.group(1))
            stroke_type = match.group(2)
            
            if iter_num not in iterations:
                iterations[iter_num] = {}
            iterations[iter_num][stroke_type] = os.path.join(group_images_dir, f)
    
    # Filter to only complete pairs and sort by iteration
    for iter_num in sorted(iterations.keys()):
        if left_key in iterations[iter_num] and right_key in iterations[iter_num]:
            pairs.append((iter_num, iterations[iter_num][left_key], iterations[iter_num][right_key]))
    
    return pairs


def create_side_by_side_frame(left_img_path: str, right_img_path: str, 
                               iteration: int, output_path: str,
                               left_label: str = "16 strokes", 
                               right_label: str = "32 strokes",
                               show_iteration: bool = True,
                               grayscale: bool = True):
    """
    Create a side-by-side frame with left (16s) and right (32s) images.
    
    Args:
        left_img_path: Path to left image (16s)
        right_img_path: Path to right image (32s)
        iteration: Current iteration number
        output_path: Path to save the combined frame
        left_label: Label for left side
        right_label: Label for right side
        show_iteration: Whether to show iteration number
        grayscale: Whether to convert images to grayscale (black and white)
    """
    # Load images
    left_img = Image.open(left_img_path).convert('RGB')
    right_img = Image.open(right_img_path).convert('RGB')
    
    # Convert colored pixels to black (threshold: non-white becomes black)
    if grayscale:
        # Process left image
        left_arr = np.array(left_img)
        # Find non-white pixels (any channel < 250)
        non_white_mask = np.any(left_arr < 250, axis=2)
        left_arr[non_white_mask] = [0, 0, 0]  # Set to black
        left_arr[~non_white_mask] = [255, 255, 255]  # Ensure white is pure white
        left_img = Image.fromarray(left_arr)
        
        # Process right image
        right_arr = np.array(right_img)
        non_white_mask = np.any(right_arr < 250, axis=2)
        right_arr[non_white_mask] = [0, 0, 0]  # Set to black
        right_arr[~non_white_mask] = [255, 255, 255]  # Ensure white is pure white
        right_img = Image.fromarray(right_arr)
    
    img_width, img_height = left_img.size
    
    # Layout parameters
    gap = 80  # Gap between images
    padding = 50  # Padding around edges
    header_height = 100  # Space for labels at top
    footer_height = 80  # Space for iteration counter at bottom
    
    canvas_width = img_width * 2 + gap + padding * 2
    canvas_height = img_height + header_height + footer_height + padding
    
    # Ensure dimensions are even (required for yuv420p)
    canvas_width = canvas_width + (canvas_width % 2)
    canvas_height = canvas_height + (canvas_height % 2)
    
    # Create canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # Calculate positions
    left_x = padding
    right_x = padding + img_width + gap
    img_y = header_height
    
    # Paste images
    canvas.paste(left_img, (left_x, img_y))
    canvas.paste(right_img, (right_x, img_y))
    
    # Try to load a nice font, fall back to default
    try:
        # Try common font paths
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        label_font = None
        iter_font = None
        for fp in font_paths:
            if os.path.exists(fp):
                label_font = ImageFont.truetype(fp, 42)  # Larger font for labels
                iter_font = ImageFont.truetype(fp, 32)   # Larger font for iteration
                break
        if label_font is None:
            label_font = ImageFont.load_default()
            iter_font = ImageFont.load_default()
    except Exception:
        label_font = ImageFont.load_default()
        iter_font = ImageFont.load_default()
    
    # Draw labels
    left_label_x = left_x + img_width // 2
    right_label_x = right_x + img_width // 2
    label_y = header_height // 2
    
    # Get text bounding boxes for centering
    left_bbox = draw.textbbox((0, 0), left_label, font=label_font)
    right_bbox = draw.textbbox((0, 0), right_label, font=label_font)
    
    draw.text((left_label_x - (left_bbox[2] - left_bbox[0]) // 2, 
               label_y - (left_bbox[3] - left_bbox[1]) // 2), 
              left_label, fill='black', font=label_font)
    draw.text((right_label_x - (right_bbox[2] - right_bbox[0]) // 2, 
               label_y - (right_bbox[3] - right_bbox[1]) // 2), 
              right_label, fill='black', font=label_font)
    
    # Draw iteration counter
    if show_iteration:
        iter_text = f"Iteration: {iteration}"
        iter_bbox = draw.textbbox((0, 0), iter_text, font=iter_font)
        iter_x = canvas_width // 2 - (iter_bbox[2] - iter_bbox[0]) // 2
        iter_y = img_y + img_height + (footer_height - (iter_bbox[3] - iter_bbox[1])) // 2
        draw.text((iter_x, iter_y), iter_text, fill='rgb(80,80,80)', font=iter_font)
    
    # Save frame
    canvas.save(output_path)
    return canvas_width, canvas_height


def generate_optimization_video(run_folder: str, output_video: str = None,
                                fps: int = 10, hold_final: float = 2.0,
                                p1: str = None, p2: str = None,
                                left_strokes: int = None, right_strokes: int = None,
                                grayscale: bool = True):
    """
    Generate optimization video from a run folder.
    
    Args:
        run_folder: Path to the run folder containing group_images
        output_video: Output video path (default: run_folder/optimization.mp4)
        fps: Frames per second for the video
        hold_final: Seconds to hold the final frame
        p1: Name for phase 1 (left side)
        p2: Name for phase 2 (right side)
        left_strokes: Number of strokes for left side (auto-detect if None)
        right_strokes: Number of strokes for right side (auto-detect if None)
        grayscale: Whether to convert images to grayscale
    """
    run_folder = Path(run_folder)
    group_images_dir = run_folder / "group_images"
    
    if not group_images_dir.exists():
        print(f"Error: group_images directory not found at {group_images_dir}")
        return False
    
    # Auto-detect stroke numbers if not specified
    available_strokes = detect_stroke_numbers(str(group_images_dir))
    
    if not available_strokes:
        print("Error: No stroke files found in group_images")
        return False
    
    print(f"Available stroke numbers: {available_strokes}")
    
    # Use first two stroke numbers if not specified
    if left_strokes is None:
        left_strokes = available_strokes[0] if len(available_strokes) >= 1 else 16
    if right_strokes is None:
        right_strokes = available_strokes[1] if len(available_strokes) >= 2 else 32
    
    print(f"Using: left={left_strokes}s, right={right_strokes}s")
    
    # Generate labels with actual stroke numbers
    if p1:
        left_label = f"{p1} ({left_strokes} strokes)"
    else:
        left_label = f"{left_strokes} strokes"
    
    if p2:
        right_label = f"{p2} ({right_strokes} strokes)"
    else:
        right_label = f"{right_strokes} strokes"
    
    # Find iteration pairs
    pairs = find_iteration_pairs(str(group_images_dir), left_strokes, right_strokes)
    
    if not pairs:
        print("Error: No iteration pairs found")
        return False
    
    print(f"Found {len(pairs)} iteration pairs")
    print(f"  First: iter_{pairs[0][0]:04d}")
    print(f"  Last:  iter_{pairs[-1][0]:04d}")
    
    # Check for final images
    final_left = group_images_dir / f"final_{left_strokes}s.png"
    final_right = group_images_dir / f"final_{right_strokes}s.png"
    has_final = final_left.exists() and final_right.exists()
    
    if has_final:
        print("  Found final images")
    
    # Default output path
    if output_video is None:
        output_video = str(run_folder / "optimization.mp4")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_idx = 0
        canvas_size = None
        
        # Generate frames for each iteration
        print("\nGenerating frames...")
        for iter_num, path_16s, path_32s in pairs:
            frame_path = os.path.join(temp_dir, f'frame_{frame_idx:06d}.png')
            w, h = create_side_by_side_frame(
                path_16s, path_32s, iter_num, frame_path,
                left_label=left_label, right_label=right_label,
                show_iteration=True, grayscale=grayscale
            )
            if canvas_size is None:
                canvas_size = (w, h)
            frame_idx += 1
            
            if frame_idx % 5 == 0:
                print(f"  Generated frame {frame_idx}/{len(pairs) + (1 if has_final else 0)}")
        
        # Add final frame if exists
        if has_final:
            # Get the last iteration number for the final frame display
            last_iter = pairs[-1][0] if pairs else 0
            frame_path = os.path.join(temp_dir, f'frame_{frame_idx:06d}.png')
            create_side_by_side_frame(
                str(final_left), str(final_right), last_iter, frame_path,
                left_label=left_label, right_label=right_label,
                show_iteration=False, grayscale=grayscale  # Don't show iteration for final
            )
            frame_idx += 1
        
        # Duplicate last frame for hold
        hold_frames = int(fps * hold_final)
        last_frame_path = os.path.join(temp_dir, f'frame_{frame_idx-1:06d}.png')
        for i in range(hold_frames):
            import shutil
            hold_frame_path = os.path.join(temp_dir, f'frame_{frame_idx:06d}.png')
            shutil.copy(last_frame_path, hold_frame_path)
            frame_idx += 1
        
        print(f"\nTotal frames: {frame_idx}")
        
        # Create video with ffmpeg
        print("\nCreating video...")
        try:
            output_path = Path(output_video)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            subprocess.run([
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_dir, 'frame_%06d.png'),
                '-c:v', 'libx264',
                '-preset', 'slow',  # Better compression efficiency
                '-crf', '12',  # Very high quality (lower = better, 0-51)
                '-pix_fmt', 'yuv420p',
                '-vf', 'unsharp=5:5:1.0:5:5:0.0',  # Sharpen filter for crisp edges
                str(output_path)
            ], check=True, capture_output=True)
            
            print(f"\nVideo saved to: {output_path}")
            print(f"Duration: {frame_idx / fps:.2f} seconds")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating video: {e}")
            print(f"stderr: {e.stderr.decode() if e.stderr else ''}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate optimization video showing two stroke versions side by side",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python generate_optimization_video.py video/optimization/chicken+monkey-6 --p1 chicken --p2 monkey
  python generate_optimization_video.py video/optimization/chicken+monkey-6 -o output.mp4 --fps 15 --p1 chicken --p2 monkey
  python generate_optimization_video.py video/optimization/run1 --left-strokes 32 --right-strokes 64
"""
    )
    
    parser.add_argument('run_folder', type=str, 
                       help='Path to the run folder containing group_images')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output video path (default: run_folder/optimization.mp4)')
    parser.add_argument('--fps', type=int, default=10,
                       help='Frames per second (default: 10)')
    parser.add_argument('--hold', type=float, default=2.0,
                       help='Seconds to hold final frame (default: 2.0)')
    parser.add_argument('--p1', type=str, default=None,
                       help='Name for phase 1 (left side)')
    parser.add_argument('--p2', type=str, default=None,
                       help='Name for phase 2 (right side)')
    parser.add_argument('--left-strokes', type=int, default=None,
                       help='Number of strokes for left side (auto-detect if not specified)')
    parser.add_argument('--right-strokes', type=int, default=None,
                       help='Number of strokes for right side (auto-detect if not specified)')
    parser.add_argument('--no-grayscale', action='store_true',
                       help='Keep original colors instead of converting to grayscale')
    
    args = parser.parse_args()
    
    if not Path(args.run_folder).exists():
        print(f"Error: Run folder does not exist: {args.run_folder}")
        return 1
    
    success = generate_optimization_video(
        args.run_folder,
        args.output,
        args.fps,
        args.hold,
        args.p1,
        args.p2,
        args.left_strokes,
        args.right_strokes,
        grayscale=not args.no_grayscale
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

