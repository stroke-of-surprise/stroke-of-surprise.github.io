#!/usr/bin/env python3
"""
Sort SVG strokes based on human drawing order principles.
1. Identify phases by color (in order of appearance)
2. Normalize colors to tab10 colormap (same as painter_params.py)
3. Sort strokes: phase order is preserved (phase0 before phase1, phase1 before phase2, etc.)
   Within each phase, sort by position (top to bottom, left to right)
"""

import xml.etree.ElementTree as ET
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
import subprocess


def extract_stroke_color(path_elem):
    """
    Extract stroke color from a path element.
    Checks both stroke attribute and style attribute.
    Returns normalized color string (rgb(...) format) or None.
    """
    # Check direct stroke attribute first
    stroke = path_elem.get('stroke', '')
    
    # Check style attribute if stroke not found
    if not stroke:
        style = path_elem.get('style', '')
        if style:
            # Try to extract stroke from style
            style_match = re.search(r'stroke:\s*rgb\([^)]+\)', style)
            if style_match:
                stroke = style_match.group(0).replace('stroke:', '').strip()
    
    # Normalize color string (remove spaces, handle rgb() format)
    if stroke and stroke.startswith('rgb('):
        color_normalized = re.sub(r'\s+', '', stroke)
        return color_normalized
    
    return None


def parse_rgb_color(stroke_attr: str) -> Tuple[int, int, int]:
    """
    Parse RGB color from stroke attribute.
    Returns (r, g, b) tuple.
    """
    if not stroke_attr:
        return (0, 0, 0)  # Default to black
    
    # Handle rgb(r, g, b) format
    rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', stroke_attr)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        return (r, g, b)
    
    return (0, 0, 0)


def extract_path_bounds(path_d: str) -> Tuple[float, float, float, float]:
    """
    Extract bounding box (min_x, min_y, max_x, max_y) from SVG path data.
    """
    # Extract all numbers from the path
    numbers = re.findall(r'-?\d+\.?\d*', path_d)
    if not numbers:
        return (0, 0, 0, 0)
    
    coords = [float(n) for n in numbers]
    
    # Group coordinates into (x, y) pairs
    points = []
    i = 0
    while i < len(coords) - 1:
        points.append((coords[i], coords[i + 1]))
        i += 2
    
    if not points:
        return (0, 0, 0, 0)
    
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    
    return (min_x, min_y, max_x, max_y)


def calculate_path_length(path_d: str) -> float:
    """
    Approximate path length by calculating distance between consecutive points.
    """
    # Extract all numbers from the path
    numbers = re.findall(r'-?\d+\.?\d*', path_d)
    if not numbers:
        return 0.0
    
    coords = [float(n) for n in numbers]
    
    # Group coordinates into (x, y) pairs
    points = []
    i = 0
    while i < len(coords) - 1:
        points.append((coords[i], coords[i + 1]))
        i += 2
    
    if len(points) < 2:
        return 0.0
    
    # Calculate cumulative distance
    total_length = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total_length += (dx * dx + dy * dy) ** 0.5
    
    return total_length


def sort_strokes_by_phase_order(paths: List[ET.Element], color_to_phase: Dict[str, int], phase_to_color: Dict[int, str]) -> List[ET.Element]:
    """
    Sort strokes based on phase order (preserved) and human drawing order within each phase.
    
    Args:
        paths: List of path elements
        color_to_phase: Dictionary mapping color string to phase index
        phase_to_color: Dictionary mapping phase index to new color (tab10)
    
    Returns:
        Sorted list of path elements
    """
    # Extract information for each path
    path_info = []
    
    for idx, path in enumerate(paths):
        path_d = path.get('d', '')
        stroke_color = extract_stroke_color(path)
        
        # Get phase index for this path
        phase_idx = color_to_phase.get(stroke_color, 999)  # 999 for unknown colors (put last)
        
        # Calculate metrics for sorting within phase
        min_x, min_y, max_x, max_y = extract_path_bounds(path_d)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        path_length = calculate_path_length(path_d)
        
        path_info.append({
            'index': idx,
            'path': path,
            'phase_idx': phase_idx,
            'center_x': center_x,
            'center_y': center_y,
            'path_length': path_length,
            'min_y': min_y  # Use min_y for top-to-bottom sorting
        })
    
    # Sort: phase order first (phase0 < phase1 < phase2 < ...), then within phase by position
    def sort_key(info):
        # Primary: phase index (preserve phase order)
        phase_idx = info['phase_idx']
        # Secondary: Y position (top to bottom)
        y_pos = info['min_y']
        # Tertiary: X position (left to right)
        x_pos = info['center_x']
        # Quaternary: path length (larger first, so negative)
        length = -info['path_length']
        
        return (phase_idx, y_pos, x_pos, length)
    
    sorted_info = sorted(path_info, key=sort_key)
    
    return [info['path'] for info in sorted_info]


def sort_svg_file(input_svg: str, output_svg: str):
    """
    Sort strokes in SVG file:
    1. Identify phases by color
    2. Normalize colors to tab10 colormap
    3. Sort by phase order (preserved) and position within phase
    4. Save to output
    
    Returns:
        (success: bool, num_phases: int, phase_to_color: Dict[int, str], ns_uri: str)
    """
    # Parse SVG
    tree = ET.parse(input_svg)
    root = tree.getroot()
    
    # Handle namespace
    ns_uri = None
    if root.tag.startswith('{'):
        ns_uri = root.tag[1:root.tag.index('}')]
        ET.register_namespace('', ns_uri)
    
    # Get tab10 colormap (same as painter_params.py line 706)
    cmap = plt.colormaps.get_cmap('tab10')
    
    # First pass: identify all unique colors (phases) in order of appearance
    colors_seen = set()
    colors_order = []
    
    for path in root.iter():
        tag = path.tag
        if ns_uri and tag.startswith('{'):
            tag = tag[len('{' + ns_uri + '}'):]
        
        if tag == 'path':
            color = extract_stroke_color(path)
            if color and color not in colors_seen:
                colors_seen.add(color)
                colors_order.append(color)
    
    num_phases = len(colors_order)
    
    if num_phases == 0:
        print(f"Warning: No colors found in {input_svg}")
        return (False, 0, {}, ns_uri)
    
    if num_phases > 10:
        print(f"Warning: More than 10 phases ({num_phases}) found, only first 10 will use tab10 colors")
        num_phases = 10
    
    print(f"Found {len(colors_order)} unique colors (phases)")
    
    # Create color mappings: old_color -> phase_idx, phase_idx -> new_color (tab10)
    color_to_phase = {}
    phase_to_color = {}
    
    for phase_idx, old_color in enumerate(colors_order[:10]):
        color_to_phase[old_color] = phase_idx
        
        # Get tab10 color (RGBA in 0-1 range)
        rgba = cmap.colors[phase_idx]
        # Convert to RGB in 0-255 range
        r = int(rgba[0] * 255)
        g = int(rgba[1] * 255)
        b = int(rgba[2] * 255)
        new_color = f"rgb({r},{g},{b})"
        phase_to_color[phase_idx] = new_color
        print(f"Phase {phase_idx}: {old_color} -> {new_color}")
    
    # Find the group element containing paths
    g_element = None
    for elem in root.iter():
        tag = elem.tag
        if ns_uri and tag.startswith('{'):
            tag = tag[len('{' + ns_uri + '}'):]
        
        if tag == 'g' and elem != root:
            g_element = elem
            break
    
    # Extract paths
    if g_element is None:
        # If no group found, look for paths directly under root
        paths = []
        for elem in root.iter():
            tag = elem.tag
            if ns_uri and tag.startswith('{'):
                tag = tag[len('{' + ns_uri + '}'):]
            if tag == 'path':
                paths.append(elem)
    else:
        # Extract paths from group
        paths = []
        for elem in list(g_element):
            tag = elem.tag
            if ns_uri and tag.startswith('{'):
                tag = tag[len('{' + ns_uri + '}'):]
            if tag == 'path':
                paths.append(elem)
    
        if not paths:
            print(f"Error: No paths found in {input_svg}")
            return (False, num_phases, phase_to_color, ns_uri)
    
    # Sort paths by phase order and position
    sorted_paths = sort_strokes_by_phase_order(paths, color_to_phase, phase_to_color)
    
    # Update colors to tab10 and replace paths
    for path in sorted_paths:
        old_color = extract_stroke_color(path)
        phase_idx = color_to_phase.get(old_color, 0)
        new_color = phase_to_color.get(phase_idx, phase_to_color[0])
        
        # Update stroke color
        path.set('stroke', new_color)
        # Also handle style attribute if present
        style = path.get('style', '')
        if style and 'stroke:' in style:
            style = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{new_color}', style)
            path.set('style', style)
    
    # Replace paths in SVG
    if g_element is None:
        # Remove old paths and add sorted ones
        for path in paths:
            root.remove(path)
        for path in sorted_paths:
            root.append(path)
    else:
        # Remove old paths from group
        for path in paths:
            g_element.remove(path)
        # Add sorted paths to group
        for path in sorted_paths:
            g_element.append(path)
    
    # Pretty print and save
    ET.indent(tree, space="  ")
    tree.write(output_svg, encoding='utf-8', xml_declaration=True)
    
    print(f"\nSorted SVG saved to: {output_svg}")
    print(f"Total strokes: {len(sorted_paths)}")
    
    # Count strokes per phase
    for phase_idx in range(min(num_phases, len(colors_order))):
        phase_color = phase_to_color[phase_idx]
        count = sum(1 for p in sorted_paths if extract_stroke_color(p) == phase_color)
        print(f"Phase {phase_idx}: {count} strokes")
    
    return (True, num_phases, phase_to_color, ns_uri)


def generate_animations(svg_file: str, output_dir: Path):
    """
    Generate both SVG and GIF animations from an SVG file.
    
    Args:
        svg_file: Path to input SVG file
        output_dir: Output directory
    """
    try:
        # Generate animated SVG
        result = subprocess.run(
            ['python', 'svg2anim.py', svg_file, '--format', 'svg', '--output-dir', str(output_dir)],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Generate animated GIF
        result = subprocess.run(
            ['python', 'svg2anim.py', svg_file, '--format', 'gif', '--output-dir', str(output_dir)],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating animations: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def extract_phase_svg(input_svg: str, phase_idx: int, phase_color: str, output_svg: str, ns_uri: str = None, black: bool = False) -> bool:
    """
    Extract paths of a specific phase from sorted SVG file.
    
    Args:
        input_svg: Path to sorted SVG file
        phase_idx: Phase index (0, 1, 2, ...)
        phase_color: Color string for this phase (tab10 color)
        output_svg: Path to output SVG file
        ns_uri: SVG namespace URI (if any)
        black: If True, set all stroke colors to black
    
    Returns:
        True if successful, False otherwise
    """
    # Parse SVG
    tree = ET.parse(input_svg)
    root = tree.getroot()
    
    # Find paths with the target phase color
    paths = []
    for path in root.iter():
        tag = path.tag
        if ns_uri and tag.startswith('{'):
            tag = tag[len('{' + ns_uri + '}'):]
        
        if tag == 'path':
            color = extract_stroke_color(path)
            if color == phase_color:
                paths.append(path)
    
    if not paths:
        print(f"Warning: No paths found for phase {phase_idx}")
        return False
    
    # Create new SVG structure
    if ns_uri:
        new_root = ET.Element(f"{{{ns_uri}}}svg")
    else:
        new_root = ET.Element("svg")
    
    # Copy attributes from original root
    for attr, value in root.attrib.items():
        new_root.set(attr, value)
    
    # Create defs and g elements
    if ns_uri is None:
        defs = ET.SubElement(new_root, "defs")
        g = ET.SubElement(new_root, "g")
    else:
        defs = ET.SubElement(new_root, f"{{{ns_uri}}}defs")
        g = ET.SubElement(new_root, f"{{{ns_uri}}}g")
    
    # Add paths to group (maintain order from input)
    black_color = "rgb(0,0,0)"
    for path in paths:
        # Create new path element
        path_tag = 'path' if ns_uri is None else f"{{{ns_uri}}}path"
        new_path = ET.SubElement(g, path_tag)
        
        # Copy all attributes
        for attr, value in path.attrib.items():
            if black and attr == 'stroke':
                # Set stroke color to black
                new_path.set(attr, black_color)
            elif black and attr == 'style' and 'stroke:' in value:
                # Replace stroke color in style attribute
                style_value = re.sub(r'stroke:\s*rgb\([^)]+\)', f'stroke:{black_color}', value)
                new_path.set(attr, style_value)
            else:
                new_path.set(attr, value)
        
        # If black is True and stroke attribute doesn't exist, add it
        if black and not new_path.get('stroke') and not ('stroke:' in new_path.get('style', '')):
            new_path.set('stroke', black_color)
    
    # Pretty print and save
    new_tree = ET.ElementTree(new_root)
    ET.indent(new_tree, space="  ")
    new_tree.write(output_svg, encoding='utf-8', xml_declaration=True)
    
    color_desc = "black" if black else "colored"
    print(f"Created phase {phase_idx} SVG ({color_desc}): {output_svg} ({len(paths)} strokes)")
    return True


def main():
    """Main function with ArgumentParser."""
    parser = argparse.ArgumentParser(
        description="Sort SVG strokes by phase order and human drawing order. "
                    "Identifies phases by color, normalizes to tab10 colormap, "
                    "and generates animations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sort SVG with default output name
  python sort_svg_strokes.py input.svg
  
  # Sort SVG with custom output name
  python sort_svg_strokes.py input.svg output.svg
  
  # Sort SVG without generating animations
  python sort_svg_strokes.py input.svg --no-animations
        """
    )
    
    parser.add_argument(
        'input_svg',
        type=str,
        help='Input SVG file path'
    )
    
    parser.add_argument(
        'output_svg',
        type=str,
        nargs='?',
        default=None,
        help='Output SVG file path (default: <input_svg>_sorted.svg)'
    )
    
    parser.add_argument(
        '--no-animations',
        action='store_true',
        help='Skip generating animations (only sort and normalize colors)'
    )
    
    parser.add_argument(
        '--black',
        action='store_true',
        help='Generate black versions of phase animations (all strokes in black)'
    )
    
    args = parser.parse_args()
    
    input_svg = args.input_svg
    
    # Determine output file name
    if args.output_svg:
        output_svg = args.output_svg
    else:
        input_path = Path(input_svg)
        output_svg = str(input_path.parent / f"{input_path.stem}_sorted.svg")
    
    if not Path(input_svg).exists():
        print(f"Error: Input file does not exist: {input_svg}")
        sys.exit(1)
    
    success, num_phases, phase_to_color, ns_uri = sort_svg_file(input_svg, output_svg)
    
    if not success:
        sys.exit(1)
    
    print(f"\nSuccessfully sorted SVG strokes!")
    print(f"Input:  {input_svg}")
    print(f"Output: {output_svg}")
    
    # Generate animations (unless --no-animations is specified)
    if not args.no_animations:
        print("\n" + "=" * 60)
        print("Generating animations...")
        print("=" * 60)
        output_dir = Path(output_svg).parent
        
        # Generate animation for the complete sorted SVG
        generate_animations(output_svg, output_dir)
        
        # Generate animations for each phase separately
        if num_phases > 0:
            print("\n" + "=" * 60)
            print("Generating animations for each phase...")
            print("=" * 60)
            
            # Create temporary directory for phase-specific SVGs
            temp_dir = output_dir / "temp_phase_svgs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = Path(output_svg).stem
            
            # Extract and generate animations for each phase
            for phase_idx in range(num_phases):
                phase_color = phase_to_color[phase_idx]
                
                # Generate colored version
                phase_svg = temp_dir / f"{base_name}_phase{phase_idx}.svg"
                if extract_phase_svg(output_svg, phase_idx, phase_color, str(phase_svg), ns_uri, black=False):
                    print(f"\nGenerating animations for phase {phase_idx} (colored)...")
                    generate_animations(str(phase_svg), output_dir)
                
                # Generate black version if --black flag is set
                if args.black:
                    phase_svg_black = temp_dir / f"{base_name}_phase{phase_idx}_black.svg"
                    if extract_phase_svg(output_svg, phase_idx, phase_color, str(phase_svg_black), ns_uri, black=True):
                        print(f"\nGenerating animations for phase {phase_idx} (black)...")
                        generate_animations(str(phase_svg_black), output_dir)
            
            # Clean up temporary files (optional)
            # import shutil
            # shutil.rmtree(temp_dir)
    else:
        print("\nAnimations generation skipped (--no-animations flag set)")


if __name__ == "__main__":
    main()
