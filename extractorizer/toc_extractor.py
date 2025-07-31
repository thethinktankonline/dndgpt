#!/usr/bin/env python3
"""
Simple TOC Extractor - Test script for extracting table of contents from PDF files
"""

import os
import fitz  # PyMuPDF
import argparse
from pathlib import Path

# Configuration
DEBUG = True

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def extract_and_display_toc(pdf_path, chapter_level=1):
    """Extract and display the table of contents from a PDF
    
    Args:
        pdf_path: Path to the PDF file
        chapter_level: TOC level to use for chapter breaks (1=top level, 2=second level, etc.)
    """
    
    print(f"\n📖 Analyzing PDF: {pdf_path}")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File '{pdf_path}' not found.")
        return None
    
    try:
        # Open the PDF
        debug_print("Opening PDF document...")
        doc = fitz.open(pdf_path)
        
        # Basic document info
        print(f"📄 Document Info:")
        print(f"   Title: {doc.metadata.get('title', 'N/A')}")
        print(f"   Author: {doc.metadata.get('author', 'N/A')}")
        print(f"   Pages: {doc.page_count}")
        print(f"   Created: {doc.metadata.get('creationDate', 'N/A')}")
        
        # Extract TOC
        debug_print("Extracting table of contents...")
        toc = doc.get_toc(simple=False)
        
        if not toc:
            print("\n⚠️  No table of contents found in this PDF")
            print("   The document may not have bookmarks or TOC entries")
            doc.close()
            return []
        
        print(f"\n📚 Table of Contents ({len(toc)} entries):")
        print(f"   Using level {chapter_level} entries as chapter breaks")
        print("-" * 60)
        
        # Display TOC entries (limited to avoid overwhelming output)
        chapters = []
        level_counts = {}
        
        # Count entries by level and collect potential chapters
        for idx, entry in enumerate(toc):
            if len(entry) >= 3:
                level, title, page = entry[0], entry[1], entry[2]
                
                # Count by level
                level_counts[level] = level_counts.get(level, 0) + 1
                
                # Show first 20 entries for overview
                if idx < 20:
                    indent = "  " * (level - 1)
                    level_marker = "📖" if level == 1 else "📝" if level == 2 else "•" if level == 3 else "◦"
                    print(f"{indent}{level_marker} {title} (Page {page})")
                elif idx == 20:
                    print("   ... (showing first 20 entries)")
                
                # Collect chapters at the specified level
                if level == chapter_level:
                    chapters.append((level, title, page))
                
                debug_print(f"Entry {idx}: Level={level}, Title='{title}', Page={page}")
        
        # Display level summary
        print(f"\n📊 TOC Level Summary:")
        for level in sorted(level_counts.keys()):
            print(f"   Level {level}: {level_counts[level]} entries")
        
        print(f"\n📋 Found {len(chapters)} chapters at level {chapter_level}:")
        print("-" * 60)
        
        # Show chapter ranges
        if chapters:
            base_filename = Path(pdf_path).stem.lower().replace(' ', '_').replace('-', '_')
            
            for idx, (level, title, start_page) in enumerate(chapters):
                # Calculate end page
                end_page = doc.page_count
                if idx + 1 < len(chapters):
                    _, _, next_start = chapters[idx + 1]
                    end_page = next_start - 1
                
                page_count = end_page - start_page + 1
                sanitized_name = sanitize_filename(title)
                
                print(f"   Chapter {idx+1:2d}: {title}")
                print(f"              Pages {start_page:3d}-{end_page:3d} ({page_count:3d} pages)")
                print(f"              Filename: {base_filename}_{sanitized_name}")
                print()
        else:
            print(f"   No chapters found at level {chapter_level}")
            print(f"   Try using --level 2 for level 2 entries")
        
        doc.close()
        return chapters
        
    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        return None

def sanitize_filename(name):
    """Clean filename for safe file system usage"""
    import re
    safe = re.sub(r"[^0-9a-zA-Z _-]", "", name)
    safe = safe.strip().replace(' ', '_').lower()
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')

def main():
    parser = argparse.ArgumentParser(
        description='Extract and display table of contents from PDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python toc_extractor.py srd/SRD_CC_v5.2.1.pdf
  python toc_extractor.py srd/SRD_CC_v5.2.1.pdf --level 2
  python toc_extractor.py ../documents/manual.pdf --quiet
        """
    )
    
    parser.add_argument(
        'input_pdf',
        help='Path to the PDF file to analyze'
    )
    parser.add_argument(
        '--level', '-l',
        type=int,
        default=1,
        help='TOC level to use for chapter breaks (default: 1)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Disable debug output'
    )
    
    args = parser.parse_args()
    
    # Set debug level
    global DEBUG
    DEBUG = not args.quiet
    
    # Extract and display TOC
    chapters = extract_and_display_toc(args.input_pdf, args.level)
    
    if chapters is None:
        return 1
    elif len(chapters) == 0:
        print(f"\n⚠️  No chapters found at level {args.level}")
        print("   Try using a different --level value")
        return 0
    else:
        print(f"\n✅ Successfully analyzed {len(chapters)} chapters at level {args.level}")
        return 0

if __name__ == '__main__':
    exit(main())
