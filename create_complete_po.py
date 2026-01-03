#!/usr/bin/env python3
"""
Create Complete PO File Workflow

This script automates the complete workflow to create a PO file with both
English source text and Chinese translations from existing translation files.

Usage:
    python create_complete_po.py <chinese_json> <english_po> <output_po>

Example:
    python create_complete_po.py zh_Hans/swade-core-rules.swade-armor.json english-source.po complete-armor.po

Workflow:
1. Extract Chinese translations from JSON to PO format
2. Merge with English source PO file
3. Create final PO with English msgid and Chinese msgstr
"""

import sys
import subprocess
import tempfile
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        if result.returncode != 0:
            print(f"Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Error running command: {cmd}")
        print(f"Exception: {e}")
        return False


def create_complete_po(chinese_json, english_po, output_po):
    """Create a complete PO file with English source and Chinese translations."""
    
    # Validate input files
    chinese_json_path = Path(chinese_json)
    english_po_path = Path(english_po)
    
    if not chinese_json_path.exists():
        print(f"Error: Chinese JSON file '{chinese_json}' does not exist")
        return False
    
    if not english_po_path.exists():
        print(f"Error: English PO file '{english_po}' does not exist")
        return False
    
    # Create output directory
    output_path = Path(output_po)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temporary file for extracted Chinese PO
    with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False, encoding='utf-8') as temp_file:
        temp_po_path = temp_file.name
    
    try:
        print(f"Step 1: Extracting Chinese translations from '{chinese_json}'...")
        
        # Extract Chinese JSON to PO format
        extract_cmd = f'python -m automation.format_converter extract "{chinese_json}" --output "{temp_po_path}" --format po'
        if not run_command(extract_cmd, cwd=Path.cwd()):
            return False
        
        print(f"Step 2: Merging with English source file '{english_po}'...")
        
        # Merge extracted Chinese PO with English source PO
        merge_cmd = f'python merge_extracted_po.py "{temp_po_path}" "{english_po}" "{output_po}"'
        if not run_command(merge_cmd, cwd=Path.cwd()):
            return False
        
        print(f"✓ Successfully created complete PO file: {output_po}")
        return True
        
    finally:
        # Clean up temporary file
        try:
            Path(temp_po_path).unlink()
        except:
            pass


def main():
    if len(sys.argv) != 4:
        print("Usage: python create_complete_po.py <chinese_json> <english_po> <output_po>")
        print()
        print("Creates a complete PO file with English source text and Chinese translations.")
        print()
        print("Arguments:")
        print("  chinese_json  - Path to Chinese translation JSON file (e.g., zh_Hans/swade-core-rules.swade-armor.json)")
        print("  english_po    - Path to English source PO file (e.g., from generator)")
        print("  output_po     - Path for output complete PO file")
        print()
        print("Example:")
        print("  python create_complete_po.py zh_Hans/swade-core-rules.swade-armor.json english-armor.po complete-armor.po")
        sys.exit(1)
    
    chinese_json = sys.argv[1]
    english_po = sys.argv[2]
    output_po = sys.argv[3]
    
    if create_complete_po(chinese_json, english_po, output_po):
        print()
        print("Workflow completed successfully!")
        print(f"The complete PO file is ready at: {output_po}")
        print()
        print("This file contains:")
        print("- English source text in msgid fields")
        print("- Chinese translations in msgstr fields")
        print("- Proper PO format for translation tools")
    else:
        print("Workflow failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()