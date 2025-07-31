#!/usr/bin/env python3
"""
PDF Document Splitter - Intelligent chapter extraction based on TOC analysis
Uses diagnostic analysis to recommend optimal extraction strategies
"""

import os
import fitz  # PyMuPDF
import argparse
import re
from pathlib import Path
from collections import defaultdict
import sys

# Import our diagnostic analyzer
try:
    from toc_diagnostic import TOCAnalyzer
except ImportError:
    print("❌ Error: toc_diagnostic.py not found. Make sure it's in the same directory.")
    sys.exit(1)

# Configuration
DEBUG = False

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

class DocumentSplitter:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.toc = self.doc.get_toc(simple=False)
        self.analyzer = TOCAnalyzer(pdf_path)
        
        # Validate document structure before proceeding
        self._validate_document_structure()
        
    def _validate_document_structure(self):
        """Validate that the document is properly structured for extraction"""
        
        print(f"🔍 Validating document structure...")
        
        # Check 1: Does the document have a TOC?
        if not self.toc:
            raise ValueError(
                "❌ Document Validation Failed: No table of contents found.\n"
                "   This tool requires PDFs with embedded bookmarks/TOC structure.\n"
                "   Please use documents that have been properly structured with headings."
            )
        
        # Check 2: Does the TOC have meaningful entries?
        if len(self.toc) < 2:
            raise ValueError(
                "❌ Document Validation Failed: Insufficient TOC entries.\n"
                f"   Found only {len(self.toc)} TOC entries. Need at least 2 for meaningful extraction.\n"
                "   This tool is designed for well-structured documents with multiple chapters/sections."
            )
        
        # Check 3: Are TOC entries properly formatted?
        valid_entries = 0
        for entry in self.toc:
            if len(entry) >= 3 and isinstance(entry[0], int) and isinstance(entry[2], int):
                valid_entries += 1
        
        if valid_entries < len(self.toc) * 0.8:  # At least 80% valid entries
            raise ValueError(
                "❌ Document Validation Failed: Malformed TOC structure.\n"
                f"   Only {valid_entries}/{len(self.toc)} TOC entries are properly formatted.\n"
                "   This suggests the document may not have proper heading structure."
            )
        
        # Check 4: Run diagnostic analysis for quality assessment
        try:
            analysis_data = self.analyzer.analyze_structure()
            if not analysis_data:
                raise ValueError(
                    "❌ Document Validation Failed: Could not analyze TOC structure.\n"
                    "   The document may have corrupted or invalid bookmark data."
                )
            
            # Check quality scores
            best_level_score = analysis_data['ranked_levels'][0][1] if analysis_data['ranked_levels'] else 0
            
            if best_level_score < 10:  # Very low intelligence score
                print(f"⚠️  Document Structure Warning:")
                print(f"   Low structure quality score: {best_level_score:.1f}/100")
                print(f"   This document may not be optimally structured for extraction.")
                print(f"   Consider using documents with clearer heading hierarchy.")
                
                # Ask user if they want to proceed anyway
                confirm = input(f"   Continue anyway? (y/N): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    raise ValueError("❌ Document validation cancelled by user.")
            
            # Check for reasonable page distribution
            total_entries = analysis_data['total_entries']
            total_pages = analysis_data['document_pages']
            
            if total_entries > total_pages:
                print(f"⚠️  Structure Warning: More TOC entries ({total_entries}) than pages ({total_pages})")
                print(f"   This may indicate overly granular bookmarking.")
            
            print(f"✅ Document structure validation passed!")
            print(f"   📋 {total_entries} TOC entries across {len(analysis_data['level_analysis'])} levels")
            print(f"   📊 Best extraction score: {best_level_score:.1f}/100")
            
        except Exception as e:
            raise ValueError(f"❌ Document Validation Failed: Error during structure analysis: {str(e)}")
        
    def get_chapters_at_level(self, level):
        """Extract chapters at a specific TOC level"""
        chapters = []
        
        if not self.toc:
            return chapters
        
        # Get entries at the specified level
        level_entries = []
        for entry in self.toc:
            if len(entry) >= 3 and entry[0] == level:
                level_entries.append((entry[1], entry[2]))  # title, page
        
        # Calculate page ranges
        for i, (title, start_page) in enumerate(level_entries):
            end_page = self.doc.page_count
            if i + 1 < len(level_entries):
                _, next_start = level_entries[i + 1]
                end_page = next_start - 1
            
            # Handle edge case: if start_page > end_page (same-page chapters)
            # Default to including the full page
            if start_page > end_page:
                end_page = start_page
                debug_print(f"Same-page chapter detected: '{title}' on page {start_page}")
            
            chapters.append({
                'title': title,
                'start_page': start_page,
                'end_page': end_page,
                'page_count': end_page - start_page + 1
            })
        
        return chapters
    
    def sanitize_filename(self, name):
        """Clean filename for safe file system usage"""
        safe = re.sub(r"[^0-9a-zA-Z _-]", "", name)
        safe = safe.strip().replace(' ', '_').lower()
        safe = re.sub(r'_+', '_', safe)
        return safe.strip('_')
    
    def split_to_pdf(self, chapters, output_dir, prefix):
        """Split document into PDF chapters"""
        print(f"\n📄 Creating PDF chapters...")
        
        for i, chapter in enumerate(chapters, 1):
            # Create filename with numerical prefix for order
            sanitized_title = self.sanitize_filename(chapter['title'])
            filename = f"{prefix}_{i:02d}_{sanitized_title}.pdf"
            output_path = os.path.join(output_dir, filename)
            
            print(f"   📖 Chapter {i:2d}: {chapter['title']}")
            print(f"        Pages {chapter['start_page']:3d}-{chapter['end_page']:3d} → {filename}")
            
            # Validate page range
            start_page = max(1, chapter['start_page'])
            end_page = min(self.doc.page_count, chapter['end_page'])
            
            if start_page > end_page:
                print(f"        ⚠️  Warning: Invalid page range, skipping chapter")
                continue
            
            # Create new PDF with the chapter pages
            new_pdf = fitz.open()
            pages_added = 0
            
            for page_num in range(start_page - 1, end_page):
                if page_num < self.doc.page_count:
                    new_pdf.insert_pdf(self.doc, from_page=page_num, to_page=page_num)
                    pages_added += 1
            
            # Only save if we actually added pages
            if pages_added > 0:
                new_pdf.save(output_path)
                debug_print(f"        ✅ Saved {pages_added} pages to {filename}")
            else:
                print(f"        ⚠️  Warning: No pages to save for {filename}")
            
            new_pdf.close()
        
        print(f"✅ Created {len(chapters)} PDF chapters")
    
    def split_to_docx(self, chapters, output_dir, prefix):
        """Split document into DOCX chapters (placeholder for future Adobe integration)"""
        print(f"\n📝 DOCX extraction not yet implemented")
        print(f"   💡 Future enhancement: Use Adobe PDF Services for high-quality conversion")
        print(f"   📄 For now, use PDF output and convert manually if needed")
        print(f"   📝 Filenames would follow pattern: {prefix}_01_chapter_title.docx")
    
    def split_document(self, level, output_dir, prefix, output_formats):
        """Main document splitting function"""
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 Output directory: {output_dir}")
        
        # Get chapters at specified level
        chapters = self.get_chapters_at_level(level)
        
        if not chapters:
            print(f"❌ No chapters found at level {level}")
            return False
        
        print(f"\n📊 Extraction Summary:")
        print(f"   Level: {level}")
        print(f"   Chapters: {len(chapters)}")
        print(f"   Prefix: {prefix}")
        print(f"   Formats: {', '.join(output_formats)}")
        
        # Split into requested formats
        success = True
        
        if 'pdf' in output_formats:
            try:
                self.split_to_pdf(chapters, output_dir, prefix)
            except Exception as e:
                print(f"❌ Error creating PDF chapters: {e}")
                success = False
        
        if 'docx' in output_formats:
            try:
                self.split_to_docx(chapters, output_dir, prefix)
            except Exception as e:
                print(f"❌ Error creating DOCX chapters: {e}")
                success = False
        
        return success
    
    def close(self):
        """Close resources"""
        if hasattr(self, 'doc'):
            self.doc.close()
        if hasattr(self, 'analyzer'):
            self.analyzer.close()

def validate_document_structure(pdf_path):
    """Standalone function to validate document structure without creating a splitter"""
    
    print(f"🔍 Validating document: {Path(pdf_path).name}")
    
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc(simple=False)
        
        if not toc:
            print("❌ No table of contents found")
            return False
        
        if len(toc) < 2:
            print(f"❌ Insufficient TOC entries: {len(toc)}")
            return False
        
        analyzer = TOCAnalyzer(pdf_path)
        analysis_data = analyzer.analyze_structure()
        
        if not analysis_data:
            print("❌ Could not analyze TOC structure")
            return False
        
        best_score = analysis_data['ranked_levels'][0][1] if analysis_data['ranked_levels'] else 0
        
        print(f"✅ Document suitable for extraction!")
        print(f"   📋 {len(toc)} TOC entries")
        print(f"   📊 Quality score: {best_score:.1f}/100")
        print(f"   🎯 Recommended level: {analysis_data['ranked_levels'][0][0]}")
        
        doc.close()
        analyzer.close()
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return False

def interactive_extraction(pdf_path):
    """Interactive extraction with diagnostic guidance"""
    
    print(f"\n🔍 Analyzing document structure...")
    
    # Run diagnostic analysis
    analyzer = TOCAnalyzer(pdf_path)
    analysis_data = analyzer.analyze_structure()
    
    if not analysis_data:
        print("❌ No table of contents found. Cannot perform intelligent extraction.")
        return False
    
    # Show diagnostic summary
    print(f"\n📊 Document Analysis Results:")
    print(f"   📄 Document: {Path(pdf_path).name}")
    print(f"   📋 Pages: {analysis_data['document_pages']}")
    print(f"   🔖 TOC Entries: {analysis_data['total_entries']}")
    print(f"   📊 TOC Levels: {len(analysis_data['level_analysis'])}")
    
    # Show level recommendations
    print(f"\n💡 Recommended Extraction Levels:")
    for rank, (level, score) in enumerate(analysis_data['ranked_levels'][:3], 1):
        stats = analysis_data['level_analysis'][level]
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        print(f"   {medal} Level {level}: {stats['count']} chapters, avg {stats['avg_page_range']:.1f} pages (score: {score:.1f})")
    
    analyzer.close()
    
    # Get user choices
    print(f"\n🎯 Extraction Configuration:")
    
    # Choose level
    recommended_level = analysis_data['ranked_levels'][0][0]
    while True:
        level_input = input(f"   📊 Choose TOC level (recommended: {recommended_level}): ").strip()
        if not level_input:
            level = recommended_level
            break
        try:
            level = int(level_input)
            if level in analysis_data['level_analysis']:
                break
            else:
                print(f"   ❌ Level {level} not available. Available levels: {list(analysis_data['level_analysis'].keys())}")
        except ValueError:
            print("   ❌ Please enter a valid number")
    
    # Choose output directory
    default_output = os.path.join(os.path.dirname(pdf_path), "extracted_chapters")
    output_dir = input(f"   📁 Output directory (default: {default_output}): ").strip()
    if not output_dir:
        output_dir = default_output
    
    # Choose prefix
    default_prefix = Path(pdf_path).stem.lower().replace(' ', '_').replace('-', '_')
    prefix = input(f"   🏷️  Filename prefix (default: {default_prefix}): ").strip()
    if not prefix:
        prefix = default_prefix
    
    # Choose output formats
    print(f"   📄 Output formats:")
    print(f"      1. PDF only")
    print(f"      2. DOCX only (not yet implemented)")
    print(f"      3. Both PDF and DOCX")
    
    while True:
        format_choice = input(f"   Choose format (1-3, default: 1): ").strip()
        if not format_choice or format_choice == "1":
            output_formats = ['pdf']
            break
        elif format_choice == "2":
            output_formats = ['docx']
            break
        elif format_choice == "3":
            output_formats = ['pdf', 'docx']
            break
        else:
            print("   ❌ Please choose 1, 2, or 3")
    
    # Confirm extraction
    print(f"\n📋 Extraction Summary:")
    print(f"   📄 Document: {Path(pdf_path).name}")
    print(f"   📊 Level: {level} ({analysis_data['level_analysis'][level]['count']} chapters)")
    print(f"   📁 Output: {output_dir}")
    print(f"   🏷️  Prefix: {prefix}")
    print(f"   📄 Formats: {', '.join(output_formats)}")
    
    confirm = input(f"\n❓ Proceed with extraction? (Y/n): ").strip().lower()
    if confirm and confirm not in ['y', 'yes']:
        print("❌ Extraction cancelled")
        return False
    
    # Perform extraction
    print(f"\n🚀 Starting extraction...")
    splitter = DocumentSplitter(pdf_path)
    success = splitter.split_document(level, output_dir, prefix, output_formats)
    splitter.close()
    
    if success:
        print(f"\n🎉 Extraction completed successfully!")
        print(f"📁 Files saved to: {output_dir}")
    else:
        print(f"\n❌ Extraction completed with errors")
    
    return success

def main():
    parser = argparse.ArgumentParser(
        description='Intelligent PDF document splitter with diagnostic analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_splitter.py srd/SRD_CC_v5.2.1.pdf
  python pdf_splitter.py document.pdf --level 2 --output chapters/ --prefix doc
  python pdf_splitter.py report.pdf --batch --level 1 --format pdf
        """
    )
    
    parser.add_argument('input_pdf', help='Path to PDF file to split')
    parser.add_argument('--level', '-l', type=int, help='TOC level to use for splitting')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--prefix', '-p', help='Filename prefix for chapters')
    parser.add_argument('--format', '-f', choices=['pdf', 'docx', 'both'], 
                       default='pdf', help='Output format (default: pdf)')
    parser.add_argument('--batch', '-b', action='store_true', 
                       help='Batch mode (no interactive prompts)')
    parser.add_argument('--validate', '-v', action='store_true',
                       help='Only validate document structure (no extraction)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Set debug level
    global DEBUG
    DEBUG = args.debug
    
    if not os.path.exists(args.input_pdf):
        print(f"❌ Error: File '{args.input_pdf}' not found")
        return 1
    
    try:
        if args.validate:
            # Validation-only mode
            success = validate_document_structure(args.input_pdf)
            return 0 if success else 1
            
        elif args.batch:
            # Batch mode - use provided arguments or defaults
            if not args.level:
                print("❌ Error: --level required in batch mode")
                return 1
            
            output_dir = args.output or os.path.join(os.path.dirname(args.input_pdf), "extracted_chapters")
            prefix = args.prefix or Path(args.input_pdf).stem.lower().replace(' ', '_').replace('-', '_')
            
            output_formats = ['pdf', 'docx'] if args.format == 'both' else [args.format]
            
            splitter = DocumentSplitter(args.input_pdf)
            success = splitter.split_document(args.level, output_dir, prefix, output_formats)
            splitter.close()
            
            return 0 if success else 1
        else:
            # Interactive mode
            success = interactive_extraction(args.input_pdf)
            return 0 if success else 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
