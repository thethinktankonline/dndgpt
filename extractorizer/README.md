# Extractorizer - PDF Document Intelligence & Extraction Suite

A comprehensive toolkit for analyzing and extracting structured content from PDF documents, specifically designed for D&D SRD processing and similar structured documents.

## 🛠️ Tools Overview

### 1. TOC Diagnostic Tool (`toc_diagnostic.py`)

**Purpose**: Analyze PDFs with embedded Table of Contents for extraction feasibility

**Key Features**:

- TOC structure analysis and scoring
- Semantic document type detection (gaming, financial, legal, etc.)
- Font and image statistics
- Document suitability assessment

**Usage**:

```bash
# Basic analysis
uv run python toc_diagnostic.py "../srd/SRD_CC_v5.2.1.pdf"

# Detailed analysis with recommendations
uv run python toc_diagnostic.py "../srd/SRD_CC_v5.2.1.pdf" --detailed

# Enable debug output
uv run python toc_diagnostic.py document.pdf --debug
```

**Best For**: Initial document assessment, determining if TOC-based extraction is viable

---

### 2. PDF Splitter Tool (`pdf_splitter.py`)

**Purpose**: Interactive extraction of chapters/sections using TOC structure

**Key Features**:

- TOC-based chapter extraction
- Numerical prefixes for proper ordering (01*, 02*, etc.)
- Document validation (prevents extraction from unsuitable PDFs)
- Same-page chapter handling
- Interactive chapter selection

**Usage**:

```bash
# Interactive extraction with validation
uv run python pdf_splitter.py "../srd/SRD_CC_v5.2.1.pdf"

# Extract to specific output directory
uv run python pdf_splitter.py input.pdf --output-dir "extracted_chapters"
```

**Best For**: Extracting chapters from well-structured PDFs with embedded TOC

---

### 3. Content Analyzer Tool (`content_analyzer.py`) ⭐

**Purpose**: Structure analysis for PDFs WITHOUT embedded TOC using font/formatting patterns

**Key Features**:

- Multi-level heading hierarchy detection
- Font-based structure analysis
- Confidence scoring for potential headings
- Level-specific analysis (focus on specific heading sizes)
- Perfect for analyzing extracted chapters

**Usage Examples**:

```bash
# Basic structure analysis
uv run python content_analyzer.py extracted_chapter.pdf

# Detailed analysis with all headings shown
uv run python content_analyzer.py spells.pdf --detailed

# Focus on specific heading level (spell names are Level 4)
uv run python content_analyzer.py spells.pdf --level 4 --detailed

# Higher confidence threshold for cleaner results
uv run python content_analyzer.py spells.pdf --level 4 --min-score 10

# 🤖 AI-Powered Analysis (requires OpenAI API key)
uv run python content_analyzer.py spells.pdf --ask-ai --auto-level    # AI finds optimal level
uv run python content_analyzer.py spells.pdf --level 4 --ask-ai       # AI validates level 4
uv run python content_analyzer.py spells.pdf --ask-ai --context "D&D spells"  # With context

# Multiple options combined
uv run python content_analyzer.py spells.pdf --level 4 --min-score 10 --detailed
```

**Best For**: Analyzing extracted chapters, finding spell lists, identifying subsections in documents without TOC

---

## 🎯 Workflow Examples

### Standard SRD Processing Workflow

1. **Initial Assessment**: `toc_diagnostic.py SRD_document.pdf --detailed`
2. **Extract Chapters**: `pdf_splitter.py SRD_document.pdf`
3. **Analyze Extracted**: `content_analyzer.py srd_5e_07_spells.pdf --level 4 --detailed`

### Spell Analysis Workflow (Current Use Case)

```bash
# Find all spell names in extracted spells chapter
uv run python content_analyzer.py "../srd/srd 5.2/srd_5e_07_spells.pdf" --level 4 --min-score 10 --detailed

# Results: 113 individual D&D spells identified with confidence scores
# Examples: "Wish", "Fireball", "Magic Missile", "Cure Wounds", etc.
```

---

## 📊 Current Achievements

### ✅ Completed Features

- **TOC-based extraction** with numerical prefixes (01*, 02*, etc.)
- **Document validation** preventing extraction from unsuitable PDFs
- **Multi-level heading detection** with font-based analysis
- **Structure quality assessment** with scoring algorithms
- **Level-specific analysis** for granular content inspection
- **Detailed reporting** with formatting indicators and confidence scores

### 🔍 Key Discoveries

- **Extracted chapters lose TOC structure** → Content analyzer solves this
- **Font analysis replaces TOC** for structure detection in extracted files
- **Level 4 headings (12.0pt)** contain individual spell names (113 found)
- **Confidence scoring** effectively filters noise from real headings

### 📈 Current Capabilities

- Extract SRD chapters with proper numerical ordering
- Analyze extracted chapters for internal structure
- Identify spell lists, subsections, and content hierarchy
- Generate detailed reports with extraction recommendations

---

## 🚀 Next Steps & Future Enhancements

### ✅ NEW: AI Intelligence Layer

- **🤖 AI Validation**: OpenAI-powered structure validation using GPT-4o
- **🎯 Auto-Level Detection**: AI automatically finds optimal extraction level
- **📋 Smart Strategy**: AI provides detailed extraction recommendations
- **🔧 MCP Standard**: Built using Model Context Protocol for interoperability

### AI Integration Features

- **Structure Validation**: AI confirms extracted headings are meaningful
- **Level Recommendation**: AI suggests better levels if current choice is poor
- **Context-Aware**: Provide document context (e.g., "D&D spells") for better analysis
- **Extraction Strategy**: Detailed recommendations for successful content extraction
- **Fallback Options**: Alternative approaches when primary strategy fails

### Setup Requirements

1. **OpenAI API Key**: Set `TRAINING_OPENAI_API_KEY` in `.env` file
2. **Dependencies**: `uv add mcp openai python-dotenv pydantic`
3. **Schema Module**: `pdf_structure_meta_schema.py` with Pydantic validation
4. **MCP Server**: `pdf_structure_mcp_server.py` for AI integration

### Planned Intelligence Layer

- **LLM Integration**: Send structure analysis to AI for intelligent extraction recommendations ✅
- **Strategy Suggestions**: AI-powered grouping and organization suggestions ✅
- **Content Understanding**: Semantic analysis of document types and optimal extraction patterns ✅

### Potential Enhancements

- **Batch Processing**: Analyze multiple files simultaneously
- **Custom Extraction**: User-defined extraction rules based on analysis
- **Content Classification**: Automatic categorization of extracted sections
- **Export Formats**: JSON, CSV, or structured data output

---

## 🔧 Technical Notes

### Dependencies

- **PyMuPDF (fitz)**: PDF processing, TOC extraction, font analysis
- **Python Standard Library**: argparse, pathlib, collections, statistics
- **uv**: Package management and execution

### Performance

- **TOC Diagnostic**: Fast analysis using embedded TOC structure
- **Content Analyzer**: Samples 30% of pages for efficiency while maintaining accuracy
- **Font Analysis**: Optimized for large documents with statistical sampling

### File Structure

```
extractorizer/
├── toc_diagnostic.py     # TOC-based analysis
├── pdf_splitter.py       # Interactive extraction
├── content_analyzer.py   # Content structure analysis
└── README.md            # This file
```

---

## 💡 Tips & Best Practices

1. **Always start with `toc_diagnostic.py`** to assess document structure
2. **Use `--detailed` flag** for comprehensive analysis and recommendations
3. **Content analyzer works best on extracted chapters** (not full documents)
4. **Level 4 analysis typically finds individual items** (spells, rules, etc.)
5. **Adjust `--min-score` to filter out false positives** in heading detection
6. **Check multiple levels** to understand document hierarchy fully

---

_Last Updated: Current development session - Spell analysis workflow validated_
