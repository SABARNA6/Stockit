#!/usr/bin/env python3
"""
Zip project files while excluding unnecessary directories.
"""

import os
import zipfile
from pathlib import Path

# Directories and files to exclude
EXCLUDE_PATTERNS = {
    # Python
    'venv',
    '__pycache__',
    '.pytest_cache',
    '*.egg-info',
    'dist',
    'build',
    
    # Node
    'node_modules',
    
    # Version control
    '.git',
    '.github',
    
    # IDE/Editor
    '.vscode',
    '.idea',
    '*.swp',
    '*.swo',
    '.DS_Store',
    
    # Environment
    '.env',
    '.env.local',
    
    # Docker
    '.dockerignore',
    
    # OS
    'Thumbs.db',
}

def should_exclude(path, name):
    """Check if a path should be excluded."""
    # Check exact matches
    if name in EXCLUDE_PATTERNS:
        return True
    
    # Check pattern matches
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*') and name.endswith(pattern[1:]):
            return True
        if pattern.endswith('*') and name.startswith(pattern[:-1]):
            return True
    
    # Exclude __pycache__ at any level
    if name == '__pycache__':
        return True
    
    return False

def zip_project(project_path='.', output_file='project.zip'):
    """Zip project excluding specified directories."""
    project_path = Path(project_path).resolve()
    output_file = Path(output_file)
    
    print(f"📦 Creating zip: {output_file}")
    print(f"📁 Source: {project_path}")
    print(f"⏭️  Excluding: {', '.join(sorted(EXCLUDE_PATTERNS))}\n")
    
    file_count = 0
    total_size = 0
    
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_path):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(root, d)]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip excluded files
                if should_exclude(root, file):
                    continue
                
                try:
                    # Calculate relative path for archive
                    arcname = file_path.relative_to(project_path)
                    zipf.write(file_path, arcname)
                    
                    file_count += 1
                    total_size += file_path.stat().st_size
                    
                    # Print progress every 50 files
                    if file_count % 50 == 0:
                        print(f"  ✓ Added {file_count} files ({total_size / 1024 / 1024:.1f}MB)")
                
                except Exception as e:
                    print(f"  ⚠️  Error adding {file_path}: {e}")
    
    zip_size = output_file.stat().st_size
    print(f"\n✅ Done!")
    print(f"   Files: {file_count}")
    print(f"   Original: {total_size / 1024 / 1024:.1f}MB")
    print(f"   Compressed: {zip_size / 1024 / 1024:.1f}MB")
    print(f"   Ratio: {(1 - zip_size/total_size)*100:.1f}% saved")

if __name__ == '__main__':
    import sys
    
    # Use command-line arguments if provided
    project_path = sys.argv[1] if len(sys.argv) > 1 else '.'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'project.zip'
    
    zip_project(project_path, output_file)
