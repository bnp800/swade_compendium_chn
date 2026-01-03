#!/usr/bin/env python3
"""
Merge Extracted PO Files

This script merges PO files where:
- Source file: Contains Chinese translations in msgid (extracted from zh_Hans JSON)
- Target file: Contains English source text in msgid (from generator)

The result will have English in msgid and Chinese in msgstr.

Usage:
    python merge_extracted_po.py chinese_extracted.po english_source.po output.po
"""

import re
import sys
from pathlib import Path


def parse_po_entry(lines, start_idx):
    """Parse a single PO entry starting from the given line index."""
    entry = {
        'comments': [],
        'msgctxt': '',
        'msgid': '',
        'msgstr': '',
        'raw_lines': []
    }
    
    i = start_idx
    while i < len(lines):
        line = lines[i].rstrip()
        entry['raw_lines'].append(line)
        
        if line.startswith('#'):
            entry['comments'].append(line)
        elif line.startswith('msgctxt'):
            # Extract msgctxt value
            match = re.match(r'msgctxt\s+"([^"]*)"', line)
            if match:
                entry['msgctxt'] = match.group(1)
        elif line.startswith('msgid'):
            # Extract msgid value, handle multiline
            match = re.match(r'msgid\s+"([^"]*)"', line)
            if match:
                entry['msgid'] = match.group(1)
            # Check for continuation lines
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('"'):
                cont_match = re.match(r'\s*"([^"]*)"', lines[j])
                if cont_match:
                    content = cont_match.group(1)
                    if content.endswith('\\n'):
                        entry['msgid'] += content[:-2] + '\n'
                    else:
                        entry['msgid'] += content
                    entry['raw_lines'].append(lines[j].rstrip())
                j += 1
            i = j - 1
        elif line.startswith('msgstr'):
            # Extract msgstr value, handle multiline
            match = re.match(r'msgstr\s+"([^"]*)"', line)
            if match:
                entry['msgstr'] = match.group(1)
            # Check for continuation lines
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('"'):
                cont_match = re.match(r'\s*"([^"]*)"', lines[j])
                if cont_match:
                    content = cont_match.group(1)
                    if content.endswith('\\n'):
                        entry['msgstr'] += content[:-2] + '\n'
                    else:
                        entry['msgstr'] += content
                    entry['raw_lines'].append(lines[j].rstrip())
                j += 1
            i = j - 1
        elif line == '':
            # End of entry
            break
        
        i += 1
    
    return entry, i


def parse_po_file(filepath):
    """Parse a PO file and return a dictionary of entries keyed by msgctxt."""
    entries = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Handle header
    header_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith('#') or line.startswith('msgid ""') or line.startswith('msgstr ""'):
            header_lines.append(line)
            if line.startswith('msgstr ""'):
                # Skip the header msgstr content
                i += 1
                while i < len(lines) and lines[i].strip().startswith('"'):
                    header_lines.append(lines[i].rstrip())
                    i += 1
                break
        i += 1
    
    # Parse entries
    while i < len(lines):
        if lines[i].strip() == '':
            i += 1
            continue
        
        if lines[i].startswith('#:'):
            entry, next_i = parse_po_entry(lines, i)
            if entry['msgctxt']:
                entries[entry['msgctxt']] = entry
            i = next_i + 1
        else:
            i += 1
    
    return header_lines, entries


def escape_po_string(text):
    """Escape special characters for PO format."""
    if not text:
        return ""
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\t', '\\t')
    return text


def merge_extracted_po_files(chinese_file, english_file, output_file):
    """Merge extracted Chinese PO with English source PO."""
    
    print(f"Parsing Chinese file: {chinese_file}")
    chinese_header, chinese_entries = parse_po_file(chinese_file)
    
    print(f"Parsing English file: {english_file}")
    english_header, english_entries = parse_po_file(english_file)
    
    print(f"Chinese entries: {len(chinese_entries)}")
    print(f"English entries: {len(english_entries)}")
    
    # Create merged content
    merged_lines = []
    
    # Use Chinese header (but could use either)
    merged_lines.extend(chinese_header)
    merged_lines.append('')
    
    # Process all entries from English file (which has the complete structure)
    matched_count = 0
    for msgctxt, english_entry in english_entries.items():
        # Add comments from English file
        for comment in english_entry['comments']:
            merged_lines.append(comment)
        
        # Add msgctxt
        merged_lines.append(f'msgctxt "{escape_po_string(msgctxt)}"')
        
        # Add msgid (English source text)
        if '\n' in english_entry['msgid']:
            merged_lines.append('msgid ""')
            for line in english_entry['msgid'].split('\n'):
                merged_lines.append(f'"{escape_po_string(line)}\\n"')
        else:
            merged_lines.append(f'msgid "{escape_po_string(english_entry["msgid"])}"')
        
        # Add msgstr (Chinese translation from Chinese file)
        if msgctxt in chinese_entries and chinese_entries[msgctxt]['msgid']:
            # The Chinese translation is in the msgid field of the Chinese file
            chinese_text = chinese_entries[msgctxt]['msgid']
            if '\n' in chinese_text:
                merged_lines.append('msgstr ""')
                for line in chinese_text.split('\n'):
                    merged_lines.append(f'"{escape_po_string(line)}\\n"')
            else:
                merged_lines.append(f'msgstr "{escape_po_string(chinese_text)}"')
            matched_count += 1
        else:
            merged_lines.append('msgstr ""')
        
        merged_lines.append('')
    
    # Write merged file
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in merged_lines:
            f.write(line + '\n')
    
    print(f"Merged file written to: {output_file}")
    print(f"Total entries processed: {len(english_entries)}")
    print(f"Entries with translations: {matched_count}")
    print(f"Translation coverage: {matched_count/len(english_entries)*100:.1f}%")


def main():
    if len(sys.argv) != 4:
        print("Usage: python merge_extracted_po.py chinese_extracted.po english_source.po output.po")
        print()
        print("Merges PO files where:")
        print("- Chinese file: Contains Chinese translations in msgid (from format converter)")
        print("- English file: Contains English source text in msgid (from generator)")
        print("- Output: English msgid + Chinese msgstr")
        sys.exit(1)
    
    chinese_file = sys.argv[1]
    english_file = sys.argv[2]
    output_file = sys.argv[3]
    
    # Validate input files
    for file_path in [chinese_file, english_file]:
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' does not exist")
            sys.exit(1)
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        merge_extracted_po_files(chinese_file, english_file, output_file)
        print("✓ Successfully merged PO files")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()