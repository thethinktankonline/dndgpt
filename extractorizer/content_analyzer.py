#!/usr/bin/env python3
"""
Content Structure Analyzer - Analyze PDFs without TOC using content patterns
For documents that don't have embedded table of contents but have visual structural formatting
"""

import os
import fitz  # PyMuPDF
import argparse
import re
from pathlib import Path
from collections import defaultdict, Counter
import statistics
import asyncio
import json

# Configuration
DEBUG = False

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

class ContentAnalyzer:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.structural_elements = []
        self.font_analysis = {}
        self.layout_patterns = {}
        
    def analyze_content_structure(self, sample_ratio=0.3):
        """Analyze document structure based on content formatting patterns"""
        
        print(f"🔬 Analyzing content structure without TOC...")
        
        page_count = self.doc.page_count
        # Sample pages for analysis (more than TOC diagnostic since no TOC to rely on)
        if page_count <= 10:
            pages_to_analyze = range(page_count)
        else:
            sample_count = max(10, int(page_count * sample_ratio))
            step = max(1, page_count // sample_count)
            pages_to_analyze = range(0, page_count, step)
        
        debug_print(f"Analyzing {len(pages_to_analyze)} pages out of {page_count}")
        
        # Collect structural elements
        font_sizes = []
        font_usage = defaultdict(int)
        text_elements = []
        
        for page_num in pages_to_analyze:
            try:
                page = self.doc[page_num]
                text_dict = page.get_text("dict")
                
                for block in text_dict.get("blocks", []):
                    if "lines" in block:  # Text block
                        for line in block["lines"]:
                            line_text = ""
                            line_fonts = []
                            line_sizes = []
                            
                            for span in line.get("spans", []):
                                font_name = span.get("font", "")
                                font_size = span.get("size", 0)
                                text = span.get("text", "").strip()
                                
                                if text:  # Only process non-empty text
                                    line_text += text + " "
                                    line_fonts.append(font_name)
                                    line_sizes.append(font_size)
                                    font_usage[font_name] += len(text)
                                    font_sizes.append(font_size)
                            
                            if line_text.strip():
                                # Analyze this line for structural significance
                                element = self._analyze_text_element(
                                    line_text.strip(), 
                                    line_sizes, 
                                    line_fonts, 
                                    page_num,
                                    block.get("bbox", [0,0,0,0])
                                )
                                if element:
                                    text_elements.append(element)
                                    
            except Exception as e:
                debug_print(f"Error analyzing page {page_num}: {e}")
                continue
        
        # Analyze patterns
        self._analyze_font_patterns(font_sizes, font_usage)
        self._identify_structural_elements(text_elements)
        
        return self._generate_content_report()
    
    def _analyze_text_element(self, text, font_sizes, font_names, page_num, bbox):
        """Analyze a single text element for structural significance"""
        
        if not text or not font_sizes:
            return None
        
        avg_font_size = statistics.mean(font_sizes)
        primary_font = max(set(font_names), key=font_names.count) if font_names else "Unknown"
        
        # Calculate structural indicators
        indicators = {
            'is_short': len(text.split()) <= 8,  # Short lines often headings
            'is_numbered': bool(re.match(r'^\d+\.?\s', text)),  # Starts with number
            'is_uppercase': text.isupper(),
            'is_title_case': text.istitle(),
            'has_colon': text.endswith(':'),
            'is_bold': 'Bold' in primary_font or 'bold' in primary_font.lower(),
            'large_font': avg_font_size > 12,  # Adjust threshold as needed
            'very_large_font': avg_font_size > 16,
            'starts_sentence': text[0].isupper() if text else False,
            'ends_period': text.endswith('.'),
            'standalone_line': len(text.split()) <= 3,  # Very short, likely header
        }
        
        # Calculate structure score
        structure_score = 0
        
        # High value indicators
        if indicators['very_large_font']: structure_score += 10
        if indicators['is_bold']: structure_score += 8
        if indicators['large_font']: structure_score += 6
        if indicators['is_numbered']: structure_score += 7
        if indicators['is_uppercase'] and indicators['is_short']: structure_score += 9
        if indicators['is_title_case'] and indicators['is_short']: structure_score += 5
        
        # Medium value indicators
        if indicators['has_colon']: structure_score += 4
        if indicators['standalone_line']: structure_score += 3
        
        # Negative indicators (likely body text)
        if indicators['ends_period'] and not indicators['is_short']: structure_score -= 3
        if len(text.split()) > 15: structure_score -= 2  # Long lines likely body text
        
        return {
            'text': text,
            'page': page_num,
            'font_size': avg_font_size,
            'font_name': primary_font,
            'structure_score': structure_score,
            'indicators': indicators,
            'bbox': bbox
        }
    
    def _analyze_font_patterns(self, font_sizes, font_usage):
        """Analyze font usage patterns to understand document hierarchy"""
        
        if not font_sizes:
            return
        
        self.font_analysis = {
            'avg_size': statistics.mean(font_sizes),
            'median_size': statistics.median(font_sizes),
            'size_range': (min(font_sizes), max(font_sizes)),
            'size_std': statistics.stdev(font_sizes) if len(font_sizes) > 1 else 0,
            'common_sizes': Counter(font_sizes).most_common(5),
            'total_fonts': len(set(font_usage.keys())),
            'primary_fonts': sorted(font_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        # Determine likely heading sizes
        size_counts = Counter(font_sizes)
        all_sizes = sorted(set(font_sizes), reverse=True)
        
        # Heading sizes are typically larger and less frequent
        self.font_analysis['likely_heading_sizes'] = []
        for size in all_sizes:
            if size > self.font_analysis['median_size'] + 2:  # Significantly larger
                frequency = size_counts[size] / len(font_sizes)
                if frequency < 0.1:  # Less than 10% of document
                    self.font_analysis['likely_heading_sizes'].append((size, frequency))
    
    def _identify_structural_elements(self, text_elements):
        """Identify potential section breaks and headings at multiple levels"""
        
        # Sort by structure score
        all_headings = [elem for elem in text_elements if elem['structure_score'] > 3]  # Lower threshold
        all_headings.sort(key=lambda x: x['structure_score'], reverse=True)
        
        # Group headings by font size to identify hierarchy levels
        size_groups = defaultdict(list)
        for elem in all_headings:
            # Round font size to group similar sizes
            rounded_size = round(elem['font_size'], 1)
            size_groups[rounded_size].append(elem)
        
        # Identify heading levels based on font size and frequency
        heading_levels = {}
        sorted_sizes = sorted(size_groups.keys(), reverse=True)  # Largest to smallest
        
        for level, size in enumerate(sorted_sizes, 1):
            headings_at_size = size_groups[size]
            # Filter out sizes with too few instances (likely not consistent headings)
            if len(headings_at_size) >= 2 or size > self.font_analysis.get('median_size', 10) + 4:
                heading_levels[level] = {
                    'font_size': size,
                    'count': len(headings_at_size),
                    'headings': sorted(headings_at_size, key=lambda x: (x['page'], x['structure_score']), reverse=True),
                    'avg_score': statistics.mean([h['structure_score'] for h in headings_at_size])
                }
        
        # Group by pages to understand distribution
        page_distribution = defaultdict(list)
        for elem in all_headings:
            page_distribution[elem['page']].append(elem)
        
        self.structural_elements = {
            'total_elements': len(text_elements),
            'potential_headings': all_headings[:50],  # Increased from 20 to 50
            'heading_levels': heading_levels,
            'heading_distribution': dict(page_distribution),
            'avg_headings_per_page': len(all_headings) / len(set(e['page'] for e in text_elements)) if text_elements else 0
        }
    
    def _generate_content_report(self):
        """Generate analysis report"""
        
        return {
            'document_pages': self.doc.page_count,
            'font_analysis': self.font_analysis,
            'structural_elements': self.structural_elements,
            'content_structure_quality': self._assess_structure_quality()
        }
    
    def _assess_structure_quality(self):
        """Assess how well-structured the content appears to be"""
        
        quality_score = 0
        notes = []
        
        # Font diversity indicates structured formatting
        if self.font_analysis.get('total_fonts', 0) > 3:
            quality_score += 20
            notes.append("✅ Good font diversity suggests structured formatting")
        elif self.font_analysis.get('total_fonts', 0) < 2:
            notes.append("⚠️ Limited font variety may indicate simple structure")
        
        # Font size range indicates hierarchy
        size_range = self.font_analysis.get('size_range', (0, 0))
        font_range = size_range[1] - size_range[0]
        if font_range > 8:
            quality_score += 25
            notes.append("✅ Wide font size range suggests clear hierarchy")
        elif font_range < 4:
            notes.append("⚠️ Limited font size variation")
        
        # Heading frequency
        avg_headings = self.structural_elements.get('avg_headings_per_page', 0)
        if 0.5 <= avg_headings <= 3:
            quality_score += 20
            notes.append("✅ Good heading density for structure extraction")
        elif avg_headings > 5:
            notes.append("⚠️ Very high heading density - may be over-structured")
        elif avg_headings < 0.2:
            notes.append("⚠️ Very low heading density - limited structure detected")
        
        # Consistent structure indicators
        potential_headings = self.structural_elements.get('potential_headings', [])
        if potential_headings:
            high_score_count = len([h for h in potential_headings if h['structure_score'] > 10])
            if high_score_count > 3:
                quality_score += 15
                notes.append("✅ Multiple high-confidence structural elements found")
        
        return {
            'score': quality_score,
            'assessment': self._quality_assessment(quality_score),
            'notes': notes
        }
    
    def _quality_assessment(self, score):
        """Convert quality score to assessment"""
        if score >= 60:
            return "🟢 Excellent - Well-structured content suitable for extraction"
        elif score >= 40:
            return "🟡 Good - Some structure detected, extraction possible"
        elif score >= 20:
            return "🟠 Fair - Limited structure, manual review recommended"
        else:
            return "🔴 Poor - Minimal structure detected, not ideal for extraction"
    
    def print_content_report(self, detailed=False):
        """Print content analysis report"""
        
        print(f"\n🔬 Content Structure Analysis: {Path(self.pdf_path).name}")
        print("=" * 80)
        
        report = self.analyze_content_structure()
        
        # Document overview
        print(f"📊 Document Overview:")
        print(f"   Total Pages: {report['document_pages']}")
        print(f"   Analysis Method: Content-based (no TOC required)")
        
        # Structure quality assessment
        quality = report['content_structure_quality']
        print(f"\n📋 Structure Quality Assessment:")
        print(f"   {quality['assessment']}")
        print(f"   Quality Score: {quality['score']}/100")
        for note in quality['notes']:
            print(f"   {note}")
        
        # Font analysis summary
        font = report['font_analysis']
        print(f"\n🔤 Font Structure Analysis:")
        print(f"   📊 Total Fonts: {font.get('total_fonts', 0)}")
        print(f"   📏 Size Range: {font['size_range'][0]:.1f}pt - {font['size_range'][1]:.1f}pt")
        print(f"   📐 Average Size: {font['avg_size']:.1f}pt")
        
        # Structural elements
        struct = report['structural_elements']
        print(f"\n🏗️ Structural Elements:")
        print(f"   📋 Total Potential Headings: {len(struct['potential_headings'])}")
        print(f"   📊 Avg Headings/Page: {struct['avg_headings_per_page']:.1f}")
        
        # Show heading levels
        if 'heading_levels' in struct and struct['heading_levels']:
            print(f"\n📊 Detected Heading Levels:")
            for level, info in struct['heading_levels'].items():
                print(f"   Level {level}: {info['font_size']:.1f}pt font, {info['count']} headings (avg score: {info['avg_score']:.1f})")
        
        if detailed and struct['potential_headings']:
            print(f"\n🎯 Top Potential Section Headings (All Levels):")
            for i, heading in enumerate(struct['potential_headings'][:15], 1):  # Show more headings
                print(f"   {i:2d}. \"{heading['text'][:50]}{'...' if len(heading['text']) > 50 else ''}\"")
                print(f"       Page {heading['page']}, Score: {heading['structure_score']}, Font: {heading['font_size']:.1f}pt")
            
            # Show headings by level if user wants to see specific levels
            if 'heading_levels' in struct:
                print(f"\n🔍 Headings by Level:")
                for level, info in list(struct['heading_levels'].items())[:3]:  # Top 3 levels
                    print(f"   📋 Level {level} ({info['font_size']:.1f}pt):")
                    for i, heading in enumerate(info['headings'][:5], 1):  # Top 5 per level
                        print(f"      {i}. \"{heading['text'][:60]}{'...' if len(heading['text']) > 60 else ''}\"")
        
        # Recommendations
        self._print_content_recommendations(report)
    
    def print_level_analysis(self, target_level, min_score=3.0, detailed=False):
        """Print analysis focused on a specific heading level"""
        
        print(f"\n🎯 Level {target_level} Analysis: {Path(self.pdf_path).name}")
        print("=" * 80)
        
        report = self.analyze_content_structure()
        struct = report['structural_elements']
        
        if 'heading_levels' not in struct or target_level not in struct['heading_levels']:
            print(f"❌ Level {target_level} not found.")
            if 'heading_levels' in struct:
                available_levels = list(struct['heading_levels'].keys())
                print(f"   Available levels: {available_levels}")
                
                # Show all levels for reference
                print(f"\n📊 All Detected Levels:")
                for level, info in struct['heading_levels'].items():
                    print(f"   Level {level}: {info['font_size']:.1f}pt, {info['count']} headings")
            return
        
        level_info = struct['heading_levels'][target_level]
        print(f"📊 Level {target_level} Details:")
        print(f"   Font Size: {level_info['font_size']:.1f}pt")
        print(f"   Total Headings: {level_info['count']}")
        print(f"   Average Score: {level_info['avg_score']:.1f}")
        
        # Filter headings by minimum score
        filtered_headings = [h for h in level_info['headings'] if h['structure_score'] >= min_score]
        
        print(f"\n🎯 Level {target_level} Headings (score >= {min_score}):")
        print(f"   Found {len(filtered_headings)} headings meeting criteria")
        
        if detailed:
            print(f"\n📋 All Level {target_level} Headings:")
            for i, heading in enumerate(filtered_headings, 1):
                indicators = []
                if heading['indicators'].get('is_bold'): indicators.append("Bold")
                if heading['indicators'].get('is_title_case'): indicators.append("TitleCase")
                if heading['indicators'].get('is_numbered'): indicators.append("Numbered")
                if heading['indicators'].get('has_colon'): indicators.append("Colon")
                
                indicator_str = f" [{', '.join(indicators)}]" if indicators else ""
                print(f"   {i:3d}. \"{heading['text']}\"")
                print(f"        Page {heading['page']}, Score: {heading['structure_score']:.1f}{indicator_str}")
        else:
            # Show just the first 20 for overview
            print(f"\n📋 Top 20 Level {target_level} Headings:")
            for i, heading in enumerate(filtered_headings[:20], 1):
                print(f"   {i:2d}. \"{heading['text'][:70]}{'...' if len(heading['text']) > 70 else ''}\"")
                print(f"       Page {heading['page']}, Score: {heading['structure_score']:.1f}")
        
        # Extraction recommendations for this level
        print(f"\n💡 Level {target_level} Extraction Recommendations:")
        print("-" * 50)
        if len(filtered_headings) >= 5:
            print(f"✅ Good extraction target - {len(filtered_headings)} sections found")
            print(f"   • Font size: {level_info['font_size']:.1f}pt")
            print(f"   • Average {len(filtered_headings) / report['document_pages']:.1f} sections per page")
            print(f"   • This level appears suitable for section-based splitting")
        else:
            print(f"⚠️ Limited sections at this level - {len(filtered_headings)} found")
            print(f"   • Consider adjusting --min-score threshold")
            print(f"   • Or try a different level")
    
    def _print_content_recommendations(self, report):
        """Print recommendations for content extraction"""
        
        print(f"\n💡 Content Extraction Recommendations:")
        print("-" * 50)
        
        quality_score = report['content_structure_quality']['score']
        
        if quality_score >= 40:
            print(f"✅ Content-based extraction feasible")
            print(f"   • Font size patterns can identify section breaks")
            print(f"   • Look for elements with font size > {report['font_analysis']['median_size'] + 2:.1f}pt")
            
            # Identify potential extraction patterns
            headings = report['structural_elements']['potential_headings']
            if headings:
                common_patterns = self._identify_heading_patterns(headings)
                if common_patterns:
                    print(f"   • Detected patterns: {', '.join(common_patterns)}")
        else:
            print(f"⚠️ Limited structure for automatic extraction")
            print(f"   • Consider manual section identification")
            print(f"   • May need page-based splitting instead")
        
        print(f"\n🛠️ Alternative Approaches:")
        print(f"   • Use font size analysis for section detection")
        print(f"   • Apply pattern matching for numbered sections")
        print(f"   • Consider hybrid manual + automated approach")
    
    def _identify_heading_patterns(self, headings):
        """Identify common patterns in potential headings"""
        
        patterns = []
        
        # Check for numbering patterns
        numbered = [h for h in headings if h['indicators']['is_numbered']]
        if len(numbered) > 3:
            patterns.append("Numbered sections")
        
        # Check for title case patterns
        title_case = [h for h in headings if h['indicators']['is_title_case']]
        if len(title_case) > len(headings) * 0.6:
            patterns.append("Title case headings")
        
        # Check for bold patterns
        bold = [h for h in headings if h['indicators']['is_bold']]
        if len(bold) > len(headings) * 0.5:
            patterns.append("Bold formatting")
        
        # Check for consistent font sizes
        sizes = [h['font_size'] for h in headings[:10]]  # Top 10
        if len(set(sizes)) <= 3:  # Few distinct sizes
            patterns.append("Consistent heading sizes")
        
        return patterns
    
    def close(self):
        """Close the PDF document"""
        if hasattr(self, 'doc'):
            self.doc.close()

# =============================================================================
# AI Integration Functions
# =============================================================================

def run_ai_validation(pdf_path: str, level: int, context: str = "general") -> dict:
    """Run AI validation using the MCP server"""
    try:
        from pdf_structure_mcp_server import run_ai_validation as ai_validate
        return asyncio.run(ai_validate(pdf_path, level, context))
    except ImportError:
        return {
            "error": "AI validation requires pdf_structure_mcp_server.py",
            "suggestion": "Ensure MCP server dependencies are installed"
        }
    except Exception as e:
        return {
            "error": f"AI validation failed: {str(e)}",
            "fallback": "Use standard analysis without AI"
        }

def run_ai_auto_level(pdf_path: str, context: str = "general") -> dict:
    """Run AI auto-level detection using the MCP server"""
    try:
        from pdf_structure_mcp_server import run_ai_validation as ai_validate
        return asyncio.run(ai_validate(pdf_path, None, context))
    except ImportError:
        return {
            "error": "AI auto-level requires pdf_structure_mcp_server.py",
            "suggestion": "Ensure MCP server dependencies are installed"
        }
    except Exception as e:
        return {
            "error": f"AI auto-level detection failed: {str(e)}",
            "fallback": "Use manual level selection"
        }

def print_ai_result(result: dict, operation: str):
    """Print AI analysis result in a formatted way"""
    print(f"\n🤖 AI Analysis Result: {operation}")
    print("=" * 60)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if "suggestion" in result:
            print(f"💡 Suggestion: {result['suggestion']}")
        if "fallback" in result:
            print(f"🔄 Fallback: {result['fallback']}")
        return
    
    # Handle validation results
    if "status" in result:
        status = result["status"]
        confidence = result.get("confidence", 0)
        reason = result.get("reason", "No reason provided")
        
        status_emoji = "✅" if status == "VALID" else "❌" if status == "INVALID" else "🔄"
        print(f"{status_emoji} Status: {status}")
        print(f"🎯 Confidence: {confidence:.1%}")
        print(f"📝 Reason: {reason}")
        
        if status == "TRY_LEVEL" and "suggested_level" in result:
            print(f"🎲 Suggested Level: {result['suggested_level']}")
        
        if "detected_patterns" in result and result["detected_patterns"]:
            print(f"🔍 Detected Patterns: {', '.join(result['detected_patterns'])}")
            
        if "sample_headings_analysis" in result:
            print(f"📋 Sample Analysis: {result['sample_headings_analysis']}")
    
    # Handle auto-level results
    elif "optimal_level" in result:
        print(f"🎯 Optimal Level Found: {result['optimal_level']}")
        print(f"✅ Extraction Strategy Available")
        
        if "extraction_strategy" in result:
            strategy = result["extraction_strategy"]
            if "primary_strategy" in strategy:
                ps = strategy["primary_strategy"]
                print(f"📋 Strategy: {ps.get('approach', 'Unknown')}")
                print(f"🎯 Confidence: {ps.get('confidence', 0):.1%}")
                print(f"🏷️ Naming: {ps.get('section_naming', 'Unknown')}")
                
        levels_tested = result.get("levels_tested", [])
        print(f"🧪 Levels Tested: {len(levels_tested)}")
    
    # Handle strategy results  
    elif "primary_strategy" in result:
        ps = result["primary_strategy"]
        print(f"📋 Primary Strategy: {ps.get('approach', 'Unknown')}")
        print(f"🎯 Target Level: {ps.get('target_level', 'Unknown')}")
        print(f"🎯 Confidence: {ps.get('confidence', 0):.1%}")
        print(f"🏷️ Section Naming: {ps.get('section_naming', 'Unknown')}")
        print(f"📦 Grouping: {ps.get('grouping_strategy', 'Unknown')}")
        
        if "expected_output" in result:
            eo = result["expected_output"]
            print(f"📊 Expected Sections: {eo.get('section_count', 'Unknown')}")
            print(f"📄 Output Format: {eo.get('output_format', 'Unknown')}")
            print(f"⭐ Quality Estimate: {eo.get('quality_estimate', 'Unknown')}")
    
    print()  # Add spacing

def main():
    parser = argparse.ArgumentParser(
        description='Content-based PDF structure analysis (no TOC required)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python content_analyzer.py extracted_chapter.pdf
  python content_analyzer.py document.pdf --detailed
  python content_analyzer.py spells.pdf --level 2 --detailed    # Focus on level 2 headings
  python content_analyzer.py spells.pdf --level 3 --min-score 5 # Level 3, higher threshold
  python content_analyzer.py spells.pdf --ask-ai --auto-level   # AI finds optimal level
  python content_analyzer.py spells.pdf --level 4 --ask-ai      # AI validates level 4
  python content_analyzer.py simple_doc.pdf --debug
        """
    )
    
    parser.add_argument('input_pdf', help='Path to PDF file to analyze')
    parser.add_argument('--detailed', '-d', action='store_true', 
                       help='Show detailed analysis including potential headings')
    parser.add_argument('--level', '-l', type=int, 
                       help='Focus on specific heading level (1=largest, 2=medium, 3=smaller, etc.)')
    parser.add_argument('--min-score', '-s', type=float, default=3.0,
                       help='Minimum structure score for headings (default: 3.0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--ask-ai', action='store_true', 
                       help='Use AI validation and strategy suggestions')
    parser.add_argument('--auto-level', action='store_true',
                       help='Automatically find optimal level using AI (requires --ask-ai)')
    parser.add_argument('--context', type=str, default='general document analysis',
                       help='Document context for AI analysis (e.g., "D&D spells", "legal document")')
    
    args = parser.parse_args()
    
    # Set debug level
    global DEBUG
    DEBUG = args.debug
    
    if not os.path.exists(args.input_pdf):
        print(f"❌ Error: File '{args.input_pdf}' not found")
        return 1
    
    try:
        analyzer = ContentAnalyzer(args.input_pdf)
        
        # AI-powered analysis
        if args.ask_ai:
            if args.auto_level:
                # Auto-find optimal level with AI
                print("🤖 Using AI to find optimal extraction level...")
                result = run_ai_auto_level(args.input_pdf, args.context)
                print_ai_result(result, "Auto Level Detection")
            elif args.level:
                # Validate specific level with AI
                print(f"🤖 Using AI to validate Level {args.level}...")
                result = run_ai_validation(args.input_pdf, args.level, args.context)
                print_ai_result(result, f"Level {args.level} Validation")
            else:
                # Run standard analysis first, then ask for AI validation of best level
                report = analyzer.analyze_content_structure()
                if 'heading_levels' in report['structural_elements'] and report['structural_elements']['heading_levels']:
                    # Find best level by score
                    levels = report['structural_elements']['heading_levels']
                    best_level = max(levels.keys(), key=lambda k: levels[k]['avg_score'])
                    print(f"🤖 Using AI to validate best detected level ({best_level})...")
                    result = run_ai_validation(args.input_pdf, best_level, args.context)
                    print_ai_result(result, f"Best Level ({best_level}) Validation")
                else:
                    print("❌ No heading levels detected for AI analysis")
        
        # Standard analysis (always run unless auto-level with AI found optimal)
        if not args.ask_ai or not args.auto_level:
            if args.level:
                # Show specific level analysis
                analyzer.print_level_analysis(args.level, args.min_score, detailed=args.detailed)
            else:
                analyzer.print_content_report(detailed=args.detailed)
            
        analyzer.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error analyzing PDF: {str(e)}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
