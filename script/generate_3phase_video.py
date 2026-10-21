#!/usr/bin/env python3
"""
Generate video animation showing phase 1 -> phase 2 -> phase 3 progression.
1. Phase 1 animates on the left side
2. Phase 1 converts to black and stays static (left)
3. Phase 1 (black) duplicates and moves to center
4. Phase 2 animates on the center (on top of phase 1 copy)
5. Phase 2 converts to black
6. Phase 2 (black) duplicates and moves to right
7. Phase 3 animates on the right (on top of phase 2 copy)
8. Phase 3 converts to black
"""

import xml.etree.ElementTree as ET
import re
import sys
import argparse
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image

# Import functions from sort_svg_strokes.py
from sort_svg_strokes import extract_stroke_color, parse_rgb_color


def extract_phase_paths(input_svg: str, phase_idx: int, phase_color: str, ns_uri: str = None) -> List[ET.Element]:
    """
    Extract paths of a specific phase from sorted SVG file.
    
    Args:
        input_svg: Path to sorted SVG file
        phase_idx: Phase index (0, 1, 2, ...)
        phase_color: Color string for this phase (tab10 color)
        ns_uri: SVG namespace URI (if any)
    
    Returns:
        List of path elements for this phase
    """
    tree = ET.parse(input_svg)
    root = tree.getroot()
    
    paths = []
    for path in root.iter():
        tag = path.tag
        if ns_uri and tag.startswith('{'):
            tag = tag[len('{' + ns_uri + '}'):]
        
        if tag == 'path':
            color = extract_stroke_color(path)
            if color == phase_color:
                paths.append(path)
    
    return paths


def create_3phase_composite_svg(left_paths: Optional[List[ET.Element]], 
                                center_paths: Optional[List[ET.Element]],
                                right_paths: Optional[List[ET.Element]],
                                left_x: float, center_x: float, right_x: float,
                                canvas_width: float, canvas_height: float, 
                                left_color: Optional[str] = None, 
                                center_color: Optional[str] = None,
                                right_color: Optional[str] = None,
                                show_arrow1: bool = False, arrow1_x: float = None,
                                show_arrow2: bool = False, arrow2_x: float = None,
                                arrow_color: str = None,
                                arrow1_opacity: float = 1.0, arrow2_opacity: float = 1.0,
                                arrow_length: float = 60.0,
                                left_caption: Optional[str] = None, 
                                center_caption: Optional[str] = None,
                                right_caption: Optional[str] = None,
                                left_caption_opacity: float = 1.0, 
                                center_caption_opacity: float = 1.0,
                                right_caption_opacity: float = 1.0,
                                ns_uri: str = None) -> ET.Element:
    """
    Create composite SVG with left, center, and right paths, with optional arrows.
    """
    svg_ns = ns_uri if ns_uri else "http://www.w3.org/2000/svg"
    if ns_uri:
        ET.register_namespace('', ns_uri)
        root = ET.Element(f"{{{ns_uri}}}svg")
    else:
        root = ET.Element('svg')
        root.set('xmlns', svg_ns)
    root.set('version', '1.1')
    root.set('width', str(int(canvas_width)))
    root.set('height', str(int(canvas_height)))
    root.set('viewBox', f'0 0 {int(canvas_width)} {int(canvas_height)}')
    
    # Add white background
    bg_tag = 'rect' if ns_uri is None else f"{{{ns_uri}}}rect"
    bg = ET.SubElement(root, bg_tag)
    bg.set('width', str(int(canvas_width)))
    bg.set('height', str(int(canvas_height)))
    bg.set('fill', 'white')
    
    caption_height = 100  # Space for captions
    svg_width = 512
    svg_height = 512
    
    # Left side
    if left_paths is not None:
        left_g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
        left_g = ET.SubElement(root, left_g_tag)
        left_g.set('transform', f'translate({left_x},{caption_height})')
        
        for path in left_paths:
            path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
            new_path = ET.SubElement(left_g, path_tag)
            
            for attr, value in path.attrib.items():
                if left_color and attr == 'stroke':
                    new_path.set(attr, left_color)
                elif left_color and attr == 'style' and 'stroke:' in value:
                    style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{left_color}', value)
                    new_path.set(attr, style_value)
                else:
                    new_path.set(attr, value)
            
            if left_color and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
                new_path.set('stroke', left_color)
    
    # Center side
    if center_paths is not None:
        center_g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
        center_g = ET.SubElement(root, center_g_tag)
        center_g.set('transform', f'translate({center_x},{caption_height})')
        
        for path in center_paths:
            path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
            new_path = ET.SubElement(center_g, path_tag)
            
            for attr, value in path.attrib.items():
                if center_color and attr == 'stroke':
                    new_path.set(attr, center_color)
                elif center_color and attr == 'style' and 'stroke:' in value:
                    style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{center_color}', value)
                    new_path.set(attr, style_value)
                else:
                    new_path.set(attr, value)
            
            if center_color and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
                new_path.set('stroke', center_color)
    
    # Right side
    if right_paths is not None:
        right_g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
        right_g = ET.SubElement(root, right_g_tag)
        right_g.set('transform', f'translate({right_x},{caption_height})')
        
        for path in right_paths:
            path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
            new_path = ET.SubElement(right_g, path_tag)
            
            for attr, value in path.attrib.items():
                if right_color and attr == 'stroke':
                    new_path.set(attr, right_color)
                elif right_color and attr == 'style' and 'stroke:' in value:
                    style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{right_color}', value)
                    new_path.set(attr, style_value)
                else:
                    new_path.set(attr, value)
            
            if right_color and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
                new_path.set('stroke', right_color)
    
    # Add arrows
    arrow_color_val = arrow_color if arrow_color else 'rgb(100,100,100)'
    
    if show_arrow1 or show_arrow2:
        # Arrowhead marker definition
        defs_tag = 'defs' if ns_uri is None else f"{{{ns_uri}}}defs"
        defs = ET.SubElement(root, defs_tag)
        
        marker_tag = 'marker' if ns_uri is None else f"{{{ns_uri}}}marker"
        marker = ET.SubElement(defs, marker_tag)
        marker.set('id', 'arrowhead')
        marker.set('markerWidth', '10')
        marker.set('markerHeight', '10')
        marker.set('refX', '9')
        marker.set('refY', '3')
        marker.set('orient', 'auto')
        
        polygon_tag = 'polygon' if ns_uri is None else f"{{{ns_uri}}}polygon"
        polygon = ET.SubElement(marker, polygon_tag)
        polygon.set('points', '0 0, 10 3, 0 6')
        polygon.set('fill', arrow_color_val)
    
    # Arrow 1 (between left and center)
    if show_arrow1 and arrow1_x is not None:
        arrow_g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
        arrow_g = ET.SubElement(root, arrow_g_tag)
        arrow_y = caption_height + svg_height / 2
        arrow_g.set('transform', f'translate({arrow1_x},{arrow_y})')
        arrow_g.set('opacity', str(arrow1_opacity))
        
        line_tag = 'line' if ns_uri is None else f"{{{ns_uri}}}line"
        arrow_line = ET.SubElement(arrow_g, line_tag)
        arrow_line.set('x1', '0')
        arrow_line.set('y1', '0')
        arrow_line.set('x2', str(arrow_length))
        arrow_line.set('y2', '0')
        arrow_line.set('stroke', arrow_color_val)
        arrow_line.set('stroke-width', '4')
        arrow_line.set('marker-end', 'url(#arrowhead)')
    
    # Arrow 2 (between center and right)
    if show_arrow2 and arrow2_x is not None:
        arrow_g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
        arrow_g = ET.SubElement(root, arrow_g_tag)
        arrow_y = caption_height + svg_height / 2
        arrow_g.set('transform', f'translate({arrow2_x},{arrow_y})')
        arrow_g.set('opacity', str(arrow2_opacity))
        
        line_tag = 'line' if ns_uri is None else f"{{{ns_uri}}}line"
        arrow_line = ET.SubElement(arrow_g, line_tag)
        arrow_line.set('x1', '0')
        arrow_line.set('y1', '0')
        arrow_line.set('x2', str(arrow_length))
        arrow_line.set('y2', '0')
        arrow_line.set('stroke', arrow_color_val)
        arrow_line.set('stroke-width', '4')
        arrow_line.set('marker-end', 'url(#arrowhead)')
    
    # Add captions
    caption_y = 80
    caption_font_size = 48  # Slightly smaller for 3 phases
    
    # Left caption
    if left_caption:
        left_caption_x = left_x + svg_width / 2
        text_tag = 'text' if ns_uri is None else f"{{{ns_uri}}}text"
        left_text = ET.SubElement(root, text_tag)
        left_text.set('x', str(int(left_caption_x)))
        left_text.set('y', str(caption_y))
        left_text.set('font-family', 'Arial, sans-serif')
        left_text.set('font-size', str(caption_font_size))
        left_text.set('font-weight', 'bold')
        left_text.set('fill', 'rgb(0,0,0)')
        left_text.set('opacity', str(left_caption_opacity))
        left_text.set('text-anchor', 'middle')
        left_text.set('alignment-baseline', 'middle')
        left_text.text = left_caption
    
    # Center caption
    if center_caption:
        center_caption_x = center_x + svg_width / 2
        text_tag = 'text' if ns_uri is None else f"{{{ns_uri}}}text"
        center_text = ET.SubElement(root, text_tag)
        center_text.set('x', str(int(center_caption_x)))
        center_text.set('y', str(caption_y))
        center_text.set('font-family', 'Arial, sans-serif')
        center_text.set('font-size', str(caption_font_size))
        center_text.set('font-weight', 'bold')
        center_text.set('fill', 'rgb(0,0,0)')
        center_text.set('opacity', str(center_caption_opacity))
        center_text.set('text-anchor', 'middle')
        center_text.set('alignment-baseline', 'middle')
        center_text.text = center_caption
    
    # Right caption
    if right_caption:
        right_caption_x = right_x + svg_width / 2
        text_tag = 'text' if ns_uri is None else f"{{{ns_uri}}}text"
        right_text = ET.SubElement(root, text_tag)
        right_text.set('x', str(int(right_caption_x)))
        right_text.set('y', str(caption_y))
        right_text.set('font-family', 'Arial, sans-serif')
        right_text.set('font-size', str(caption_font_size))
        right_text.set('font-weight', 'bold')
        right_text.set('fill', 'rgb(0,0,0)')
        right_text.set('opacity', str(right_caption_opacity))
        right_text.set('text-anchor', 'middle')
        right_text.set('alignment-baseline', 'middle')
        right_text.text = right_caption
    
    return root


def convert_svg_to_png(svg_path: str, png_path: str, width: int = 512, height: int = 512) -> bool:
    """
    Convert SVG file to PNG using rsvg-convert or cairosvg.
    """
    try:
        subprocess.run([
            'rsvg-convert',
            '--background-color', 'white',
            '--width', str(width),
            '--height', str(height),
            '-o', png_path,
            svg_path,
        ], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            import cairosvg
            cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width, output_height=height)
            return True
        except ImportError:
            print(f"Warning: Neither rsvg-convert nor cairosvg available.")
            return False
        except Exception as e:
            print(f"Warning: Failed to convert SVG to PNG: {e}")
            return False


def parse_path_data(path_d: str) -> List[Tuple[float, float]]:
    """Parse SVG path data and extract coordinate points."""
    points = []
    commands = path_d.split()
    
    i = 0
    current_x, current_y = 0, 0
    
    while i < len(commands):
        cmd = commands[i]
        
        if cmd in ['M', 'L']:
            if i + 2 < len(commands):
                x = float(commands[i + 1])
                y = float(commands[i + 2])
                points.append((x, y))
                current_x, current_y = x, y
                i += 3
            else:
                i += 1
                
        elif cmd == 'C':
            if i + 6 < len(commands):
                x1 = float(commands[i + 1])
                y1 = float(commands[i + 2])
                x2 = float(commands[i + 3])
                y2 = float(commands[i + 4])
                x = float(commands[i + 5])
                y = float(commands[i + 6])
                
                for t_idx in range(21):
                    t = t_idx / 20.0
                    curve_x = (1-t)**3 * current_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x
                    curve_y = (1-t)**3 * current_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y
                    points.append((curve_x, curve_y))
                current_x, current_y = x, y
                i += 7
            else:
                i += 1
        else:
            i += 1
    
    return points


def create_frame_svg(paths: List[ET.Element], current_stroke: int, stroke_progress: float,
                    dimensions: Tuple[float, float], output_path: str, color_override: str = None,
                    ns_uri: str = None):
    """
    Create a static SVG frame showing strokes with drawing progress.
    """
    width, height = dimensions
    
    svg_ns = ns_uri if ns_uri else "http://www.w3.org/2000/svg"
    if ns_uri:
        ET.register_namespace('', ns_uri)
        root = ET.Element(f"{{{ns_uri}}}svg")
    else:
        root = ET.Element('svg')
        root.set('xmlns', svg_ns)
    
    root.set('version', '1.1')
    root.set('width', str(int(width)))
    root.set('height', str(int(height)))
    root.set('viewBox', f'0 0 {int(width)} {int(height)}')
    
    bg_tag = 'rect' if ns_uri is None else f"{{{ns_uri}}}rect"
    bg = ET.SubElement(root, bg_tag)
    bg.set('width', str(int(width)))
    bg.set('height', str(int(height)))
    bg.set('fill', 'white')
    
    g_tag = 'g' if ns_uri is None else f"{{{ns_uri}}}g"
    g = ET.SubElement(root, g_tag)
    
    # Add fully drawn strokes
    for path_idx in range(current_stroke):
        path_elem = paths[path_idx]
        path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
        new_path = ET.SubElement(g, path_tag)
        
        for attr, value in path_elem.attrib.items():
            if color_override and attr == 'stroke':
                new_path.set(attr, color_override)
            elif color_override and attr == 'style' and 'stroke:' in value:
                style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{color_override}', value)
                new_path.set(attr, style_value)
            else:
                new_path.set(attr, value)
        
        if color_override and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
            new_path.set('stroke', color_override)
    
    # Add current stroke with progress
    if current_stroke < len(paths) and stroke_progress > 0:
        path_elem = paths[current_stroke]
        path_d = path_elem.get('d', '')
        
        points = parse_path_data(path_d)
        path_length = 0
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            path_length += (dx**2 + dy**2)**0.5
        
        if path_length > 0:
            path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
            new_path = ET.SubElement(g, path_tag)
            
            for attr, value in path_elem.attrib.items():
                if attr in ['stroke-dasharray', 'stroke-dashoffset']:
                    continue
                if color_override and attr == 'stroke':
                    new_path.set(attr, color_override)
                elif color_override and attr == 'style' and 'stroke:' in value:
                    style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{color_override}', value)
                    new_path.set(attr, style_value)
                else:
                    new_path.set(attr, value)
            
            if color_override and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
                new_path.set('stroke', color_override)
            
            dashoffset = path_length * (1.0 - stroke_progress)
            new_path.set('stroke-dasharray', str(path_length))
            new_path.set('stroke-dashoffset', str(dashoffset))
    
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)


def generate_3phase_video(input_svg: str, output_video: str, fps: int = 30,
                         p1_caption: str = None, p2_caption: str = None, p3_caption: str = None):
    """
    Generate video showing phase 1 -> phase 2 -> phase 3 progression.
    """
    # First, sort the SVG to identify phases
    print("Step 1: Sorting SVG to identify phases...")
    sorted_svg = str(Path(input_svg).parent / f"{Path(input_svg).stem}_sorted_temp.svg")
    
    from sort_svg_strokes import sort_svg_file
    success, num_phases, phase_to_color, ns_uri = sort_svg_file(input_svg, sorted_svg)
    
    if not success or num_phases < 3:
        print(f"Error: Need at least 3 phases, found {num_phases}")
        sys.exit(1)
    
    print(f"Found {num_phases} phases")
    for phase_idx in range(min(3, num_phases)):
        print(f"  Phase {phase_idx}: {phase_to_color[phase_idx]}")
    
    # Extract phase paths
    phase0_color = phase_to_color[0]
    phase1_color = phase_to_color[1]
    phase2_color = phase_to_color[2]
    
    phase0_paths = extract_phase_paths(sorted_svg, 0, phase0_color, ns_uri)
    phase1_paths = extract_phase_paths(sorted_svg, 1, phase1_color, ns_uri)
    phase2_paths = extract_phase_paths(sorted_svg, 2, phase2_color, ns_uri)
    
    print(f"Phase 0: {len(phase0_paths)} strokes")
    print(f"Phase 1: {len(phase1_paths)} strokes")
    print(f"Phase 2: {len(phase2_paths)} strokes")
    
    dimensions = (512, 512)
    svg_width = 512
    svg_height = 512
    gap = 60  # Gap between phases (smaller for 3 phases)
    arrow_width = 50  # Width for arrow
    total_width = svg_width * 3 + gap * 2 + arrow_width * 2
    canvas_width = total_width + 80
    caption_height = 100
    canvas_height = svg_height + caption_height
    
    # Calculate centered positions
    start_x = (canvas_width - total_width) / 2
    phase0_x = start_x
    phase1_x = start_x + svg_width + gap + arrow_width
    phase2_x = start_x + (svg_width + gap + arrow_width) * 2
    arrow1_x = start_x + svg_width + gap / 2
    arrow2_x = start_x + svg_width + gap + arrow_width + svg_width + gap / 2
    
    # Animation parameters
    base_frames_per_stroke = 8
    hold_frames = int(fps * 2)  # Final hold
    caption_fade_frames = int(fps * 0.4)
    transition_frames = int(fps * 0.8)  # Faster transitions for 3 phases
    hold_before_caption_frames = int(fps * 0.4)
    color_transition_frames = int(fps * 0.25)
    arrow_animation_frames = int(fps * 0.25)
    
    frames = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_idx = 0
        
        # ====== PHASE 1 (p1) ======
        # Step 1: Animate phase 0 (p1) on left side
        print("\nStep 1: Generating phase 0 (p1) animation frames...")
        for stroke_idx in range(len(phase0_paths)):
            path_d = phase0_paths[stroke_idx].get('d', '')
            points = parse_path_data(path_d)
            path_length = sum(
                ((points[i][0] - points[i-1][0])**2 + (points[i][1] - points[i-1][1])**2)**0.5
                for i in range(1, len(points))
            ) if len(points) > 1 else 0
            
            stroke_frames = max(base_frames_per_stroke, int(base_frames_per_stroke * (path_length / 150.0)))
            stroke_frames = min(stroke_frames, 15)
            
            for frame_in_stroke in range(stroke_frames + 1):
                stroke_progress = frame_in_stroke / stroke_frames
                
                frame_svg_path = os.path.join(temp_dir, f'phase0_frame_{frame_idx:04d}.svg')
                create_frame_svg(phase0_paths, stroke_idx, stroke_progress, dimensions, 
                               frame_svg_path, color_override=None, ns_uri=ns_uri)
                
                frame_tree = ET.parse(frame_svg_path)
                frame_root = frame_tree.getroot()
                
                frame_paths = []
                for elem in frame_root:
                    tag = elem.tag
                    if ns_uri and tag.startswith('{'):
                        tag = tag[len('{' + ns_uri + '}'):]
                    if tag == 'g':
                        for path_elem in elem:
                            path_tag = path_elem.tag
                            if ns_uri and path_tag.startswith('{'):
                                path_tag = path_tag[len('{' + ns_uri + '}'):]
                            if path_tag == 'path':
                                frame_paths.append(path_elem)
                
                composite_svg = create_3phase_composite_svg(
                    frame_paths, None, None,
                    phase0_x, phase1_x, phase2_x,
                    canvas_width, canvas_height,
                    ns_uri=ns_uri
                )
                
                composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
                ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
                
                composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
                if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                    img = Image.open(composite_png)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    frames.append(img)
                    frame_idx += 1
        
        # Hold after p1 animation
        print("\nStep 1b: Holding p1 animation completion...")
        for _ in range(hold_before_caption_frames):
            composite_svg = create_3phase_composite_svg(
                phase0_paths, None, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 2: Convert phase 0 to black
        print("\nStep 2: Converting phase 0 to black...")
        for t in range(color_transition_frames + 1):
            progress = t / color_transition_frames
            phase0_rgb = parse_rgb_color(phase0_color)
            r = int(phase0_rgb[0] * (1 - progress))
            g = int(phase0_rgb[1] * (1 - progress))
            b = int(phase0_rgb[2] * (1 - progress))
            transition_color = f"rgb({r},{g},{b})"
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, None, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color=transition_color,
                ns_uri=ns_uri
            )
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 3: Show p1 caption (fade in)
        print("\nStep 3: Showing p1 caption (fade in)...")
        for t in range(caption_fade_frames + 1):
            caption_opacity = t / caption_fade_frames
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, None, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)",
                left_caption=p1_caption,
                left_caption_opacity=caption_opacity,
                ns_uri=ns_uri
            )
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 4: Phase 0 copies to center
        print("\nStep 4: Animating phase 0 copying to center...")
        for t in range(transition_frames + 1):
            progress = t / transition_frames
            current_center_x = phase0_x + (phase1_x - phase0_x) * progress
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, phase0_paths, None,
                phase0_x, current_center_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)",
                left_caption=p1_caption,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Show arrow 1 (fade in)
        print("\nStep 4b: Showing arrow 1 (fade in)...")
        for t in range(arrow_animation_frames + 1):
            arrow_opacity = t / arrow_animation_frames
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, phase0_paths, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=arrow_opacity,
                left_caption=p1_caption,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # ====== PHASE 2 (p2) ======
        # Step 5: Animate phase 1 (p2) on center side
        print("\nStep 5: Animating phase 1 (p2) on center...")
        
        for stroke_idx in range(len(phase1_paths)):
            path_d = phase1_paths[stroke_idx].get('d', '')
            points = parse_path_data(path_d)
            path_length = sum(
                ((points[i][0] - points[i-1][0])**2 + (points[i][1] - points[i-1][1])**2)**0.5
                for i in range(1, len(points))
            ) if len(points) > 1 else 0
            
            stroke_frames = max(base_frames_per_stroke, int(base_frames_per_stroke * (path_length / 150.0)))
            stroke_frames = min(stroke_frames, 15)
            
            for frame_in_stroke in range(stroke_frames + 1):
                stroke_progress = frame_in_stroke / stroke_frames
                
                # Build center paths: phase 0 (black) + phase 1 (colored, showing progress)
                center_paths = list(phase0_paths)
                for p_idx in range(stroke_idx):
                    center_paths.append(phase1_paths[p_idx])
                if stroke_progress > 0:
                    center_paths.append(phase1_paths[stroke_idx])
                
                composite_svg = create_3phase_composite_svg(
                    phase0_paths, center_paths, None,
                    phase0_x, phase1_x, phase2_x,
                    canvas_width, canvas_height,
                    left_color="rgb(0,0,0)", center_color=None,
                    show_arrow1=True, arrow1_x=arrow1_x,
                    arrow_color="rgb(100,100,100)", arrow1_opacity=1.0,
                    left_caption=p1_caption,
                    ns_uri=ns_uri
                )
                
                # Make phase 0 paths in center black, add dasharray to current phase 1 stroke
                for g in composite_svg:
                    tag = g.tag
                    if ns_uri and tag.startswith('{'):
                        tag = tag[len('{' + ns_uri + '}'):]
                    
                    if tag == 'g' and 'transform' in g.attrib and f'translate({phase1_x}' in g.attrib['transform']:
                        path_idx_in_center = 0
                        for path in g:
                            if path_idx_in_center < len(phase0_paths):
                                path.set('stroke', 'rgb(0,0,0)')
                                style = path.get('style', '')
                                if 'stroke:' in style:
                                    style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                    path.set('style', style)
                            else:
                                phase1_idx = path_idx_in_center - len(phase0_paths)
                                if phase1_idx == stroke_idx and stroke_progress < 1.0 and stroke_progress > 0:
                                    path_d = phase1_paths[stroke_idx].get('d', '')
                                    points = parse_path_data(path_d)
                                    path_length_calc = sum(
                                        ((points[i][0] - points[i-1][0])**2 + 
                                         (points[i][1] - points[i-1][1])**2)**0.5
                                        for i in range(1, len(points))
                                    ) if len(points) > 1 else 0
                                    if path_length_calc > 0:
                                        dashoffset = path_length_calc * (1.0 - stroke_progress)
                                        path.set('stroke-dasharray', str(path_length_calc))
                                        path.set('stroke-dashoffset', str(dashoffset))
                            path_idx_in_center += 1
                        break
                
                composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
                ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
                
                composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
                if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                    img = Image.open(composite_png)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    frames.append(img)
                    frame_idx += 1
        
        center_paths_full = phase0_paths + phase1_paths
        
        # Hold after p2 animation
        print("\nStep 5b: Holding p2 animation completion...")
        for _ in range(hold_before_caption_frames):
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color=None,
                show_arrow1=True, arrow1_x=arrow1_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0,
                left_caption=p1_caption,
                ns_uri=ns_uri
            )
            # Make phase 0 paths in center black
            for g in composite_svg:
                tag = g.tag
                if ns_uri and tag.startswith('{'):
                    tag = tag[len('{' + ns_uri + '}'):]
                if tag == 'g' and 'transform' in g.attrib and f'translate({phase1_x}' in g.attrib['transform']:
                    path_idx_in_center = 0
                    for path in g:
                        if path_idx_in_center < len(phase0_paths):
                            path.set('stroke', 'rgb(0,0,0)')
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                path.set('style', style)
                        path_idx_in_center += 1
                    break
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 6: Convert phase 1 to black
        print("\nStep 6: Converting phase 1 to black...")
        for t in range(color_transition_frames + 1):
            progress = t / color_transition_frames
            phase1_rgb = parse_rgb_color(phase1_color)
            r = int(phase1_rgb[0] * (1 - progress))
            g = int(phase1_rgb[1] * (1 - progress))
            b = int(phase1_rgb[2] * (1 - progress))
            transition_color = f"rgb({r},{g},{b})"
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color=None,
                show_arrow1=True, arrow1_x=arrow1_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0,
                left_caption=p1_caption,
                ns_uri=ns_uri
            )
            
            # Make phase 0 paths in center black, phase 1 paths use transition color
            for g in composite_svg:
                tag = g.tag
                if ns_uri and tag.startswith('{'):
                    tag = tag[len('{' + ns_uri + '}'):]
                if tag == 'g' and 'transform' in g.attrib and f'translate({phase1_x}' in g.attrib['transform']:
                    path_idx_in_center = 0
                    for path in g:
                        if path_idx_in_center < len(phase0_paths):
                            path.set('stroke', 'rgb(0,0,0)')
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                path.set('style', style)
                        else:
                            path.set('stroke', transition_color)
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{transition_color}', style)
                                path.set('style', style)
                        path_idx_in_center += 1
                    break
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 7: Show p2 caption (fade in)
        print("\nStep 7: Showing p2 caption (fade in)...")
        for t in range(caption_fade_frames + 1):
            caption_opacity = t / caption_fade_frames
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, None,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption,
                center_caption_opacity=caption_opacity,
                ns_uri=ns_uri
            )
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 8: Phase 1+0 copies to right
        print("\nStep 8: Animating phase 0+1 copying to right...")
        for t in range(transition_frames + 1):
            progress = t / transition_frames
            current_right_x = phase1_x + (phase2_x - phase1_x) * progress
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, center_paths_full,
                phase0_x, phase1_x, current_right_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Show arrow 2 (fade in)
        print("\nStep 8b: Showing arrow 2 (fade in)...")
        for t in range(arrow_animation_frames + 1):
            arrow_opacity = t / arrow_animation_frames
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, center_paths_full,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                show_arrow2=True, arrow2_x=arrow2_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=arrow_opacity,
                left_caption=p1_caption, center_caption=p2_caption,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # ====== PHASE 3 (p3) ======
        # Step 9: Animate phase 2 (p3) on right side
        print("\nStep 9: Animating phase 2 (p3) on right...")
        
        for stroke_idx in range(len(phase2_paths)):
            path_d = phase2_paths[stroke_idx].get('d', '')
            points = parse_path_data(path_d)
            path_length = sum(
                ((points[i][0] - points[i-1][0])**2 + (points[i][1] - points[i-1][1])**2)**0.5
                for i in range(1, len(points))
            ) if len(points) > 1 else 0
            
            stroke_frames = max(base_frames_per_stroke, int(base_frames_per_stroke * (path_length / 150.0)))
            stroke_frames = min(stroke_frames, 15)
            
            for frame_in_stroke in range(stroke_frames + 1):
                stroke_progress = frame_in_stroke / stroke_frames
                
                # Build right paths: phase 0+1 (black) + phase 2 (colored, showing progress)
                right_paths = list(center_paths_full)
                for p_idx in range(stroke_idx):
                    right_paths.append(phase2_paths[p_idx])
                if stroke_progress > 0:
                    right_paths.append(phase2_paths[stroke_idx])
                
                composite_svg = create_3phase_composite_svg(
                    phase0_paths, center_paths_full, right_paths,
                    phase0_x, phase1_x, phase2_x,
                    canvas_width, canvas_height,
                    left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color=None,
                    show_arrow1=True, arrow1_x=arrow1_x,
                    show_arrow2=True, arrow2_x=arrow2_x,
                    arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=1.0,
                    left_caption=p1_caption, center_caption=p2_caption,
                    ns_uri=ns_uri
                )
                
                # Make phase 0+1 paths in right black, add dasharray to current phase 2 stroke
                for g in composite_svg:
                    tag = g.tag
                    if ns_uri and tag.startswith('{'):
                        tag = tag[len('{' + ns_uri + '}'):]
                    
                    if tag == 'g' and 'transform' in g.attrib and f'translate({phase2_x}' in g.attrib['transform']:
                        path_idx_in_right = 0
                        for path in g:
                            if path_idx_in_right < len(center_paths_full):
                                path.set('stroke', 'rgb(0,0,0)')
                                style = path.get('style', '')
                                if 'stroke:' in style:
                                    style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                    path.set('style', style)
                            else:
                                phase2_idx = path_idx_in_right - len(center_paths_full)
                                if phase2_idx == stroke_idx and stroke_progress < 1.0 and stroke_progress > 0:
                                    path_d = phase2_paths[stroke_idx].get('d', '')
                                    points = parse_path_data(path_d)
                                    path_length_calc = sum(
                                        ((points[i][0] - points[i-1][0])**2 + 
                                         (points[i][1] - points[i-1][1])**2)**0.5
                                        for i in range(1, len(points))
                                    ) if len(points) > 1 else 0
                                    if path_length_calc > 0:
                                        dashoffset = path_length_calc * (1.0 - stroke_progress)
                                        path.set('stroke-dasharray', str(path_length_calc))
                                        path.set('stroke-dashoffset', str(dashoffset))
                            path_idx_in_right += 1
                        break
                
                composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
                ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
                
                composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
                if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                    img = Image.open(composite_png)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    frames.append(img)
                    frame_idx += 1
        
        right_paths_full = center_paths_full + phase2_paths
        
        # Hold after p3 animation
        print("\nStep 9b: Holding p3 animation completion...")
        for _ in range(hold_before_caption_frames):
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, right_paths_full,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color=None,
                show_arrow1=True, arrow1_x=arrow1_x,
                show_arrow2=True, arrow2_x=arrow2_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption,
                ns_uri=ns_uri
            )
            # Make phase 0+1 paths in right black
            for g in composite_svg:
                tag = g.tag
                if ns_uri and tag.startswith('{'):
                    tag = tag[len('{' + ns_uri + '}'):]
                if tag == 'g' and 'transform' in g.attrib and f'translate({phase2_x}' in g.attrib['transform']:
                    path_idx_in_right = 0
                    for path in g:
                        if path_idx_in_right < len(center_paths_full):
                            path.set('stroke', 'rgb(0,0,0)')
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                path.set('style', style)
                        path_idx_in_right += 1
                    break
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 10: Convert phase 2 to black
        print("\nStep 10: Converting phase 2 to black...")
        for t in range(color_transition_frames + 1):
            progress = t / color_transition_frames
            phase2_rgb = parse_rgb_color(phase2_color)
            r = int(phase2_rgb[0] * (1 - progress))
            g = int(phase2_rgb[1] * (1 - progress))
            b = int(phase2_rgb[2] * (1 - progress))
            transition_color = f"rgb({r},{g},{b})"
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, right_paths_full,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color=None,
                show_arrow1=True, arrow1_x=arrow1_x,
                show_arrow2=True, arrow2_x=arrow2_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption,
                ns_uri=ns_uri
            )
            
            # Make phase 0+1 paths in right black, phase 2 paths use transition color
            for g in composite_svg:
                tag = g.tag
                if ns_uri and tag.startswith('{'):
                    tag = tag[len('{' + ns_uri + '}'):]
                if tag == 'g' and 'transform' in g.attrib and f'translate({phase2_x}' in g.attrib['transform']:
                    path_idx_in_right = 0
                    for path in g:
                        if path_idx_in_right < len(center_paths_full):
                            path.set('stroke', 'rgb(0,0,0)')
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', 'stroke:rgb(0,0,0)', style)
                                path.set('style', style)
                        else:
                            path.set('stroke', transition_color)
                            style = path.get('style', '')
                            if 'stroke:' in style:
                                style = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{transition_color}', style)
                                path.set('style', style)
                        path_idx_in_right += 1
                    break
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 11: Show p3 caption (fade in)
        print("\nStep 11: Showing p3 caption (fade in)...")
        for t in range(caption_fade_frames + 1):
            caption_opacity = t / caption_fade_frames
            
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, right_paths_full,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                show_arrow2=True, arrow2_x=arrow2_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption, right_caption=p3_caption,
                right_caption_opacity=caption_opacity,
                ns_uri=ns_uri
            )
            
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        # Step 12: Hold all phases (black) with all captions
        print("\nStep 12: Holding all phases with captions...")
        for _ in range(hold_frames):
            composite_svg = create_3phase_composite_svg(
                phase0_paths, center_paths_full, right_paths_full,
                phase0_x, phase1_x, phase2_x,
                canvas_width, canvas_height,
                left_color="rgb(0,0,0)", center_color="rgb(0,0,0)", right_color="rgb(0,0,0)",
                show_arrow1=True, arrow1_x=arrow1_x,
                show_arrow2=True, arrow2_x=arrow2_x,
                arrow_color="rgb(100,100,100)", arrow1_opacity=1.0, arrow2_opacity=1.0,
                left_caption=p1_caption, center_caption=p2_caption, right_caption=p3_caption,
                ns_uri=ns_uri
            )
            composite_path = os.path.join(temp_dir, f'composite_{frame_idx:04d}.svg')
            ET.ElementTree(composite_svg).write(composite_path, encoding='utf-8', xml_declaration=True)
            
            composite_png = os.path.join(temp_dir, f'composite_{frame_idx:04d}.png')
            if convert_svg_to_png(composite_path, composite_png, int(canvas_width), int(canvas_height)):
                img = Image.open(composite_png)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                frames.append(img)
                frame_idx += 1
        
        print(f"\nGenerated {len(frames)} frames")
        
        # Save frames as video using ffmpeg
        print("\nCreating video from frames...")
        if not frames:
            print("Error: No frames generated")
            sys.exit(1)
        
        try:
            temp_frames_dir = os.path.join(temp_dir, 'video_frames')
            os.makedirs(temp_frames_dir, exist_ok=True)
            
            for idx, frame in enumerate(frames):
                frame_path = os.path.join(temp_frames_dir, f'frame_{idx:06d}.png')
                frame.save(frame_path)
            
            output_video_path = Path(output_video)
            output_video_path.parent.mkdir(parents=True, exist_ok=True)
            
            subprocess.run([
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_frames_dir, 'frame_%06d.png'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '18',
                str(output_video_path)
            ], check=True, capture_output=True)
            
            print(f"\nVideo saved to: {output_video_path}")
            print(f"Total duration: {len(frames) / fps:.2f} seconds")
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating video with ffmpeg: {e}")
            print(f"stdout: {e.stdout.decode() if e.stdout else ''}")
            print(f"stderr: {e.stderr.decode() if e.stderr else ''}")
            print("\nTrying to save as GIF instead...")
            
            gif_path = str(output_video_path.with_suffix('.gif'))
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=1000 // fps,
                loop=0
            )
            print(f"GIF saved to: {gif_path}")
        
        # Clean up temporary sorted SVG
        if Path(sorted_svg).exists():
            Path(sorted_svg).unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Generate video animation showing phase 1 -> phase 2 -> phase 3 progression",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python generate_3phase_video.py input.svg output.mp4 --p1 'Phase 1' --p2 'Phase 2' --p3 'Phase 3'"
    )
    
    parser.add_argument('input_svg', type=str, help='Input SVG file path')
    parser.add_argument('output_video', type=str, nargs='?', default=None,
                       help='Output video file path (default: <input_svg>_3phase_video.mp4)')
    parser.add_argument('--fps', type=int, default=30, help='Video FPS (default: 30)')
    parser.add_argument('--p1', type=str, default=None, help='Caption for phase 1 (phase 0)')
    parser.add_argument('--p2', type=str, default=None, help='Caption for phase 2 (phase 1)')
    parser.add_argument('--p3', type=str, default=None, help='Caption for phase 3 (phase 2)')
    
    args = parser.parse_args()
    
    input_svg = args.input_svg
    if not Path(input_svg).exists():
        print(f"Error: Input file does not exist: {input_svg}")
        sys.exit(1)
    
    if args.output_video:
        output_video = args.output_video
    else:
        output_video = str(Path(input_svg).parent / f"{Path(input_svg).stem}_3phase_video.mp4")
    
    generate_3phase_video(input_svg, output_video, args.fps, args.p1, args.p2, args.p3)


if __name__ == "__main__":
    main()

