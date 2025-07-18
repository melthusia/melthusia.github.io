#!/usr/bin/env python3
"""
Simple Text to HTML Compiler (preserves exact formatting with hyperlinks)
Usage: python md_compiler.py <source_file> <destination_file>
"""

import sys
import os
import re
from pathlib import Path

def create_html_template(content, title="Document"):
    """Wrap the content in a basic HTML template with monospace font."""
    # First, let's mark all markdown links to protect them
    # Replace [text](url) with a placeholder
    markdown_links = []
    
    def save_markdown_link(match):
        text = match.group(1)
        path = match.group(2)
        
        # If it's an external link (http/https), keep as is
        if path.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
            link_html = f'<a href="{path}" target="_blank">{text}</a>'
        else:
            # For internal links, add .html extension if not present
            if not path.endswith('.html'):
                path += '.html'
            
            # Make sure path doesn't start with /
            if path.startswith('/'):
                path = path[1:]
                
            link_html = f'<a href="{path}">{text}</a>'
        
        placeholder = f'§§MDLINK{len(markdown_links)}§§'
        markdown_links.append(link_html)
        return placeholder
    
    # Process markdown links first
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', save_markdown_link, content)
    
    # Now process literal URLs (but not those already in markdown)
    url_pattern = r'(https?://[^\s<>"\']+|ftp://[^\s<>"\']+|www\.[^\s<>"\']+|[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[^\s<>"\']*)?)'
    literal_links = []
    
    def save_literal_url(match):
        url = match.group(0)
        
        # Don't process if it's part of our placeholder
        if '§§MDLINK' in url:
            return url
            
        # Add http:// if missing
        href = url
        if not url.startswith(('http://', 'https://', 'ftp://')):
            if url.startswith('www.') or ('.' in url and '/' in url):
                href = 'http://' + url
            elif '.' in url and url.count('.') >= 1:
                href = 'http://' + url
            else:
                return url
        
        link_html = f'<a href="{href}" target="_blank">{url}</a>'
        placeholder = f'§§LINK{len(literal_links)}§§'
        literal_links.append(link_html)
        return placeholder
    
    content = re.sub(url_pattern, save_literal_url, content)
    
    # Now escape HTML special characters
    content = content.replace('&', '&amp;')
    content = content.replace('<', '&lt;')
    content = content.replace('>', '&gt;')
    
    # Restore all links
    for i, link in enumerate(markdown_links):
        content = content.replace(f'§§MDLINK{i}§§', link)
    
    for i, link in enumerate(literal_links):
        content = content.replace(f'§§LINK{i}§§', link)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: monospace;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            min-height: 100vh;
            background-color: white;
        }}
        .content {{
            font-size: 32px; /* Twice default size */
            width: 80ch; /* 80 characters width */
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.2; /* Terminal-like line spacing */
        }}
        a {{
            color: inherit; /* Use default text color */
            text-decoration: underline;
        }}
        a:hover {{
            background-color: #f0f0f0;
        }}
        /* Handle smaller screens */
        @media (max-width: 85ch) {{
            .content {{
                width: 100%;
                max-width: 80ch;
            }}
        }}
        /* Adjust font size for mobile */
        @media (max-width: 768px) {{
            .content {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body><div class="content">{content}</div></body>
</html>"""

def compile_file(src_path, dst_path, base_dir=None):
    """Convert text file to HTML preserving exact formatting."""
    # Make paths absolute
    src_path = Path(src_path).resolve()
    
    if base_dir:
        dst_path = Path(base_dir) / dst_path
    dst_path = Path(dst_path).resolve()
    
    # Check if source exists
    if not src_path.exists():
        print(f"Error: Source file '{src_path}' not found.")
        return False
    
    # Create destination directory if it doesn't exist
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read the source file
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Get title from filename
    title = src_path.stem
    
    # Create HTML with exact content
    html = create_html_template(content, title)
    
    # Write to destination
    try:
        with open(dst_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Compiled: {src_path} → {dst_path}")
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False

def compile_directory(src_dir, dst_dir, base_dir=None):
    """Recursively compile all .md files in a directory."""
    src_dir = Path(src_dir).resolve()
    
    if base_dir:
        dst_dir = Path(base_dir) / dst_dir
    dst_dir = Path(dst_dir).resolve()
    
    if not src_dir.exists():
        print(f"Error: Source directory '{src_dir}' not found.")
        return False
    
    # Find all markdown files
    md_files = list(src_dir.rglob('*.md')) + list(src_dir.rglob('*.markdown'))
    
    if not md_files:
        print(f"No markdown files found in '{src_dir}'")
        return False
    
    print(f"Found {len(md_files)} markdown file(s)")
    
    # Compile each file
    for src_file in md_files:
        # Calculate relative path from source directory
        rel_path = src_file.relative_to(src_dir)
        
        # Change extension to .html
        dst_file = dst_dir / rel_path.with_suffix('.html')
        
        compile_file(src_file, dst_file)
    
    return True

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python md_compiler.py <source> <destination> [base_dir]")
        print("\nExamples:")
        print("  python md_compiler.py file.md file.html")
        print("  python md_compiler.py file.md output/file.html /var/www")
        print("  python md_compiler.py src_dir/ dst_dir/")
        print("  python md_compiler.py docs/ public/docs/ /var/www")
        sys.exit(1)
    
    src = sys.argv[1]
    dst = sys.argv[2]
    base_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Check if source is a directory or file
    src_path = Path(src)
    
    if src_path.is_dir() or src.endswith('/'):
        # Directory mode
        success = compile_directory(src, dst, base_dir)
    else:
        # Single file mode
        success = compile_file(src, dst, base_dir)
    
    if success:
        print("Compilation complete!")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
