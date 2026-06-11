"""
Analyzer Module - Sistema de Analise de Projetos com ML
Pacote completo para analise de codigo e aprendizado continuo
"""

from .project_analyzer import (
    ProjectAnalyzer,
    AnalysisIssue,
    AnalysisResult,
    get_analyzer,
    analyze_project,
    generate_analysis_report
)

from .analyzer_ml import (
    AnalyzerML,
    get_analyzer_ml,
    record_analysis,
    record_feedback,
    get_prioritized_issues,
    get_confidence,
    get_learning_report
)

__all__ = [
    # Project Analyzer
    "ProjectAnalyzer",
    "AnalysisIssue",
    "AnalysisResult",
    "get_analyzer",
    "analyze_project",
    "generate_analysis_report",
    # ML System
    "AnalyzerML",
    "get_analyzer_ml",
    "record_analysis",
    "record_feedback",
    "get_prioritized_issues",
    "get_confidence",
    "get_learning_report",
]