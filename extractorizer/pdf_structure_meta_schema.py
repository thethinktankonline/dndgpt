#!/usr/bin/env python3
"""
PDF Structure Analysis - Schema Definitions
Contains JSON schemas and Pydantic models for structured AI responses
"""

from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field
import json

# =============================================================================
# JSON SCHEMAS (OpenAI Function Calling Compatible)
# =============================================================================

VALIDATION_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string", 
            "enum": ["VALID", "INVALID", "TRY_LEVEL"],
            "description": "Validation result status"
        },
        "confidence": {
            "type": "number", 
            "minimum": 0.0, 
            "maximum": 1.0,
            "description": "Confidence in validation result (0.0 to 1.0)"
        },
        "reason": {
            "type": "string",
            "description": "Detailed explanation for the validation decision"
        },
        "suggested_level": {
            "type": "integer",
            "minimum": 1,
            "maximum": 15,
            "description": "Recommended heading level if status is TRY_LEVEL"
        },
        "extraction_feasible": {
            "type": "boolean",
            "description": "Whether meaningful extraction is possible at any level"
        },
        "detected_patterns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of structural patterns detected (e.g., 'spell_names', 'numbered_sections')"
        },
        "sample_headings_analysis": {
            "type": "string",
            "description": "Brief analysis of what the sample headings represent"
        }
    },
    "required": ["status", "confidence", "reason", "extraction_feasible"],
    "additionalProperties": False
}

EXTRACTION_STRATEGY_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_strategy": {
            "type": "object",
            "properties": {
                "approach": {
                    "type": "string",
                    "enum": ["font_based", "pattern_based", "hybrid", "manual_assisted"],
                    "description": "Primary extraction approach"
                },
                "target_level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 15,
                    "description": "Recommended heading level for extraction"
                },
                "section_naming": {
                    "type": "string",
                    "enum": ["preserve_original", "normalize_titles", "add_prefixes", "custom_pattern"],
                    "description": "How to name extracted sections"
                },
                "grouping_strategy": {
                    "type": "string", 
                    "enum": ["individual", "alphabetical_batches", "thematic_groups", "page_ranges"],
                    "description": "How to group extracted content"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence in primary strategy success"
                }
            },
            "required": ["approach", "target_level", "section_naming", "grouping_strategy", "confidence"]
        },
        "implementation_details": {
            "type": "object",
            "properties": {
                "font_size_threshold": {
                    "type": "number",
                    "description": "Minimum font size for section detection"
                },
                "score_threshold": {
                    "type": "number", 
                    "description": "Minimum structure score for heading detection"
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Recommended items per batch if grouping"
                },
                "naming_pattern": {
                    "type": "string",
                    "description": "Template for section naming (e.g., '{index:02d}_{title}')"
                }
            }
        },
        "potential_challenges": {
            "type": "array",
            "items": {
                "type": "object", 
                "properties": {
                    "challenge": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "mitigation": {"type": "string"}
                },
                "required": ["challenge", "severity", "mitigation"]
            },
            "description": "Anticipated extraction challenges and solutions"
        },
        "fallback_strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "approach": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                },
                "required": ["approach", "description", "confidence"]
            },
            "description": "Alternative approaches if primary strategy fails"
        },
        "expected_output": {
            "type": "object",
            "properties": {
                "section_count": {
                    "type": "integer",
                    "description": "Expected number of extracted sections"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["individual_pdfs", "json_index", "csv_listing", "structured_directory"],
                    "description": "Recommended output format"
                },
                "quality_estimate": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Expected quality of extraction results"
                }
            },
            "required": ["section_count", "output_format", "quality_estimate"]
        }
    },
    "required": ["primary_strategy", "potential_challenges", "expected_output"],
    "additionalProperties": False
}

STRUCTURE_ANALYSIS_INPUT_SCHEMA = {
    "type": "object", 
    "properties": {
        "document_name": {"type": "string"},
        "document_pages": {"type": "integer"},
        "analysis_level": {"type": "integer"},
        "font_analysis": {
            "type": "object",
            "properties": {
                "font_size": {"type": "number"},
                "total_fonts": {"type": "integer"},
                "size_range": {
                    "type": "array", 
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2
                },
                "median_size": {"type": "number"}
            }
        },
        "heading_data": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "avg_score": {"type": "number"},
                "sample_headings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "page": {"type": "integer"},
                            "score": {"type": "number"},
                            "font_size": {"type": "number"}
                        }
                    }
                }
            }
        }
    },
    "required": ["document_name", "analysis_level", "heading_data"]
}

# =============================================================================
# PYDANTIC MODELS (Runtime Validation & IDE Support)
# =============================================================================

class ValidationResult(BaseModel):
    """Pydantic model for PDF structure validation results"""
    status: Literal["VALID", "INVALID", "TRY_LEVEL"] = Field(
        description="Validation result status"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in validation result (0.0 to 1.0)"
    )
    reason: str = Field(
        description="Detailed explanation for the validation decision"
    )
    suggested_level: Optional[int] = Field(
        None, ge=1, le=15,
        description="Recommended heading level if status is TRY_LEVEL"
    )
    extraction_feasible: bool = Field(
        description="Whether meaningful extraction is possible at any level"
    )
    detected_patterns: Optional[List[str]] = Field(
        None,
        description="List of structural patterns detected"
    )
    sample_headings_analysis: Optional[str] = Field(
        None,
        description="Brief analysis of what the sample headings represent"
    )

class PrimaryStrategy(BaseModel):
    """Primary extraction strategy details"""
    approach: Literal["font_based", "pattern_based", "hybrid", "manual_assisted"] = Field(
        description="Primary extraction approach"
    )
    target_level: int = Field(
        ge=1, le=15,
        description="Recommended heading level for extraction"
    )
    section_naming: Literal["preserve_original", "normalize_titles", "add_prefixes", "custom_pattern"] = Field(
        description="How to name extracted sections"
    )
    grouping_strategy: Literal["individual", "alphabetical_batches", "thematic_groups", "page_ranges"] = Field(
        description="How to group extracted content"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in primary strategy success"
    )

class ImplementationDetails(BaseModel):
    """Implementation-specific parameters"""
    font_size_threshold: Optional[float] = Field(
        None,
        description="Minimum font size for section detection"
    )
    score_threshold: Optional[float] = Field(
        None,
        description="Minimum structure score for heading detection"
    )
    batch_size: Optional[int] = Field(
        None,
        description="Recommended items per batch if grouping"
    )
    naming_pattern: Optional[str] = Field(
        None,
        description="Template for section naming (e.g., '{index:02d}_{title}')"
    )

class Challenge(BaseModel):
    """Potential extraction challenge"""
    challenge: str = Field(description="Description of the challenge")
    severity: Literal["low", "medium", "high"] = Field(description="Severity level")
    mitigation: str = Field(description="Suggested mitigation approach")

class FallbackStrategy(BaseModel):
    """Alternative extraction strategy"""
    approach: str = Field(description="Fallback approach name")
    description: str = Field(description="Detailed description of approach")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in fallback strategy"
    )

class ExpectedOutput(BaseModel):
    """Expected extraction results"""
    section_count: int = Field(description="Expected number of extracted sections")
    output_format: Literal["individual_pdfs", "json_index", "csv_listing", "structured_directory"] = Field(
        description="Recommended output format"
    )
    quality_estimate: Literal["high", "medium", "low"] = Field(
        description="Expected quality of extraction results"
    )

class ExtractionStrategy(BaseModel):
    """Complete extraction strategy recommendation"""
    primary_strategy: PrimaryStrategy = Field(description="Primary extraction approach")
    implementation_details: Optional[ImplementationDetails] = Field(
        None,
        description="Implementation-specific parameters"
    )
    potential_challenges: List[Challenge] = Field(
        description="Anticipated extraction challenges and solutions"
    )
    fallback_strategies: Optional[List[FallbackStrategy]] = Field(
        None,
        description="Alternative approaches if primary strategy fails"
    )
    expected_output: ExpectedOutput = Field(description="Expected extraction results")

class HeadingSample(BaseModel):
    """Sample heading from structure analysis"""
    text: str = Field(description="Heading text content")
    page: int = Field(description="Page number where heading appears")
    score: float = Field(description="Structure confidence score")
    font_size: float = Field(description="Font size in points")

class HeadingData(BaseModel):
    """Heading analysis data for a specific level"""
    count: int = Field(description="Total number of headings at this level")
    avg_score: float = Field(description="Average structure score")
    sample_headings: Optional[List[HeadingSample]] = Field(
        None,
        description="Sample headings for analysis"
    )

class FontAnalysis(BaseModel):
    """Font analysis data from document"""
    font_size: Optional[float] = Field(None, description="Primary font size for this level")
    total_fonts: Optional[int] = Field(None, description="Total number of fonts in document")
    size_range: Optional[List[float]] = Field(None, description="Min and max font sizes")
    median_size: Optional[float] = Field(None, description="Median font size")

class StructureAnalysisInput(BaseModel):
    """Input data for structure analysis"""
    document_name: str = Field(description="Name of the PDF document")
    document_pages: Optional[int] = Field(None, description="Total number of pages")
    analysis_level: int = Field(description="Heading level being analyzed")
    font_analysis: Optional[FontAnalysis] = Field(None, description="Font analysis data")
    heading_data: HeadingData = Field(description="Heading data for analysis")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_openai_function_schema(schema_name: str) -> Dict[str, Any]:
    """Get OpenAI function calling schema by name"""
    schemas = {
        "validation_result": {
            "name": "provide_validation_result",
            "description": "Provide structured validation of PDF extraction results",
            "parameters": VALIDATION_RESULT_SCHEMA
        },
        "extraction_strategy": {
            "name": "provide_extraction_strategy", 
            "description": "Provide detailed extraction strategy recommendations",
            "parameters": EXTRACTION_STRATEGY_SCHEMA
        }
    }
    
    if schema_name not in schemas:
        raise ValueError(f"Unknown schema: {schema_name}. Available: {list(schemas.keys())}")
    
    return schemas[schema_name]

def validate_response(schema_name: str, response_data: Dict[str, Any]) -> BaseModel:
    """Validate response data against Pydantic model"""
    models = {
        "validation_result": ValidationResult,
        "extraction_strategy": ExtractionStrategy,
        "structure_analysis_input": StructureAnalysisInput
    }
    
    if schema_name not in models:
        raise ValueError(f"Unknown model: {schema_name}. Available: {list(models.keys())}")
    
    model_class = models[schema_name]
    return model_class(**response_data)

def export_json_schemas() -> Dict[str, Dict[str, Any]]:
    """Export all JSON schemas for external use"""
    return {
        "validation_result": VALIDATION_RESULT_SCHEMA,
        "extraction_strategy": EXTRACTION_STRATEGY_SCHEMA,
        "structure_analysis_input": STRUCTURE_ANALYSIS_INPUT_SCHEMA
    }

if __name__ == "__main__":
    # Example usage and testing
    print("PDF Structure Analysis Schema Module")
    print("=" * 50)
    
    # Test schema export
    schemas = export_json_schemas()
    print(f"Available schemas: {list(schemas.keys())}")
    
    # Test Pydantic model creation
    sample_validation = ValidationResult(
        status="VALID",
        confidence=0.85,
        reason="Headings appear to be meaningful spell names",
        extraction_feasible=True,
        detected_patterns=["spell_names", "consistent_formatting"]
    )
    
    print(f"\nSample ValidationResult:")
    print(sample_validation.model_dump_json(indent=2))
