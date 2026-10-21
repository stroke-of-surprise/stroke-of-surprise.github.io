#!/usr/bin/env python3
"""
Script to create GIFs from group_images folder with WHITE background.
Based on tools/log2gif.py but ensures all images have white backgrounds.

- Single mode: Creates GIFs from group_images folder, grouping by strokes number (e.g., 10s, 16s, 32s)
  and combining them into a grid animation (log_animation.gif)
- Grid mode: Creates grid animations across multiple run folders, with separate GIFs for each strokes number
  (grid_log_10s.gif, grid_log_16s.gif, grid_log_32s.gif, etc.)
"""

import os
import shutil
import sys
import re
import argparse
from pathlib import Path
from PIL import Image
from PIL import ImageDraw, ImageFont
import tempfile
import tqdm
import json
import math
from collections import defaultdict
import termcolor

OUTPUT_SUBDIR_NAME = "gif_outputs"


def composite_on_white(img):
    """
    Composite an image onto a white background.
    Handles images with transparency (RGBA, LA, P with transparency).
    """
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        # Composite
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    else:
        return img.convert('RGB')


def natural_sort_key(s):
    """Sort strings with numbers naturally (e.g., iter100 comes before iter1000)"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


def extract_strokes_from_filename(filename):
    """
    Extract strokes number from filename (e.g., iter_0000_10s.png -> 10s)
    Returns strokes string (e.g., '10s') or None if not found
    """
    # Pattern: _<number>s.png or _<number>s_
    match = re.search(r'_(\d+s)\.png$', str(filename))
    if match:
        return match.group(1)
    return None


def create_gif_from_images(image_files, output_gif, duration=100):
    """
    Create GIF from existing PNG/JPG image files with WHITE background
    
    Args:
        image_files: List of image file paths
        output_gif: Output GIF file path
        duration: Duration per frame in milliseconds
    """
    if not image_files:
        print(f"No image files found for {output_gif}")
        return
    
    images = []
    for i, img_file in tqdm.tqdm(enumerate(image_files), total=len(image_files), desc="Creating GIF: "):
        img = Image.open(img_file)
        # Composite on white background
        img = composite_on_white(img)
        images.append(img)
    
    if not images:
        print(f"Error: No images were loaded for {output_gif}")
        return
    
    # Save as GIF
    images[0].save(
        output_gif,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0,
        optimize=False
    )


def create_grid_gif_from_gifs(gif_files, strokes_labels, output_gif, img_size=512, padding=10, duration=100, title=None, iter_names=None):
    """
    Create a grid GIF by combining frames from multiple GIF files side by side
    
    Args:
        gif_files: List of GIF file paths (one for each strokes number)
        strokes_labels: List of labels for each GIF (e.g., ['10s', '16s', '32s'])
        output_gif: Output grid GIF file path
        img_size: Size of each image in the grid
        padding: Padding between images
        duration: Duration per frame in milliseconds
        title: Title to display at the top (e.g., folder name + iter_xxxx)
        iter_names: List of iteration names for each frame (e.g., ['iter_0000', 'iter_0100', ...])
    """
    if not gif_files:
        print(f"No GIF files provided for {output_gif}")
        return False
    
    # Load all GIFs and extract their frames
    all_frames = []
    max_frames = 0
    
    for gif_file in gif_files:
        if not Path(gif_file).exists():
            print(f"Warning: GIF file not found: {gif_file}")
            all_frames.append([])
            continue
        
        frames = []
        with Image.open(gif_file) as img:
            try:
                while True:
                    frame = img.copy()
                    # Composite on white background
                    frame = composite_on_white(frame)
                    if frame.size != (img_size, img_size):
                        frame = frame.resize((img_size, img_size), Image.LANCZOS)
                    frames.append(frame)
                    img.seek(img.tell() + 1)
            except EOFError:
                pass
        all_frames.append(frames)
        max_frames = max(max_frames, len(frames))
    
    if max_frames == 0:
        print(f"Error: No frames found in any GIF file")
        return False
    
    # Create grid frames
    n_strokes = len(strokes_labels)
    label_height = 30
    title_height = 60 if title else 0
    grid_width = n_strokes * img_size + (n_strokes + 1) * padding
    grid_height = img_size + 2 * padding + label_height + title_height
    
    grid_images = []
    for frame_idx in range(max_frames):
        # Create WHITE background grid
        grid_img = Image.new('RGB', (grid_width, grid_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(grid_img)
        
        # Try to load fonts
        try:
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            try:
                label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 24)
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
            except:
                label_font = ImageFont.load_default()
                title_font = ImageFont.load_default()
        
        # Draw title if provided
        title_offset = 0
        if title:
            # Combine title with iter name if available
            display_title = title
            if iter_names and frame_idx < len(iter_names):
                display_title = f"{title} - {iter_names[frame_idx]}"
            
            bbox = draw.textbbox((0, 0), display_title, font=title_font)
            title_width = bbox[2] - bbox[0]
            title_x = (grid_width - title_width) // 2
            draw.text((title_x, 15), display_title, fill='black', font=title_font)
            title_offset = title_height
        
        # Draw images and labels
        image_y = padding + title_offset
        for idx, (strokes_label, frames) in enumerate(zip(strokes_labels, all_frames)):
            x = idx * img_size + (idx + 1) * padding
            y = image_y
            
            if frame_idx < len(frames):
                grid_img.paste(frames[frame_idx], (x, y))
            else:
                # Use last frame if this GIF has fewer frames
                if frames:
                    grid_img.paste(frames[-1], (x, y))
            
            # Draw label below image
            label_y = y + img_size + 5
            bbox = draw.textbbox((0, 0), strokes_label, font=label_font)
            text_width = bbox[2] - bbox[0]
            text_x = x + (img_size - text_width) // 2
            draw.text((text_x, label_y), strokes_label, fill='black', font=label_font)
        
        grid_images.append(grid_img)
    
    # Save as GIF
    if grid_images:
        grid_images[0].save(
            output_gif,
            save_all=True,
            append_images=grid_images[1:],
            duration=duration,
            loop=0,
            optimize=False
        )
        return True
    return False


def process_png_logs(folder, duration):
    """Process png_logs folder and create GIFs
    Format: iter_0000.png, iter_0000_black.png, iter_0100.png, iter_0100_black.png, etc.
    Creates log_animation.gif and log_animation_black.gif (if black images exist).
    """
    png_logs_dir = folder / 'png_logs'
    if not png_logs_dir.exists():
        return False
    
    # Get all PNG files
    all_png_files = list(png_logs_dir.glob('*.png'))
    
    if not all_png_files:
        print(f"Warning: No PNG files found in: {png_logs_dir}")
        return False
    
    # Separate regular and black images
    regular_images = []
    black_images = []
    
    for png_file in all_png_files:
        # Skip _group.png files
        if '_group' in png_file.name:
            continue
        # Check if it's a black image
        if '_black.png' in png_file.name:
            base_name = png_file.stem.replace('_black', '')
            black_images.append((base_name, png_file))
        else:
            base_name = png_file.stem
            if re.match(r'^iter_\d+$', base_name):
                regular_images.append((base_name, png_file))
    
    # Sort by iteration number
    regular_images = sorted(regular_images, key=lambda x: natural_sort_key(x[0]))
    black_images = sorted(black_images, key=lambda x: natural_sort_key(x[0]))
    
    if not regular_images:
        print(f"Warning: No valid iter_*.png files found in: {png_logs_dir}")
        return False
    
    print(f"\n[PNG Logs] Found {len(regular_images)} regular images and {len(black_images)} black images")
    
    # Create output directory
    output_dir = folder / OUTPUT_SUBDIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    
    success = False
    
    # Create regular GIF
    regular_gif = output_dir / 'log_animation.gif'
    regular_image_files = [img[1] for img in regular_images]
    print(f"\nCreating regular GIF: {regular_gif.name} ({len(regular_image_files)} frames)...")
    create_gif_from_images(regular_image_files, str(regular_gif), duration)
    if regular_gif.exists():
        success = True
    
    # Create black GIF if black images exist
    if black_images:
        black_gif = output_dir / 'log_animation_black.gif'
        black_image_files = [img[1] for img in black_images]
        print(f"\nCreating black GIF: {black_gif.name} ({len(black_image_files)} frames)...")
        create_gif_from_images(black_image_files, str(black_gif), duration)
    
    return success


def process_group_images(folder, duration):
    """Process group_images folder and create GIFs
    New format: iter_0000_10s.png, iter_0000_16s.png, iter_0000_32s.png, etc.
    Creates separate GIFs for each strokes number, then combines them in a grid GIF.
    If group_images doesn't exist, falls back to png_logs.
    """
    group_images_dir = folder / 'group_images'
    png_logs_dir = folder / 'png_logs'
    
    # If group_images doesn't exist, try png_logs
    if not group_images_dir.exists():
        if png_logs_dir.exists():
            print(f"group_images not found, using png_logs instead...")
            return process_png_logs(folder, duration)
        else:
            print(f"Warning: Neither group_images nor png_logs directory found in: {folder}")
            return False
    
    # Get all PNG files
    all_png_files = list(group_images_dir.glob('*.png'))
    
    if not all_png_files:
        print(f"Warning: No PNG files found in: {group_images_dir}")
        return False
    
    # Group images by strokes number (e.g., '10s', '16s', '32s')
    strokes_dict = defaultdict(list)
    for png_file in all_png_files:
        strokes = extract_strokes_from_filename(png_file)
        if strokes:
            strokes_dict[strokes].append(png_file)
    
    if not strokes_dict:
        print(f"Warning: No valid strokes numbers found in filenames (expected pattern: *_XXs.png)")
        return False
    
    # Sort strokes labels (e.g., '10s', '16s', '32s')
    strokes_labels = sorted(strokes_dict.keys(), key=lambda x: int(x.replace('s', '')))
    
    print(f"\n[Group Images] Found {len(strokes_labels)} different strokes numbers: {', '.join(strokes_labels)}")
    for strokes in strokes_labels:
        print(f"  - {strokes}: {len(strokes_dict[strokes])} images")
    
    # Create output directory
    output_dir = folder / OUTPUT_SUBDIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract iter names from the first strokes group (all strokes should have same iters)
    first_strokes = strokes_labels[0]
    first_images = sorted(strokes_dict[first_strokes], key=natural_sort_key)
    iter_names = []
    for img_path in first_images:
        stem = img_path.stem
        match = re.match(r'(iter_\d+)', stem)
        if match:
            iter_names.append(match.group(1))
        else:
            parts = stem.rsplit('_', 1)
            if len(parts) == 2:
                iter_names.append(parts[0])
    
    # Create temporary directory for individual strokes GIFs
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_gif_files = []
        
        # Create a GIF for each strokes number
        for strokes in strokes_labels:
            images = sorted(strokes_dict[strokes], key=natural_sort_key)
            temp_gif_path = Path(temp_dir) / f'strokes_{strokes}.gif'
            
            print(f"\nCreating GIF for {strokes} strokes ({len(images)} frames)...")
            create_gif_from_images(images, str(temp_gif_path), duration)
            
            if temp_gif_path.exists():
                temp_gif_files.append(str(temp_gif_path))
        
        if not temp_gif_files:
            print("Error: No GIFs were created for any strokes number")
            return False
        
        # Create final grid GIF combining all strokes
        final_gif = output_dir / 'log_animation.gif'
        print(f"\nCreating grid GIF combining {len(strokes_labels)} strokes numbers...")
        success = create_grid_gif_from_gifs(
            temp_gif_files, 
            strokes_labels, 
            str(final_gif), 
            duration=duration,
            title=folder.name,
            iter_names=iter_names
        )
        
        return success and final_gif.exists()


# ========================= GRID MODE =========================

def load_obj_bb_from_config(run_folder):
    """
    Load obj_bb from config.json in the run folder
    Returns [x0, x1, y0, y1] or None
    """
    config_file = run_folder / 'config.json'
    if not config_file.exists():
        return None
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config.get('obj_bb', None)
    except:
        return None


def scale_bbox(obj_bb, original_size, target_size):
    if obj_bb is None or len(obj_bb) != 4:
        return obj_bb
    orig_w, orig_h = original_size
    target_w, target_h = target_size
    scale_x = target_w / orig_w
    scale_y = target_h / orig_h
    x0, x1, y0, y1 = obj_bb
    scaled_x0 = max(0, min(int(x0 * scale_x), target_w - 1))
    scaled_x1 = max(0, min(int(x1 * scale_x), target_w - 1))
    scaled_y0 = max(0, min(int(y0 * scale_y), target_h - 1))
    scaled_y1 = max(0, min(int(y1 * scale_y), target_h - 1))
    return [scaled_x0, scaled_x1, scaled_y0, scaled_y1]


def draw_bbox_on_image(img, obj_bb, bbox_color='red', bbox_width=3):
    if obj_bb is None or len(obj_bb) != 4:
        return img
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    x0, x1, y0, y1 = obj_bb
    draw.rectangle([(x0, y0), (x1, y1)], outline=bbox_color, width=bbox_width)
    return img_copy


def create_grid_from_images(image_files, run_names, output_path, img_size=512, cols=None, padding=10, label_height=40, title=None, title_height=60, obj_bbs=None):
    if not image_files:
        print(f"No image files to process for {output_path}")
        return False
    n_images = len(image_files)
    if cols is None:
        cols = math.ceil(math.sqrt(n_images))
    rows = math.ceil(n_images / cols)
    loaded_images = []
    for idx, img_file in enumerate(image_files):
        if img_file is None or not Path(img_file).exists():
            # Create WHITE placeholder
            placeholder = Image.new('RGB', (img_size, img_size), color=(255, 255, 255))
            loaded_images.append(placeholder)
        else:
            img = Image.open(img_file)
            # Composite on white background
            img = composite_on_white(img)
            if img.size != (img_size, img_size):
                img = img.resize((img_size, img_size), Image.LANCZOS)
            if obj_bbs is not None and idx < len(obj_bbs) and obj_bbs[idx] is not None:
                scaled_bbox = scale_bbox(obj_bbs[idx], (512, 512), (img_size, img_size))
                img = draw_bbox_on_image(img, scaled_bbox)
            loaded_images.append(img)
    cell_width = img_size
    cell_height = img_size + label_height
    grid_width = cols * cell_width + (cols + 1) * padding
    grid_height = rows * cell_height + (rows + 1) * padding
    if title:
        grid_height += title_height
        title_offset = title_height
    else:
        title_offset = 0
    # Create WHITE background grid
    grid_img = Image.new('RGB', (grid_width, grid_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(grid_img)
    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        try:
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20)
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
        except:
            label_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
    if title:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = bbox[2] - bbox[0]
        title_x = (grid_width - title_width) // 2
        draw.text((title_x, 15), title, fill='black', font=title_font)
    for idx, (img, run_name) in enumerate(zip(loaded_images, run_names)):
        row = idx // cols
        col = idx % cols
        x = col * cell_width + (col + 1) * padding
        y = row * cell_height + (row + 1) * padding + title_offset
        grid_img.paste(img, (x, y))
        label_y = y + img_size + 5
        bbox = draw.textbbox((0, 0), run_name, font=label_font)
        text_width = bbox[2] - bbox[0]
        text_x = x + (img_size - text_width) // 2
        draw.text((text_x, label_y), run_name, fill='black', font=label_font)
    grid_img.save(output_path, quality=95)
    return True


def process_png_logs_grid(run_folders, folder, output_dir, args):
    """Process png_logs folders in grid mode
    Creates grid_log.gif and grid_log_black.gif from log_animation.gif of each run
    """
    print("\n" + "="*60)
    print("Processing png_logs folders (grid mode)...")
    print("="*60)
    
    # Load obj_bb from config.json if enabled
    obj_bbs_dict = {}
    if args.draw_bbox:
        print("Bounding box drawing is enabled. Loading obj_bb from config.json...")
        for run_folder in run_folders:
            obj_bb = load_obj_bb_from_config(run_folder)
            if obj_bb is not None:
                obj_bbs_dict[run_folder.name] = obj_bb
        if not obj_bbs_dict:
            print("  No obj_bb found in any config.json")
    
    # First, create log_animation.gif for each run folder if it doesn't exist
    run_gif_paths = {}
    run_gif_black_paths = {}
    
    for run_folder in run_folders:
        png_logs_dir = run_folder / 'png_logs'
        if not png_logs_dir.exists():
            print(f"Warning: png_logs not found in {run_folder.name}, skipping")
            continue
        
        # Check if GIF already exists
        run_output_dir = run_folder / OUTPUT_SUBDIR_NAME
        run_gif = run_output_dir / 'log_animation.gif'
        run_gif_black = run_output_dir / 'log_animation_black.gif'
        
        # Create GIFs if they don't exist
        if not run_gif.exists():
            print(f"Creating log_animation.gif for {run_folder.name}...")
            process_png_logs(run_folder, args.duration)
        
        if run_gif.exists():
            run_gif_paths[run_folder.name] = str(run_gif)
        if run_gif_black.exists():
            run_gif_black_paths[run_folder.name] = str(run_gif_black)
    
    if not run_gif_paths:
        print("\nNo log_animation.gif files found in any run folder!")
        return False
    
    sorted_run_names = sorted(run_gif_paths.keys(), key=natural_sort_key)
    print(f"\nFound {len(sorted_run_names)} runs with log_animation.gif")
    if run_gif_black_paths:
        print(f"Found {len(run_gif_black_paths)} runs with log_animation_black.gif")
    
    # Create output directories
    gif_output_dir = output_dir / OUTPUT_SUBDIR_NAME
    gif_output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    
    # Extract frames from all GIFs and create grid frames
    all_frames_dict = {}
    max_frames = 0
    
    for run_name in sorted_run_names:
        gif_path = run_gif_paths[run_name]
        frames = []
        with Image.open(gif_path) as img:
            try:
                while True:
                    frame = img.copy()
                    # Composite on white background
                    frame = composite_on_white(frame)
                    if frame.size != (args.img_size, args.img_size):
                        frame = frame.resize((args.img_size, args.img_size), Image.LANCZOS)
                    frames.append(frame)
                    img.seek(img.tell() + 1)
            except EOFError:
                pass
        all_frames_dict[run_name] = frames
        max_frames = max(max_frames, len(frames))
    
    if max_frames == 0:
        print("\nError: No frames found in any GIF!")
        return False
    
    # Create grid frames
    grid_frames = []
    for frame_idx in tqdm.tqdm(range(max_frames), desc="Creating grid frames"):
        run_names = []
        frame_images = []
        
        for run_name in sorted_run_names:
            run_names.append(run_name)
            frames = all_frames_dict[run_name]
            if frame_idx < len(frames):
                frame_images.append(frames[frame_idx])
            else:
                if frames:
                    frame_images.append(frames[-1])
                else:
                    frame_images.append(None)
        
        obj_bbs_list = [obj_bbs_dict.get(run_name, None) for run_name in run_names]
        
        # Create temporary directory for frame images
        with tempfile.TemporaryDirectory() as temp_frame_dir:
            temp_image_paths = []
            for idx, img in enumerate(frame_images):
                if img is None:
                    temp_image_paths.append(None)
                else:
                    temp_img_path = os.path.join(temp_frame_dir, f'frame_{frame_idx}_img{idx}.png')
                    img.save(temp_img_path)
                    temp_image_paths.append(temp_img_path)
            
            # Create temporary grid frame
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                grid_path = tmp_file.name
                
                success = create_grid_from_images(
                    temp_image_paths,
                    run_names,
                    grid_path,
                    img_size=args.img_size,
                    cols=args.cols,
                    padding=args.padding,
                    title=f"{folder.name} - frame {frame_idx}",
                    obj_bbs=obj_bbs_list if obj_bbs_dict else None
                )
                
                if success:
                    grid_frames.append(grid_path)
    
    if not grid_frames:
        print("\nError: No grid frames were created!")
        return False
    
    # Create grid GIF
    output_gif = gif_output_dir / 'grid_log.gif'
    print(f"\nCreating grid GIF: {output_gif.name}")
    create_gif_from_images(grid_frames, str(output_gif), duration=args.duration)
    
    # Save last frame as PNG
    if output_gif.exists() and grid_frames:
        output_png = gif_output_dir / 'grid_log.png'
        try:
            shutil.copy(grid_frames[-1], str(output_png))
            print(f"  Saved last frame: {output_png.name}")
        except Exception as e:
            print(f"  Warning: Failed to copy last frame: {e}")
    
    # Clean up temporary grid frames
    for tmp_path in grid_frames:
        try:
            os.unlink(tmp_path)
        except:
            pass
    
    if output_gif.exists():
        success_count += 1
    
    # Process black GIFs if they exist
    if run_gif_black_paths:
        print(f"\nProcessing black GIFs...")
        all_frames_black_dict = {}
        max_frames_black = 0
        
        for run_name in sorted(run_gif_black_paths.keys(), key=natural_sort_key):
            if run_name not in sorted_run_names:
                continue
            gif_path = run_gif_black_paths[run_name]
            frames = []
            with Image.open(gif_path) as img:
                try:
                    while True:
                        frame = img.copy()
                        frame = composite_on_white(frame)
                        if frame.size != (args.img_size, args.img_size):
                            frame = frame.resize((args.img_size, args.img_size), Image.LANCZOS)
                        frames.append(frame)
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
            all_frames_black_dict[run_name] = frames
            max_frames_black = max(max_frames_black, len(frames))
        
        if max_frames_black > 0:
            grid_frames_black = []
            for frame_idx in tqdm.tqdm(range(max_frames_black), desc="Creating black grid frames"):
                run_names = []
                frame_images = []
                
                for run_name in sorted_run_names:
                    run_names.append(run_name)
                    if run_name in all_frames_black_dict:
                        frames = all_frames_black_dict[run_name]
                        if frame_idx < len(frames):
                            frame_images.append(frames[frame_idx])
                        else:
                            if frames:
                                frame_images.append(frames[-1])
                            else:
                                frame_images.append(None)
                    else:
                        frame_images.append(None)
                
                obj_bbs_list = [obj_bbs_dict.get(run_name, None) for run_name in run_names]
                
                with tempfile.TemporaryDirectory() as temp_frame_dir:
                    temp_image_paths = []
                    for idx, img in enumerate(frame_images):
                        if img is None:
                            temp_image_paths.append(None)
                        else:
                            temp_img_path = os.path.join(temp_frame_dir, f'black_frame_{frame_idx}_img{idx}.png')
                            img.save(temp_img_path)
                            temp_image_paths.append(temp_img_path)
                    
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                        grid_path = tmp_file.name
                        
                        success = create_grid_from_images(
                            temp_image_paths,
                            run_names,
                            grid_path,
                            img_size=args.img_size,
                            cols=args.cols,
                            padding=args.padding,
                            title=f"{folder.name} - black - frame {frame_idx}",
                            obj_bbs=obj_bbs_list if obj_bbs_dict else None
                        )
                        
                        if success:
                            grid_frames_black.append(grid_path)
            
            if grid_frames_black:
                output_gif_black = gif_output_dir / 'grid_log_black.gif'
                print(f"Creating black grid GIF: {output_gif_black.name}")
                create_gif_from_images(grid_frames_black, str(output_gif_black), duration=args.duration)
                
                if output_gif_black.exists() and grid_frames_black:
                    output_png_black = gif_output_dir / 'grid_log_black.png'
                    try:
                        shutil.copy(grid_frames_black[-1], str(output_png_black))
                        print(f"  Saved last frame: {output_png_black.name}")
                    except Exception as e:
                        print(f"  Warning: Failed to copy last frame: {e}")
                
                for tmp_path in grid_frames_black:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                
                if output_gif_black.exists():
                    success_count += 1
    
    return success_count > 0


def process_group_images_grid(run_folders, folder, output_dir, args):
    print("\n" + "="*60)
    print("Processing group_images folders...")
    print("="*60)
    
    # Load obj_bb from config.json if enabled
    obj_bbs_dict = {}
    if args.draw_bbox:
        print("Bounding box drawing is enabled. Loading obj_bb from config.json...")
        for run_folder in run_folders:
            obj_bb = load_obj_bb_from_config(run_folder)
            if obj_bb is not None:
                obj_bbs_dict[run_folder.name] = obj_bb
        if not obj_bbs_dict:
            print("  No obj_bb found in any config.json")

    # Group images by strokes number and iteration across all runs
    strokes_dict = defaultdict(lambda: defaultdict(list))
    all_strokes = set()
    
    for run_folder in run_folders:
        group_images_dir = run_folder / 'group_images'
        if not group_images_dir.exists():
            print(f"Warning: group_images not found in {run_folder.name}, skipping")
            continue
        
        png_files = list(group_images_dir.glob('*.png'))
        if not png_files:
            print(f"Warning: No PNG files found in {run_folder.name}/group_images, skipping")
            continue

        for png_file in png_files:
            strokes = extract_strokes_from_filename(png_file)
            if not strokes:
                continue
            
            all_strokes.add(strokes)
            stem = png_file.stem
            match = re.match(r'(iter_\d+)', stem)
            if match:
                iter_name = match.group(1)
                strokes_dict[strokes][iter_name].append((run_folder.name, png_file))
            else:
                parts = stem.rsplit('_', 1)
                if len(parts) == 2 and parts[1] == strokes:
                    iter_name = parts[0]
                    strokes_dict[strokes][iter_name].append((run_folder.name, png_file))
    
    if not strokes_dict:
        print("\nNo valid PNG files with strokes pattern found in any run folder's group_images!")
        return False
    
    # Sort strokes labels
    sorted_strokes = sorted(all_strokes, key=lambda x: int(x.replace('s', '')))
    print(f"\nFound {len(sorted_strokes)} different strokes numbers: {', '.join(sorted_strokes)}")

    # Create output directories
    gif_output_dir = output_dir / OUTPUT_SUBDIR_NAME
    gif_output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    
    # Process each strokes number separately
    for strokes in sorted_strokes:
        print(f"\nProcessing strokes: {strokes}")
        iter_dict = strokes_dict[strokes]
        sorted_iters = sorted(iter_dict.keys(), key=natural_sort_key)
        sorted_run_names = sorted(set([run_name for iters in iter_dict.values() for run_name, _ in iters]), 
                                   key=natural_sort_key)
        
        # Create grid frames for this strokes number
        grid_frames = []
        for iter_name in tqdm.tqdm(sorted_iters, desc=f"Creating grids for {strokes}"):
            run_names = []
            image_paths = []
            
            for run_name in sorted_run_names:
                run_names.append(run_name)
                found = False
                for rn, png_file in iter_dict[iter_name]:
                    if rn == run_name:
                        image_paths.append(str(png_file))
                        found = True
                        break
                if not found:
                    image_paths.append(None)
            
            obj_bbs_list = [obj_bbs_dict.get(run_name, None) for run_name in run_names]
            
            # Create temporary grid frame
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                grid_path = tmp_file.name
                success = create_grid_from_images(
                    image_paths,
                    run_names,
                    grid_path,
                    img_size=args.img_size,
                    cols=args.cols,
                    padding=args.padding,
                    title=f"{folder.name} - {strokes} - {iter_name}",
                    obj_bbs=obj_bbs_list if obj_bbs_dict else None
                )
                if success:
                    grid_frames.append(grid_path)
        
        if not grid_frames:
            print(f"\nError: No grid frames were created for {strokes}!")
            continue
        
        # Create GIF animation for this strokes number
        output_gif = gif_output_dir / f'grid_log_{strokes}.gif'
        print(f"Creating GIF: {output_gif.name}")
        create_gif_from_images(grid_frames, str(output_gif), duration=args.duration)
        
        # Save last frame as PNG
        if output_gif.exists() and grid_frames:
            output_png = gif_output_dir / f'grid_log_{strokes}.png'
            try:
                shutil.copy(grid_frames[-1], str(output_png))
                print(f"  Saved last frame: {output_png.name}")
            except Exception as e:
                print(f"  Warning: Failed to copy last frame: {e}")
        
        # Clean up temporary grid frames
        for tmp_path in grid_frames:
            try:
                os.unlink(tmp_path)
            except:
                pass
        
        if output_gif.exists():
            success_count += 1
    
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description='Create GIFs and grids with WHITE background',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Single mode (default):\n"
            "    python log2gif_trans.py single ControlSketch/.../run7/32_strokes --duration 100\n"
            "    python log2gif_trans.py ControlSketch/.../run7/32_strokes --duration 100\n"
            "  Grid mode (across runs):\n"
            "    python log2gif_trans.py grid ControlSketch/test/loop/horse_bbox_loop --cols 4 --img-size 256 --draw-bbox\n"
        )
    )

    subparsers = parser.add_subparsers(dest='mode')

    # Single mode (process group_images folder)
    p_single = subparsers.add_parser('single', help='Create GIFs from group_images in a single folder')
    p_single.add_argument('folder', type=str, help='Folder containing group_images subdirectory')
    p_single.add_argument('--duration', type=int, default=100, help='Duration per frame in milliseconds (default: 100)')

    # Grid mode (create grid animations across multiple run folders)
    p_grid = subparsers.add_parser('grid', help='Create grid animations across multiple run folders in a parent folder')
    p_grid.add_argument('folder', type=str, help='Folder containing run subdirectories (e.g., ControlSketch/test/loop/horse_bbox_loop)')
    p_grid.add_argument('--img-size', type=int, default=300, help='Cell image size (default: 300)')
    p_grid.add_argument('--cols', type=int, default=None, help='Columns in grid (auto if not specified)')
    p_grid.add_argument('--padding', type=int, default=10, help='Padding between images (default: 10)')
    p_grid.add_argument('--duration', type=int, default=100, help='Duration per frame in ms (default: 100)')
    p_grid.add_argument('--output-dir', type=str, default=None, help='Output directory (default: input folder)')
    p_grid.add_argument('--draw-bbox', '--bbox', action='store_true', help='Draw obj_bb from config.json')
    p_grid.add_argument('--n_samples', '-n', type=int, default=None, help='Number of run folders to include')

    # If no subcommand is provided, default to single mode for backward compatibility
    args, unknown = parser.parse_known_args()
    if args.mode is None:
        # Re-parse as single mode by injecting 'single'
        args = parser.parse_args(['single'] + unknown)

    if args.mode == 'single':
        folder = Path(args.folder)
        if not folder.exists():
            print(f"Error: Folder does not exist: {folder}")
            sys.exit(1)
        print(termcolor.colored("="*60, "yellow"))
        print(termcolor.colored(f"Processing folder: {folder}", "yellow"))
        print(termcolor.colored("="*60, "yellow"))
        group_processed = process_group_images(folder, args.duration)
        print(termcolor.colored("\n" + "="*60, "green"))
        print(termcolor.colored("Summary", "green"))
        print(termcolor.colored("="*60, "green"))
        if group_processed:
            print(termcolor.colored("✓ Group images processed:", "green"))
            output_dir = folder / OUTPUT_SUBDIR_NAME
            if (output_dir / 'log_animation.gif').exists():
                print(termcolor.colored(f"  - {output_dir / 'log_animation.gif'}", "green"))
        if not group_processed:
            print(termcolor.colored("Error: No valid group_images directory found!", "red"))
            sys.exit(1)
        print(termcolor.colored("="*60, "green"))
        return

    if args.mode == 'grid':
        folder = Path(args.folder)
        if not folder.exists():
            print(f"Error: Folder does not exist: {folder}")
            sys.exit(1)
        print(termcolor.colored("="*60, "yellow"))
        print(termcolor.colored(f"Processing folder: {folder}", "yellow"))
        print(termcolor.colored("="*60, "yellow"))
        # Collect child folders
        candidate_dirs = [d for d in folder.iterdir() if d.is_dir() and not d.name.startswith('.')]
        run_folders_group = []
        run_folders_png = []
        for d in candidate_dirs:
            if (d / 'group_images').exists():
                run_folders_group.append(d)
            elif (d / 'png_logs').exists():
                run_folders_png.append(d)
        
        # Determine which processing function to use
        if run_folders_group:
            run_folders = sorted(run_folders_group, key=lambda x: natural_sort_key(x.name))
            processing_type = "Group images"
        elif run_folders_png:
            run_folders = sorted(run_folders_png, key=lambda x: natural_sort_key(x.name))
            processing_type = "PNG logs"
        else:
            print(f"Error: No run folders with group_images or png_logs found in: {folder}")
            sys.exit(1)
        
        if not run_folders:
            print(f"Error: No run folders found in: {folder}")
            sys.exit(1)
        print(f"\nFound {len(run_folders)} run folders: {', '.join([d.name for d in run_folders])}")
        if getattr(args, 'n_samples', None) is not None and args.n_samples > 0:
            original_count = len(run_folders)
            if original_count > args.n_samples:
                print(f"Limiting to first {args.n_samples} run folders (out of {original_count} total)")
                run_folders = run_folders[:args.n_samples]
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = folder
        
        # Call appropriate processing function
        if processing_type == "Group images":
            success = process_group_images_grid(run_folders, folder, output_dir, args)
        else:
            success = process_png_logs_grid(run_folders, folder, output_dir, args)

        print(termcolor.colored("\n" + "="*60, "green"))
        print(termcolor.colored("Summary", "green"))
        print(termcolor.colored("="*60, "green"))
        if success:
            print(termcolor.colored(f"✓ {processing_type} processed:", "green"))
            gif_output_dir = output_dir / OUTPUT_SUBDIR_NAME
            grid_gifs = sorted(gif_output_dir.glob('grid_log_*.gif'))
            grid_pngs = sorted(gif_output_dir.glob('grid_log_*.png'))
            for gif_file in grid_gifs:
                print(termcolor.colored(f"  - Animation GIF: {gif_file.name}", "green"))
            for png_file in grid_pngs:
                print(termcolor.colored(f"  - Grid PNG: {png_file.name}", "green"))
        if not success:
            print(termcolor.colored("Error: No valid subdirectories found!", "red"))
            sys.exit(1)
        print(termcolor.colored("="*60, "green"))
        return


if __name__ == '__main__':
    main()

