#!/usr/bin/env python3
"""
PDF Structure Analysis MCP Server
Provides AI-powered validation and extraction strategy for PDF documents using OpenAI
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from openai import OpenAI
from dotenv import load_dotenv

from content_analyzer import ContentAnalyzer
from pdf_structure_meta_schema import (
    get_openai_function_schema, 
    validate_response,
    ValidationResult,
    ExtractionStrategy,
    StructureAnalysisInput,
    HeadingSample,
    HeadingData,
    FontAnalysis
)

# Load environment variables
load_dotenv()

# Initialize MCP server
server = Server("pdf-structure-analyzer")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("TRAINING_OPENAI_API_KEY"))

# Configuration
DEBUG = False
MAX_SAMPLE_HEADINGS = 10

def debug_print(message: str):
    if DEBUG:
        print(f"[MCP-DEBUG] {message}")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available PDF analysis tools"""
    return [
        types.Tool(
            name="validate_pdf_structure",
            description="Validate if extracted PDF structure represents meaningful document sections using AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string", 
                        "description": "Absolute path to PDF file"
                    },
                    "level": {
                        "type": "integer", 
                        "description": "Heading level to validate (1=largest, 2=medium, etc.)"
                    },
                    "min_score": {
                        "type": "number", 
                        "default": 3.0,
                        "description": "Minimum structure score threshold"
                    },
                    "context": {
                        "type": "string", 
                        "default": "general document analysis",
                        "description": "Document context or purpose for better analysis"
                    }
                },
                "required": ["pdf_path", "level"]
            }
        ),
        types.Tool(
            name="suggest_extraction_strategy",
            description="Provide detailed extraction recommendations for validated PDF structure using AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string", 
                        "description": "Absolute path to PDF file"
                    },
                    "validated_level": {
                        "type": "integer", 
                        "description": "AI-validated heading level"
                    },
                    "context": {
                        "type": "string", 
                        "default": "general document processing",
                        "description": "Document context/purpose for tailored recommendations"
                    }
                },
                "required": ["pdf_path", "validated_level"]
            }
        ),
        types.Tool(
            name="auto_find_optimal_level",
            description="Automatically find the optimal extraction level using AI validation across multiple levels",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string", 
                        "description": "Absolute path to PDF file"
                    },
                    "context": {
                        "type": "string", 
                        "default": "general document analysis",
                        "description": "Document context for analysis"
                    },
                    "max_levels_to_try": {
                        "type": "integer", 
                        "default": 5,
                        "description": "Maximum number of levels to test"
                    }
                },
                "required": ["pdf_path"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "validate_pdf_structure":
            return await validate_structure(arguments)
        elif name == "suggest_extraction_strategy":
            return await suggest_strategy(arguments)
        elif name == "auto_find_optimal_level":
            return await auto_find_optimal_level(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        debug_print(f"Error in {name}: {str(e)}")
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": f"Tool execution failed: {str(e)}",
                "tool": name,
                "arguments": arguments
            }, indent=2)
        )]

async def validate_structure(args: dict) -> List[types.TextContent]:
    """Validate PDF structure using OpenAI with structured function calling"""
    
    pdf_path = args["pdf_path"]
    level = args["level"]
    min_score = args.get("min_score", 3.0)
    context = args.get("context", "general document analysis")
    
    debug_print(f"Validating PDF structure: {pdf_path}, level {level}")
    
    # Analyze PDF structure
    analyzer = ContentAnalyzer(pdf_path)
    try:
        report = analyzer.analyze_content_structure()
        
        # Check if requested level exists
        struct = report['structural_elements']
        if 'heading_levels' not in struct or level not in struct['heading_levels']:
            available_levels = list(struct['heading_levels'].keys()) if 'heading_levels' in struct else []
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Level {level} not found in document",
                    "available_levels": available_levels,
                    "suggestion": "Try a different level or use auto_find_optimal_level tool"
                }, indent=2)
            )]
        
        # Prepare structure data for AI analysis
        level_info = struct['heading_levels'][level]
        filtered_headings = [h for h in level_info['headings'] if h['structure_score'] >= min_score]
        
        # Create structured input for AI
        structure_input = StructureAnalysisInput(
            document_name=Path(pdf_path).name,
            document_pages=report['document_pages'],
            analysis_level=level,
            font_analysis=FontAnalysis(
                font_size=level_info['font_size'],
                total_fonts=report['font_analysis'].get('total_fonts'),
                size_range=list(report['font_analysis'].get('size_range', [0, 0])),
                median_size=report['font_analysis'].get('median_size')
            ),
            heading_data=HeadingData(
                count=len(filtered_headings),
                avg_score=level_info['avg_score'],
                sample_headings=[
                    HeadingSample(
                        text=h['text'][:100],  # Limit text length
                        page=h['page'],
                        score=h['structure_score'],
                        font_size=h['font_size']
                    ) for h in filtered_headings[:MAX_SAMPLE_HEADINGS]
                ]
            )
        )
        
    finally:
        analyzer.close()
    
    # Upload PDF to OpenAI temporarily for AI analysis
    temp_file_id = None
    try:
        with open(pdf_path, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")
            temp_file_id = file.id
            debug_print(f"Uploaded PDF with file ID: {temp_file_id}")
        
        # Create validation prompt
        validation_prompt = f"""
Analyze this PDF document structure to validate if the extracted headings represent meaningful content sections.

Context: {context}
Document Analysis: {structure_input.model_dump_json(indent=2)}

Please examine the actual PDF content and compare it with the extracted structure data.

Key validation criteria:
1. Do the sample headings represent logical document sections?
2. Are they consistent in formatting and purpose?
3. Would extraction at this level produce meaningful, usable content?
4. Are there better levels that should be tried instead?

Consider the document context: {context}
"""
        
        # Get validation function schema
        validation_function = get_openai_function_schema("validation_result")
        
        # Call OpenAI with function calling
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": validation_prompt,
                    "attachments": [{"file_id": file.id, "tools": [{"type": "file_search"}]}]
                }
            ],
            tools=[{"type": "function", "function": validation_function}],
            tool_choice={"type": "function", "function": {"name": validation_function["name"]}},
            temperature=0.3
        )
        
        # Parse and validate function call result
        tool_call = response.choices[0].message.tool_calls[0]
        validation_data = json.loads(tool_call.function.arguments)
        
        # Validate with Pydantic
        validation_result = validate_response("validation_result", validation_data)
        
        debug_print(f"AI validation result: {validation_result.status}")
        
        return [types.TextContent(
            type="text",
            text=validation_result.model_dump_json(indent=2)
        )]
        
    finally:
        # Clean up uploaded file
        if temp_file_id:
            try:
                client.files.delete(temp_file_id)
                debug_print(f"Cleaned up file: {temp_file_id}")
            except Exception as e:
                debug_print(f"Error cleaning up file: {e}")

async def suggest_strategy(args: dict) -> List[types.TextContent]:
    """Suggest detailed extraction strategy for validated structure"""
    
    pdf_path = args["pdf_path"]
    validated_level = args["validated_level"]
    context = args.get("context", "general document processing")
    
    debug_print(f"Suggesting strategy for: {pdf_path}, level {validated_level}")
    
    # Get detailed structure analysis
    analyzer = ContentAnalyzer(pdf_path)
    try:
        report = analyzer.analyze_content_structure()
        
        # Check validated level exists
        if validated_level not in report['structural_elements']['heading_levels']:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Validated level {validated_level} not found in analysis"
                }, indent=2)
            )]
        
        level_info = report['structural_elements']['heading_levels'][validated_level]
        
    finally:
        analyzer.close()
    
    # Upload PDF for AI analysis
    temp_file_id = None
    try:
        with open(pdf_path, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")
            temp_file_id = file.id
        
        strategy_prompt = f"""
Provide detailed extraction strategy for this validated PDF structure.

Document: {Path(pdf_path).name}
Validated Level: {validated_level}
Context: {context}
Level Details: Font size {level_info['font_size']:.1f}pt, {level_info['count']} headings, avg score {level_info['avg_score']:.1f}

Full Structure Analysis: {json.dumps(report, indent=2, default=str)}

Based on your analysis of the actual PDF content and the structure data, provide:

1. **Primary Strategy**: The best approach for extraction
2. **Implementation Details**: Specific parameters and thresholds
3. **Potential Challenges**: What could go wrong and how to handle it
4. **Fallback Strategies**: Alternative approaches if primary fails
5. **Expected Output**: What the user can expect from extraction

Consider the document context ({context}) when making recommendations.
Focus on practical, actionable advice for successful content extraction.
"""
        
        # Get strategy function schema
        strategy_function = get_openai_function_schema("extraction_strategy")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": strategy_prompt,
                    "attachments": [{"file_id": file.id, "tools": [{"type": "file_search"}]}]
                }
            ],
            tools=[{"type": "function", "function": strategy_function}],
            tool_choice={"type": "function", "function": {"name": strategy_function["name"]}},
            temperature=0.4  # Slightly more creative for strategy suggestions
        )
        
        # Parse and validate result
        tool_call = response.choices[0].message.tool_calls[0]
        strategy_data = json.loads(tool_call.function.arguments)
        
        # Validate with Pydantic
        strategy_result = validate_response("extraction_strategy", strategy_data)
        
        return [types.TextContent(
            type="text", 
            text=strategy_result.model_dump_json(indent=2)
        )]
        
    finally:
        if temp_file_id:
            try:
                client.files.delete(temp_file_id)
            except Exception as e:
                debug_print(f"Error cleaning up file: {e}")

async def auto_find_optimal_level(args: dict) -> List[types.TextContent]:
    """Automatically find optimal extraction level using AI validation"""
    
    pdf_path = args["pdf_path"]
    context = args.get("context", "general document analysis")
    max_levels = args.get("max_levels_to_try", 5)
    
    debug_print(f"Auto-finding optimal level for: {pdf_path}")
    
    # Get all available levels
    analyzer = ContentAnalyzer(pdf_path)
    try:
        report = analyzer.analyze_content_structure()
        available_levels = list(report['structural_elements']['heading_levels'].keys())
    finally:
        analyzer.close()
    
    if not available_levels:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "No heading levels detected in document",
                "suggestion": "Document may not have clear structural formatting"
            }, indent=2)
        )]
    
    # Sort levels by avg score (best first), limit to max_levels
    level_scores = []
    analyzer = ContentAnalyzer(pdf_path)
    try:
        for level in available_levels:
            level_info = report['structural_elements']['heading_levels'][level]
            level_scores.append((level, level_info['avg_score'], level_info['count']))
    finally:
        analyzer.close()
    
    # Sort by score, then by reasonable count (not too few, not too many)
    level_scores.sort(key=lambda x: (x[1], min(x[2], 100) if x[2] >= 5 else x[2] * 0.1), reverse=True)
    levels_to_try = [level for level, _, _ in level_scores[:max_levels]]
    
    debug_print(f"Trying levels in order: {levels_to_try}")
    
    # Try each level until we find a valid one
    results = []
    for level in levels_to_try:
        try:
            validation_args = {
                "pdf_path": pdf_path,
                "level": level,
                "context": context
            }
            
            validation_results = await validate_structure(validation_args)
            validation_json = json.loads(validation_results[0].text)
            
            if "error" in validation_json:
                continue
                
            # Parse validation result
            validation = ValidationResult(**validation_json)
            
            results.append({
                "level": level,
                "validation": validation_json,
                "status": validation.status
            })
            
            # If we found a valid level, stop searching
            if validation.status == "VALID":
                debug_print(f"Found optimal level: {level}")
                
                # Get strategy for this level
                strategy_args = {
                    "pdf_path": pdf_path,
                    "validated_level": level,
                    "context": context
                }
                
                strategy_results = await suggest_strategy(strategy_args)
                strategy_json = json.loads(strategy_results[0].text)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "optimal_level": level,
                        "validation_result": validation_json,
                        "extraction_strategy": strategy_json,
                        "levels_tested": results
                    }, indent=2)
                )]
                
        except Exception as e:
            debug_print(f"Error testing level {level}: {e}")
            results.append({
                "level": level,
                "error": str(e)
            })
            continue
    
    # No valid level found
    return [types.TextContent(
        type="text",
        text=json.dumps({
            "success": False,
            "error": "No suitable extraction level found",
            "levels_tested": results,
            "suggestion": "Document may not have clear structural formatting suitable for automatic extraction"
        }, indent=2)
    )]

def run_server():
    """Run the MCP server"""
    import mcp.server.stdio
    
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pdf-structure-analyzer",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    )
                )
            )
    
    asyncio.run(main())

# Integration functions for direct use with content_analyzer.py
async def run_ai_validation(pdf_path: str, level: int = None, context: str = "general") -> dict:
    """Run AI validation - can be called directly from content_analyzer"""
    if level:
        args = {"pdf_path": pdf_path, "level": level, "context": context}
        results = await validate_structure(args)
        return json.loads(results[0].text)
    else:
        args = {"pdf_path": pdf_path, "context": context}
        results = await auto_find_optimal_level(args)
        return json.loads(results[0].text)

async def run_ai_strategy(pdf_path: str, validated_level: int, context: str = "general") -> dict:
    """Run AI strategy suggestion"""
    args = {"pdf_path": pdf_path, "validated_level": validated_level, "context": context}
    results = await suggest_strategy(args)
    return json.loads(results[0].text)

if __name__ == "__main__":
    # Check for debug flag
    import sys
    if "--debug" in sys.argv:
        DEBUG = True
        debug_print("Debug mode enabled")
    
    # Check API key
    if not os.getenv("TRAINING_OPENAI_API_KEY"):
        print("❌ Error: TRAINING_OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in a .env file")
        sys.exit(1)
    
    print("🚀 Starting PDF Structure Analysis MCP Server...")
    print("📋 Available tools: validate_pdf_structure, suggest_extraction_strategy, auto_find_optimal_level")
    
    run_server()
