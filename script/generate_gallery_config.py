#!/usr/bin/env python3
"""
Generate gallery configuration JSON from video files in the illusions directory.
Run this script whenever new videos are added to update the gallery.

Usage:
    python script/generate_gallery_config.py
"""

import os
import json
from pathlib import Path

def get_video_files(directory):
    """Get all mp4 files in a directory, sorted with numbered files first."""
    if not os.path.exists(directory):
        return []
    
    videos = []
    numbered = []
    unnumbered = []
    
    for f in os.listdir(directory):
        if f.endswith('.mp4'):
            # Check if it starts with a number in parentheses like (1), (2), etc.
            if f.startswith('(') and ')' in f:
                try:
                    num = int(f[1:f.index(')')])
                    numbered.append((num, f))
                except ValueError:
                    unnumbered.append(f)
            else:
                unnumbered.append(f)
    
    # Sort numbered files by number, unnumbered alphabetically
    numbered.sort(key=lambda x: x[0])
    unnumbered.sort()
    
    videos = [f for _, f in numbered] + unnumbered
    return videos

def get_svg_folders(directory, file_ext='.svg'):
    """Get all folders containing sketch_p1 and sketch_p2 files with specified extension."""
    if not os.path.exists(directory):
        return []
    
    folders = []
    numbered = []
    unnumbered = []
    
    for f in os.listdir(directory):
        folder_path = os.path.join(directory, f)
        if os.path.isdir(folder_path):
            # Check if it contains sketch_p1 and sketch_p2 files with specified extension
            p1_exists = os.path.exists(os.path.join(folder_path, f'sketch_p1{file_ext}'))
            p2_exists = os.path.exists(os.path.join(folder_path, f'sketch_p2{file_ext}'))
            
            if p1_exists and p2_exists:
                # Parse folder name to create label
                # Format: "concept1+concept2-number" -> "Concept1 → Concept2"
                # First, remove leading number pattern like "(1)", "(2)", etc.
                folder_name_for_label = f
                if folder_name_for_label.startswith('(') and ')' in folder_name_for_label:
                    # Remove the (N) prefix
                    folder_name_for_label = folder_name_for_label[folder_name_for_label.index(')') + 1:].strip()
                
                parts = folder_name_for_label.split('+')
                if len(parts) >= 2:
                    # Remove trailing number (e.g., "-25")
                    last_part = parts[-1]
                    if '-' in last_part:
                        last_part = last_part.rsplit('-', 1)[0]
                    parts[-1] = last_part
                    
                    label = ' → '.join(p.replace('_', ' ').title() for p in parts)
                else:
                    label = folder_name_for_label.replace('_', ' ').title()
                
                folder_info = {'folder': f, 'label': label}
                
                # Check if folder name starts with a number pattern
                if f.startswith('(') and ')' in f:
                    try:
                        num = int(f[1:f.index(')')])
                        numbered.append((num, folder_info))
                        continue
                    except ValueError:
                        pass
                
                unnumbered.append(folder_info)
    
    # Sort numbered folders by number, unnumbered alphabetically
    numbered.sort(key=lambda x: x[0])
    unnumbered.sort(key=lambda x: x['folder'])
    
    folders = [f for _, f in numbered] + unnumbered
    return folders

def main():
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define paths
    illusions_dir = project_root / 'static' / 'illusions'
    gallery_dir = illusions_dir / 'gallery'
    bezier_dir = illusions_dir / 'bezier-cruve'
    bspline_dir = illusions_dir / 'bspline'
    vector_graph_dir = illusions_dir / 'vector-graph'
    output_file = project_root / 'static' / 'js' / 'gallery-config.json'
    
    # Generate config
    config = {
        # Video galleries (for gallery pages)
        '2-phase': {
            'basePath': '../static/illusions/gallery/2-phase/',
            'videos': get_video_files(gallery_dir / '2-phase')
        },
        '3-phase': {
            'basePath': '../static/illusions/gallery/3-phase/',
            'videos': get_video_files(gallery_dir / '3-phase')
        },
        'optimization': {
            'basePath': '../static/illusions/gallery/optimization/',
            'videos': get_video_files(gallery_dir / 'optimization')
        },
        # SVG galleries (for index page)
        'svg-2-phase': {
            'basePath': './static/illusions/bezier-cruve/2-phase/',
            'folders': get_svg_folders(bezier_dir / '2-phase')
        },
        'svg-3-phase': {
            'basePath': './static/illusions/bezier-cruve/3-phase/',
            'folders': get_svg_folders(bezier_dir / '3-phase')
        },
        'svg-bspline': {
            'basePath': './static/illusions/bspline/',
            'folders': get_svg_folders(bspline_dir, '.png')
        },
        'svg-vector-graph': {
            'basePath': './static/illusions/vector-graph/',
            'folders': get_svg_folders(vector_graph_dir, '.png')
        }
    }
    
    # Write to JSON file
    os.makedirs(output_file.parent, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"Gallery config generated: {output_file}")
    print("\nVideo galleries:")
    print(f"  2-phase: {len(config['2-phase']['videos'])} videos")
    print(f"  3-phase: {len(config['3-phase']['videos'])} videos")
    print(f"  optimization: {len(config['optimization']['videos'])} videos")
    print("\nSVG galleries:")
    print(f"  svg-2-phase: {len(config['svg-2-phase']['folders'])} folders")
    print(f"  svg-3-phase: {len(config['svg-3-phase']['folders'])} folders")
    print(f"  svg-bspline: {len(config['svg-bspline']['folders'])} folders")
    print(f"  svg-vector-graph: {len(config['svg-vector-graph']['folders'])} folders")

if __name__ == '__main__':
    main()
