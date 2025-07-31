#!/usr/bin/env python3
"""
TOC Diagnostic Tool - Intelligent analysis of PDF table of contents structure
Analyzes semantic meaning and recommends optimal extraction strategies
"""

import os
import fitz  # PyMuPDF
import argparse
import re
from pathlib import Path
from collections import defaultdict, Counter
import statistics

# Configuration
DEBUG = False

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

class TOCAnalyzer:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.toc = self.doc.get_toc(simple=False)
        self.level_analysis = defaultdict(list)
        self.document_stats = None  # Will be populated during detailed analysis
        self.semantic_patterns = {
            'chapter_indicators': ['chapter', 'part', 'section', 'book', 'volume'],
            'content_types': {
                'financial': ['financial', 'revenue', 'income', 'earnings', 'balance', 'cash', 'investment', 'performance'],
                'legal': ['legal', 'compliance', 'regulation', 'law', 'policy', 'procedure', 'risk', 'liability'],
                'reference': ['appendix', 'index', 'glossary', 'reference', 'table', 'list', 'notes', 'exhibit'],
                'governance': ['board', 'director', 'management', 'executive', 'governance', 'committee', 'audit'],
                'operational': ['business', 'operations', 'segment', 'division', 'subsidiary', 'market', 'customer'],
                'technical': ['system', 'technology', 'process', 'method', 'implementation', 'development'],
                'gaming': ['class', 'spell', 'monster', 'creature', 'item', 'equipment', 'character', 'feat'],
                'academic': ['research', 'study', 'analysis', 'methodology', 'results', 'conclusion', 'literature'],
                'narrative': ['story', 'lore', 'background', 'history', 'setting', 'biography']
            },
            'structural_words': ['overview', 'introduction', 'summary', 'conclusion', 'description']
        }
        
    def analyze_structure(self):
        """Comprehensive structural analysis of the TOC"""
        
        if not self.toc:
            return None
            
        # Organize entries by level
        for idx, entry in enumerate(self.toc):
            if len(entry) >= 3:
                level, title, page = entry[0], entry[1], entry[2]
                self.level_analysis[level].append({
                    'index': idx,
                    'title': title,
                    'page': page,
                    'title_length': len(title),
                    'word_count': len(title.split()),
                    'semantic_score': self._calculate_semantic_score(title)
                })
            else:
                debug_print(f"Skipping malformed TOC entry {idx}: {entry}")
        
        return self._generate_analysis_report()
    
    def analyze_document_details(self, sample_pages=10):
        """Perform detailed document analysis with font, image, and drawing statistics"""
        
        print(f"🔬 Performing detailed document analysis...")
        
        # Initialize counters
        total_images = 0
        total_drawings = 0
        total_links = 0
        font_analysis = defaultdict(int)
        font_sizes = []
        text_blocks = 0
        total_chars = 0
        
        # Sample pages for analysis (don't analyze every page for large docs)
        page_count = self.doc.page_count
        if page_count <= sample_pages:
            pages_to_analyze = range(page_count)
            sample_note = ""
        else:
            # Sample evenly distributed pages
            step = page_count // sample_pages
            pages_to_analyze = range(0, page_count, step)
            sample_note = f" (sampled {len(pages_to_analyze)}/{page_count} pages)"
        
        debug_print(f"Analyzing pages: {list(pages_to_analyze)}")
        
        for page_num in pages_to_analyze:
            try:
                page = self.doc[page_num]
                
                # Image analysis
                images = page.get_images()
                total_images += len(images)
                
                # Drawing analysis
                drawings = page.get_drawings()
                total_drawings += len(drawings)
                
                # Link analysis
                links = page.get_links()
                total_links += len(links)
                
                # Detailed text analysis with font information
                text_dict = page.get_text("dict")
                
                for block in text_dict.get("blocks", []):
                    if "lines" in block:  # Text block
                        text_blocks += 1
                        
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                # Font analysis
                                font_name = span.get("font", "Unknown")
                                font_size = span.get("size", 0)
                                text_content = span.get("text", "")
                                
                                font_analysis[font_name] += len(text_content)
                                font_sizes.append(font_size)
                                total_chars += len(text_content)
                
            except Exception as e:
                debug_print(f"Error analyzing page {page_num}: {e}")
                continue
        
        # Calculate statistics
        unique_fonts = len(font_analysis)
        avg_font_size = statistics.mean(font_sizes) if font_sizes else 0
        median_font_size = statistics.median(font_sizes) if font_sizes else 0
        
        # Font size distribution analysis
        font_size_distribution = defaultdict(int)
        for size in font_sizes:
            # Group font sizes into ranges
            size_range = f"{int(size//2)*2}-{int(size//2)*2+1}pt"
            font_size_distribution[size_range] += 1
        
        # Most common fonts
        top_fonts = sorted(font_analysis.items(), key=lambda x: x[1], reverse=True)[:5]
        
        self.document_stats = {
            'sample_info': {
                'pages_analyzed': len(pages_to_analyze),
                'total_pages': page_count,
                'sample_note': sample_note
            },
            'content_stats': {
                'total_images': total_images,
                'total_drawings': total_drawings,
                'total_links': total_links,
                'text_blocks': text_blocks,
                'total_characters': total_chars,
                'avg_images_per_page': total_images / len(pages_to_analyze) if pages_to_analyze else 0,
                'avg_drawings_per_page': total_drawings / len(pages_to_analyze) if pages_to_analyze else 0,
                'avg_chars_per_page': total_chars / len(pages_to_analyze) if pages_to_analyze else 0
            },
            'font_analysis': {
                'unique_fonts': unique_fonts,
                'avg_font_size': avg_font_size,
                'median_font_size': median_font_size,
                'font_size_range': (min(font_sizes), max(font_sizes)) if font_sizes else (0, 0),
                'top_fonts': top_fonts,
                'font_size_distribution': dict(font_size_distribution)
            }
        }
        
        return self.document_stats
    
    def _calculate_semantic_score(self, title):
        """Calculate semantic meaningfulness of a title"""
        score = 0
        title_lower = title.lower()
        
        # Chapter/section indicators (high value)
        for indicator in self.semantic_patterns['chapter_indicators']:
            if indicator in title_lower:
                score += 10
        
        # Content type indicators (medium-high value)
        for category, words in self.semantic_patterns['content_types'].items():
            for word in words:
                if word in title_lower:
                    score += 7
                    break  # Only count once per category
        
        # Structural indicators (medium value)
        for word in self.semantic_patterns['structural_words']:
            if word in title_lower:
                score += 5
        
        # Length and complexity indicators
        word_count = len(title.split())
        if 2 <= word_count <= 6:  # Optimal range for meaningful titles
            score += 3
        elif word_count > 6:
            score += 1
        
        # Capitalization patterns (indicates formal headings)
        if title.istitle():
            score += 2
        
        # Numeric patterns (often indicate structured content)
        if re.search(r'\d', title):
            score += 1
        
        return score
    
    def _analyze_level_characteristics(self, level, entries):
        """Analyze characteristics of entries at a specific level"""
        
        if not entries:
            return {}
        
        # Basic statistics
        title_lengths = [e['title_length'] for e in entries]
        word_counts = [e['word_count'] for e in entries]
        semantic_scores = [e['semantic_score'] for e in entries]
        page_ranges = []
        
        # Calculate page ranges for entries
        for i, entry in enumerate(entries):
            if i + 1 < len(entries):
                next_page = entries[i + 1]['page']
                page_range = next_page - entry['page']
            else:
                # Last entry - use document end
                page_range = self.doc.page_count - entry['page'] + 1
            page_ranges.append(page_range)
        
        # Content type analysis
        content_types = defaultdict(int)
        for entry in entries:
            title_lower = entry['title'].lower()
            for category, words in self.semantic_patterns['content_types'].items():
                for word in words:
                    if word in title_lower:
                        content_types[category] += 1
                        break
        
        # Structural patterns
        has_numbers = sum(1 for e in entries if re.search(r'\d', e['title']))
        has_articles = sum(1 for e in entries if any(word in e['title'].lower() 
                                                   for word in ['the', 'a', 'an']))
        proper_case = sum(1 for e in entries if e['title'].istitle())
        
        return {
            'count': len(entries),
            'avg_title_length': statistics.mean(title_lengths) if title_lengths else 0,
            'avg_word_count': statistics.mean(word_counts) if word_counts else 0,
            'avg_semantic_score': statistics.mean(semantic_scores) if semantic_scores else 0,
            'avg_page_range': statistics.mean(page_ranges) if page_ranges else 0,
            'median_page_range': statistics.median(page_ranges) if page_ranges else 0,
            'content_types': dict(content_types),
            'structural_patterns': {
                'has_numbers_pct': (has_numbers / len(entries)) * 100,
                'has_articles_pct': (has_articles / len(entries)) * 100,
                'proper_case_pct': (proper_case / len(entries)) * 100
            },
            'sample_titles': [e['title'] for e in entries[:5]]
        }
    
    def _determine_optimal_levels(self, analysis):
        """Determine which levels are most meaningful for extraction"""
        
        level_scores = {}
        
        for level, stats in analysis.items():
            score = 0
            
            # Semantic meaningfulness (0-40 points)
            score += min(stats['avg_semantic_score'] * 2, 40)
            
            # Optimal count range (0-20 points)
            count = stats['count']
            if 3 <= count <= 50:  # Sweet spot for chapters
                score += 20
            elif 51 <= count <= 100:
                score += 15
            elif count <= 2:
                score -= 10
            elif count > 200:
                score -= 5
            
            # Page range reasonableness (0-20 points)
            avg_pages = stats['avg_page_range']
            if 5 <= avg_pages <= 100:  # Reasonable chapter size
                score += 20
            elif 101 <= avg_pages <= 200:
                score += 15
            elif avg_pages < 3:
                score -= 5
            
            # Content diversity (0-15 points)
            content_diversity = len(stats['content_types'])
            score += min(content_diversity * 3, 15)
            
            # Structural consistency (0-5 points)
            if stats['structural_patterns']['proper_case_pct'] > 70:
                score += 5
            
            level_scores[level] = score
        
        # Sort by score
        ranked_levels = sorted(level_scores.items(), key=lambda x: x[1], reverse=True)
        
        return ranked_levels, level_scores
    
    def _generate_analysis_report(self):
        """Generate comprehensive analysis report"""
        
        analysis = {}
        
        # Analyze each level
        for level, entries in self.level_analysis.items():
            analysis[level] = self._analyze_level_characteristics(level, entries)
        
        # Determine optimal levels
        ranked_levels, level_scores = self._determine_optimal_levels(analysis)
        
        return {
            'level_analysis': analysis,
            'level_scores': level_scores,
            'ranked_levels': ranked_levels,
            'total_entries': len(self.toc),
            'max_level': max(self.level_analysis.keys()) if self.level_analysis else 0,
            'document_pages': self.doc.page_count
        }
    
    def print_diagnostic_report(self, detailed=False):
        """Print comprehensive diagnostic report"""
        
        print(f"\n🔍 TOC Intelligence Analysis: {Path(self.pdf_path).name}")
        print("=" * 80)
        
        if not self.toc:
            print("❌ No table of contents found in this PDF")
            return
        
        analysis_data = self.analyze_structure()
        
        # Document overview
        print(f"📊 Document Overview:")
        print(f"   Total Pages: {analysis_data['document_pages']}")
        print(f"   TOC Entries: {analysis_data['total_entries']}")
        print(f"   TOC Levels: {len(analysis_data['level_analysis'])} (1-{analysis_data['max_level']})")
        
        # Detailed document analysis if requested
        if detailed:
            self._print_detailed_document_stats()
        
        # Level-by-level analysis
        print(f"\n📋 Level Analysis & Recommendations:")
        print("-" * 60)
        
        for rank, (level, score) in enumerate(analysis_data['ranked_levels'], 1):
            stats = analysis_data['level_analysis'][level]
            
            # Determine recommendation
            if rank == 1:
                recommendation = "🥇 OPTIMAL for chapter splitting"
            elif rank == 2:
                recommendation = "🥈 GOOD alternative option"
            elif rank == 3:
                recommendation = "🥉 Consider for detailed extraction"
            else:
                recommendation = "⚪ Low priority"
            
            print(f"Level {level}: {recommendation}")
            print(f"   Entries: {stats['count']}")
            print(f"   Avg Pages/Entry: {stats['avg_page_range']:.1f}")
            print(f"   Semantic Score: {stats['avg_semantic_score']:.1f}/10")
            print(f"   Intelligence Score: {score:.1f}/100")
            
            # Content type breakdown
            if stats['content_types']:
                content_summary = ', '.join([f"{k}({v})" for k, v in 
                                           sorted(stats['content_types'].items(), 
                                                  key=lambda x: x[1], reverse=True)[:3]])
                print(f"   Content Types: {content_summary}")
            
            # Sample titles
            if detailed and stats['sample_titles']:
                print(f"   Sample Titles:")
                for title in stats['sample_titles'][:3]:
                    print(f"      • {title}")
            
            print()
        
        # Extraction recommendations
        self._print_extraction_recommendations(analysis_data)
        
        # Content-specific insights
        self._print_content_insights(analysis_data)
    
    def _print_detailed_document_stats(self):
        """Print detailed document statistics including fonts, images, and drawings"""
        
        if not self.document_stats:
            self.analyze_document_details()
        
        stats = self.document_stats
        print(f"\n🔬 Detailed Document Analysis{stats['sample_info']['sample_note']}:")
        print("-" * 60)
        
        # Content statistics
        content = stats['content_stats']
        print(f"📊 Content Statistics:")
        print(f"   📸 Images: {content['total_images']} total ({content['avg_images_per_page']:.1f}/page)")
        print(f"   🎨 Drawings/Graphics: {content['total_drawings']} total ({content['avg_drawings_per_page']:.1f}/page)")
        print(f"   🔗 Links: {content['total_links']} total")
        print(f"   📝 Text Blocks: {content['text_blocks']:,}")
        print(f"   📄 Characters: {content['total_characters']:,} ({content['avg_chars_per_page']:,.0f}/page)")
        
        # Font analysis
        font = stats['font_analysis']
        print(f"\n🔤 Font Analysis:")
        print(f"   📊 Unique Fonts: {font['unique_fonts']}")
        print(f"   📏 Font Size Range: {font['font_size_range'][0]:.1f}pt - {font['font_size_range'][1]:.1f}pt")
        print(f"   📐 Average Font Size: {font['avg_font_size']:.1f}pt")
        print(f"   📊 Median Font Size: {font['median_font_size']:.1f}pt")
        
        # Top fonts
        if font['top_fonts']:
            print(f"   🏆 Most Used Fonts:")
            for i, (font_name, char_count) in enumerate(font['top_fonts'][:3], 1):
                percentage = (char_count / content['total_characters']) * 100 if content['total_characters'] > 0 else 0
                print(f"      {i}. {font_name}: {char_count:,} chars ({percentage:.1f}%)")
        
        # Font size distribution
        if font['font_size_distribution']:
            print(f"   📊 Font Size Distribution:")
            sorted_sizes = sorted(font['font_size_distribution'].items(), 
                                key=lambda x: float(x[0].split('-')[0]))
            for size_range, count in sorted_sizes[:5]:  # Top 5 size ranges
                print(f"      {size_range}: {count} instances")
        
        # Document type analysis based on content
        self._print_content_type_analysis()
        print()
    
    def _print_content_type_analysis(self):
        """Analyze document type based on content characteristics"""
        
        if not self.document_stats:
            return
        
        content = self.document_stats['content_stats']
        font = self.document_stats['font_analysis']
        
        print(f"\n📋 Document Type Indicators:")
        
        # Visual content analysis
        if content['avg_images_per_page'] > 2:
            print(f"   🖼️  Image-rich document (good for illustrated manuals, reports)")
        elif content['avg_images_per_page'] > 0.5:
            print(f"   📷 Moderate image content (typical for structured documents)")
        else:
            print(f"   📝 Text-heavy document (typical for academic, legal, or reference)")
        
        # Graphics analysis
        if content['avg_drawings_per_page'] > 1:
            print(f"   🎨 High graphic content (charts, diagrams, technical illustrations)")
        
        # Font diversity analysis
        if font['unique_fonts'] > 10:
            print(f"   🔤 High font diversity (complex formatting, possibly design-heavy)")
        elif font['unique_fonts'] < 5:
            print(f"   📰 Simple font structure (clean, readable document)")
        
        # Font size analysis for structure detection
        font_range = font['font_size_range'][1] - font['font_size_range'][0]
        if font_range > 20:
            print(f"   📐 Wide font size range (strong hierarchical structure)")
        elif font_range > 10:
            print(f"   📏 Moderate font size variation (good heading structure)")
        else:
            print(f"   ➖ Minimal font size variation (uniform text, limited hierarchy)")
    
    def _print_extraction_recommendations(self, analysis_data):
        """Print specific extraction strategy recommendations"""
        
        print(f"💡 Extraction Strategy Recommendations:")
        print("-" * 50)
        
        best_level = analysis_data['ranked_levels'][0][0]
        best_stats = analysis_data['level_analysis'][best_level]
        
        print(f"🎯 Primary Strategy: Use Level {best_level}")
        print(f"   • Will create {best_stats['count']} chapters")
        print(f"   • Average chapter size: {best_stats['avg_page_range']:.1f} pages")
        
        # Special recommendations based on content
        content_types = best_stats['content_types']
        
        if 'gaming' in content_types and content_types['gaming'] > 5:
            print(f"   • High gaming content detected - excellent for D&D extraction")
        
        if 'reference' in content_types and content_types['reference'] > 3:
            print(f"   • Reference sections found - good for structured data extraction")
        
        # Secondary strategy
        if len(analysis_data['ranked_levels']) > 1:
            second_level = analysis_data['ranked_levels'][1][0]
            second_stats = analysis_data['level_analysis'][second_level]
            
            print(f"\n🔄 Secondary Strategy: Use Level {second_level}")
            print(f"   • For more granular extraction ({second_stats['count']} sections)")
            print(f"   • Average section size: {second_stats['avg_page_range']:.1f} pages")
        
        # Hybrid recommendations
        if best_stats['avg_page_range'] > 50:
            print(f"\n⚡ Hybrid Strategy Recommended:")
            print(f"   • Use Level {best_level} for major chapters")
            print(f"   • Use Level {best_level + 1} for subsection extraction within large chapters")
    
    def _print_content_insights(self, analysis_data):
        """Print insights about document content for extraction planning"""
        
        print(f"\n📋 Document Content Analysis:")
        print("-" * 40)
        
        # Aggregate content types across all levels
        all_content_types = defaultdict(int)
        
        for level, stats in analysis_data['level_analysis'].items():
            for content_type, count in stats['content_types'].items():
                all_content_types[content_type] += count
        
        # Determine document type and primary characteristics
        document_characteristics = self._analyze_document_type(analysis_data)
        
        print(f"📄 Document Type: {document_characteristics['type']}")
        print(f"🎯 Primary Focus: {document_characteristics['focus']}")
        
        # Content distribution analysis
        total_content = sum(all_content_types.values())
        if total_content > 0:
            # Print top content categories with percentages
            top_content = sorted(all_content_types.items(), key=lambda x: x[1], reverse=True)[:4]
            print(f"🏆 Content Distribution:")
            for category, count in top_content:
                percentage = (count / total_content) * 100
                print(f"   • {category.title()}: {count} entries ({percentage:.1f}%)")
        
        # Structural insights
        structural_insights = self._get_structural_insights(analysis_data)
        print(f"\n🔍 Structural Insights:")
        for insight in structural_insights:
            print(f"   {insight}")
        
        # Extraction recommendations based on content
        extraction_notes = self._get_content_extraction_notes(all_content_types, analysis_data)
        if extraction_notes:
            print(f"\n💡 Content-Based Extraction Notes:")
            for note in extraction_notes:
                print(f"   {note}")
    
    def _analyze_document_type(self, analysis_data):
        """Determine the document type based on content patterns"""
        
        # Aggregate all content
        all_content = defaultdict(int)
        for level_stats in analysis_data['level_analysis'].values():
            for content_type, count in level_stats['content_types'].items():
                all_content[content_type] += count
        
        if not all_content:
            return {'type': 'General Document', 'focus': 'Mixed Content'}
        
        # Determine primary type
        top_category = max(all_content.items(), key=lambda x: x[1])
        category_name, category_count = top_category
        
        document_types = {
            'financial': {'type': 'Financial/Business Document', 'focus': 'Financial reporting and business operations'},
            'legal': {'type': 'Legal/Regulatory Document', 'focus': 'Compliance and regulatory matters'},
            'governance': {'type': 'Corporate Governance Document', 'focus': 'Management and organizational structure'},
            'operational': {'type': 'Business Operations Document', 'focus': 'Business processes and operations'},
            'technical': {'type': 'Technical Documentation', 'focus': 'Technical processes and systems'},
            'gaming': {'type': 'Gaming/RPG Manual', 'focus': 'Game rules and content'},
            'academic': {'type': 'Academic/Research Document', 'focus': 'Research and scholarly content'},
            'reference': {'type': 'Reference Document', 'focus': 'Reference materials and appendices'}
        }
        
        return document_types.get(category_name, {'type': 'General Document', 'focus': 'Mixed content'})
    
    def _get_structural_insights(self, analysis_data):
        """Generate insights about document structure"""
        
        insights = []
        
        total_entries = analysis_data['total_entries']
        max_level = analysis_data['max_level']
        pages = analysis_data['document_pages']
        
        # Document complexity
        if total_entries > 200:
            insights.append("📊 Highly detailed document with extensive navigation structure")
        elif total_entries < 20:
            insights.append("📖 Simple document structure with minimal subdivisions")
        else:
            insights.append("📋 Moderately structured document with good organization")
        
        # Depth analysis
        if max_level > 3:
            insights.append(f"🔍 Deep hierarchy ({max_level} levels) - suitable for granular extraction")
        elif max_level <= 2:
            insights.append("� Shallow hierarchy - best for major section extraction")
        
        # Density analysis
        entries_per_page = total_entries / pages if pages > 0 else 0
        if entries_per_page > 2:
            insights.append("🗂️ High bookmark density - well-structured for navigation")
        elif entries_per_page < 0.5:
            insights.append("📄 Low bookmark density - may need page-based extraction for some content")
        
        return insights
    
    def _get_content_extraction_notes(self, content_types, analysis_data):
        """Generate content-specific extraction recommendations"""
        
        notes = []
        
        if not content_types:
            notes.append("⚠️ Limited content type detection - may need manual section identification")
            return notes
        
        # Financial document specific
        if 'financial' in content_types and content_types['financial'] > 3:
            notes.append("� Financial content detected - excellent for financial data extraction")
            notes.append("📈 Consider structured extraction for numerical data and tables")
        
        # Legal/compliance documents
        if 'legal' in content_types and content_types['legal'] > 2:
            notes.append("⚖️ Legal/regulatory content found - good for compliance analysis")
        
        # Gaming documents
        if 'gaming' in content_types and content_types['gaming'] > 10:
            notes.append("🎮 Gaming content detected - suitable for game database extraction")
        
        # Technical documents
        if 'technical' in content_types and content_types['technical'] > 5:
            notes.append("🔧 Technical content found - good for process documentation extraction")
        
        # Reference-heavy documents
        if 'reference' in content_types and content_types['reference'] > 5:
            notes.append("📚 Reference-heavy document - excellent for structured data extraction")
        
        # Academic documents
        if 'academic' in content_types and content_types['academic'] > 3:
            notes.append("🎓 Academic content detected - suitable for research data extraction")
        
        return notes
    
    def close(self):
        """Close the PDF document"""
        if hasattr(self, 'doc'):
            self.doc.close()

def main():
    parser = argparse.ArgumentParser(
        description='Intelligent TOC analysis for optimal PDF extraction strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python toc_diagnostic.py srd/SRD_CC_v5.2.1.pdf
  python toc_diagnostic.py document.pdf --detailed
  python toc_diagnostic.py report.pdf --debug
  python toc_diagnostic.py complex_doc.pdf -d    # Full analysis with fonts/images
        """
    )
    
    parser.add_argument('input_pdf', help='Path to PDF file to analyze')
    parser.add_argument('--detailed', '-d', action='store_true', 
                       help='Show detailed analysis including fonts, images, drawings, and sample titles')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Set debug level
    global DEBUG
    DEBUG = args.debug
    
    if not os.path.exists(args.input_pdf):
        print(f"❌ Error: File '{args.input_pdf}' not found")
        return 1
    
    try:
        analyzer = TOCAnalyzer(args.input_pdf)
        analyzer.print_diagnostic_report(detailed=args.detailed)
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
