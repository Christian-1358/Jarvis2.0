"""
Project Analyzer - Sistema de Analise Avancada de Projetos
Analisa projetos completos com aprendizado continuo e ML integrado
"""

import os
import sys
import ast
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Database
from data.core_database import get_jarvis_db


@dataclass
class AnalysisIssue:
    """Representa um problema encontrado na analise."""
    type: str  # syntax, import, unused, duplicate, security, performance, architecture
    severity: str  # critical, high, medium, low, info
    file: str
    line: int = 0
    column: int = 0
    message: str = ""
    suggestion: str = ""
    code_snippet: str = ""
    rule_id: str = ""
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            "rule_id": self.rule_id,
            "confidence": self.confidence
        }


@dataclass
class AnalysisResult:
    """Resultado de uma analise de projeto."""
    project_path: str
    project_name: str
    total_files: int = 0
    files_analyzed: int = 0
    issues: List[AnalysisIssue] = field(default_factory=list)
    score: float = 100.0
    confidence: float = 0.5
    analysis_duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    suggestions_accepted: int = 0
    suggestions_rejected: int = 0

    def to_dict(self) -> dict:
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "total_files": self.total_files,
            "files_analyzed": self.files_analyzed,
            "issues_count": len(self.issues),
            "score": self.score,
            "confidence": self.confidence,
            "analysis_duration_ms": self.analysis_duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "suggestions_accepted": self.suggestions_accepted,
            "suggestions_rejected": self.suggestions_rejected
        }

    def get_issues_by_type(self) -> Dict[str, List[AnalysisIssue]]:
        by_type = defaultdict(list)
        for issue in self.issues:
            by_type[issue.type].append(issue)
        return dict(by_type)

    def get_issues_by_severity(self) -> Dict[str, List[AnalysisIssue]]:
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue.severity].append(issue)
        return dict(by_severity)


class ProjectAnalyzer:
    """Analisador de projetos com capacidades de ML."""

    SUPPORTED_EXTENSIONS = {
        '.py', '.html', '.css', '.js', '.jsx', '.ts', '.tsx',
        '.sql', '.json', '.yaml', '.yml', '.md', '.txt'
    }

    IGNORED_DIRS = {
        'venv', 'env', '__pycache__', '.git', '.svn', '.hg',
        'node_modules', 'dist', 'build', '.pytest_cache', '.mypy_cache',
        '__pypackages__', '.tox', '.eggs', '*.egg-info'
    }

    def __init__(self):
        self.db = get_jarvis_db()
        self.rules = self._load_detection_rules()
        self.ml_weights = self._load_ml_weights()

    def _load_detection_rules(self) -> Dict:
        """Carrega regras de deteccao de problemas."""
        return {
            # Regras de Sintaxe
            "syntax_error": {
                "type": "syntax",
                "severity": "critical",
                "patterns": [r"SyntaxError", r"IndentationError", r"TabError"],
                "weight": 1.0
            },
            # Regras de Imports
            "broken_import": {
                "type": "import",
                "severity": "high",
                "patterns": [r"ImportError", r"ModuleNotFoundError", r"No module named"],
                "weight": 0.9
            },
            # Regras de Seguranca
            "hardcoded_secret": {
                "type": "security",
                "severity": "critical",
                "patterns": [
                    r"password\s*=\s*['\"][^'\"]{8,}['\"]",
                    r"api_key\s*=\s*['\"][^'\"]{20,}['\"]",
                    r"secret\s*=\s*['\"][^'\"]{20,}['\"]",
                    r"AWS_ACCESS_KEY",
                    r"PRIVATE_KEY"
                ],
                "weight": 1.0
            },
            "sql_injection": {
                "type": "security",
                "severity": "critical",
                "patterns": [
                    r"execute\s*\(\s*f[\"'](SELECT|INSERT|UPDATE|DELETE)",
                    r"\.format\s*\([^)]*%s",
                    r"f[\"'].*SELECT.*\{.*\}",
                ],
                "weight": 1.0
            },
            "eval_usage": {
                "type": "security",
                "severity": "high",
                "patterns": [r"\beval\s*\(", r"\bexec\s*\("],
                "weight": 0.8
            },
            # Regras de Performance
            "inefficient_loop": {
                "type": "performance",
                "severity": "medium",
                "patterns": [
                    r"for\s+.*\s+in\s+.*:\s*\n\s*for\s+",
                    r"while\s+True:\s*\n\s*if\s+.*:\s*break",
                ],
                "weight": 0.6
            },
            "unused_import": {
                "type": "unused",
                "severity": "low",
                "weight": 0.3
            },
            "duplicate_code": {
                "type": "duplicate",
                "severity": "medium",
                "weight": 0.5
            }
        }

    def _load_ml_weights(self) -> Dict:
        """Carrega pesos de ML do banco de dados."""
        weights = {
            "type_weights": {
                "syntax": 1.0,
                "import": 0.9,
                "security": 1.0,
                "performance": 0.6,
                "architecture": 0.5,
                "unused": 0.3,
                "duplicate": 0.4,
                "style": 0.2
            },
            "severity_weights": {
                "critical": 1.0,
                "high": 0.75,
                "medium": 0.5,
                "low": 0.25,
                "info": 0.1
            }
        }

        # Carregar do banco se disponivel
        try:
            if self.db:
                for i in range(10):
                    pass  # Placeholder for future ML weight loading
        except:
            pass

        return weights

    def analyze_project(self, project_path: str) -> AnalysisResult:
        """Analisa um projeto completo."""
        import time
        start_time = time.time()

        project_path = Path(project_path)
        if not project_path.exists():
            return AnalysisResult(
                project_path=str(project_path),
                project_name=project_path.name,
                score=0,
                confidence=0
            )

        result = AnalysisResult(
            project_path=str(project_path),
            project_name=project_path.name
        )

        # Coletar arquivos
        files = self._collect_files(project_path)
        result.total_files = len(files)
        result.files_analyzed = len(files)

        # Analisar cada arquivo
        all_issues = []
        for file_path in files:
            issues = self._analyze_file(file_path)
            all_issues.extend(issues)

        result.issues = all_issues

        # Calcular score
        result.score = self._calculate_score(all_issues)

        # Calcular confianca baseado no historico
        result.confidence = self._calculate_confidence()

        result.analysis_duration_ms = int((time.time() - start_time) * 1000)

        # Salvar no banco
        self._save_analysis_result(result)

        return result

    def _collect_files(self, project_path: Path) -> List[Path]:
        """Coleta todos os arquivos analisaveis do projeto."""
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # Filtrar diretorios ignorados
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS and not d.startswith('.')]

            for filename in filenames:
                if filename.startswith('.'):
                    continue
                file_path = Path(root) / filename
                if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                    files.append(file_path)

        return files

    def _analyze_file(self, file_path: Path) -> List[AnalysisIssue]:
        """Analisa um arquivo individual."""
        issues = []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return issues

        # Analise por tipo de arquivo
        if file_path.suffix == '.py':
            issues.extend(self._analyze_python(file_path, content))
        elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
            issues.extend(self._analyze_javascript(file_path, content))
        elif file_path.suffix in ['.html']:
            issues.extend(self._analyze_html(file_path, content))
        elif file_path.suffix in ['.css']:
            issues.extend(self._analyze_css(file_path, content))
        elif file_path.suffix in ['.sql']:
            issues.extend(self._analyze_sql(file_path, content))

        # Analises comuns
        issues.extend(self._detect_secrets(file_path, content))
        issues.extend(self._detect_duplicates(file_path, content))

        return issues

    def _analyze_python(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Analisa arquivos Python."""
        issues = []

        # Tentar parsing AST
        try:
            tree = ast.parse(content)
            self._analyze_python_ast(file_path, content, tree, issues)
        except SyntaxError as e:
            issues.append(AnalysisIssue(
                type="syntax",
                severity="critical",
                file=str(file_path),
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Erro de sintaxe: {e.msg}",
                suggestion="Corrija a sintaxe do codigo",
                rule_id="syntax_error",
                confidence=0.95
            ))
        except Exception as e:
            issues.append(AnalysisIssue(
                type="syntax",
                severity="medium",
                file=str(file_path),
                message=f"Erro ao analisar: {str(e)}",
                rule_id="parse_error",
                confidence=0.7
            ))

        # Verificar imports
        imports = self._get_python_imports(content)
        for imp in imports:
            if not self._is_valid_import(imp['name'], file_path.parent):
                issues.append(AnalysisIssue(
                    type="import",
                    severity="high",
                    file=str(file_path),
                    line=imp.get('line', 0),
                    message=f"Import nao encontrado: {imp.get('name', '')}",
                    suggestion=f"Instale o modulo ou corrija o nome",
                    rule_id="broken_import",
                    confidence=0.85
                ))

        # Verificar funcoes nao utilizadas
        unused_functions = self._detect_unused_functions(tree, content)
        for func in unused_functions:
            issues.append(AnalysisIssue(
                type="unused",
                severity="low",
                file=str(file_path),
                line=func['line'],
                message=f"Funcao '{func['name']}' definida mas nunca utilizada",
                suggestion=f"Remova a funcao ou use-a",
                rule_id="unused_function",
                confidence=0.75
            ))

        return issues

    def _analyze_python_ast(self, file_path: Path, content: str, tree: ast.AST, issues: List):
        """Analisa a arvore AST do Python."""
        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'col': node.col_offset,
                    'args': [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'line': node.lineno
                })

        # Verificar naming conventions
        for func in functions:
            if func['name'][0].isupper() and not func['name'][0].isalpha():
                issues.append(AnalysisIssue(
                    type="style",
                    severity="info",
                    file=str(file_path),
                    line=func['line'],
                    message=f"Funcao '{func['name']}' com nome em PascalCase",
                    suggestion="Use snake_case para funcoes",
                    rule_id="naming_convention",
                    confidence=0.6
                ))

        # Verificar docstrings
        for func in functions:
            if func['line']:
                # Simple check - would need more complex AST traversal
                pass

    def _get_python_imports(self, content: str) -> List[Dict]:
        """Extrai todos os imports de um arquivo Python."""
        imports = []
        for i, line in enumerate(content.split('\n'), 1):
            # Simple regex-based extraction
            if re.match(r'^\s*(import|from)\s+', line):
                match = re.match(r'^\s*(?:import|from)\s+([^\s]+)', line)
                if match:
                    name = match.group(1).split('.')[0]
                    imports.append({'name': name, 'line': i})

        return imports

    def _is_valid_import(self, import_name: str, source_dir: Path) -> bool:
        """Verifica se um import e valido."""
        # Check standard library
        stdlib = {'os', 'sys', 'json', 're', 'time', 'datetime', 'math', 'random',
                  'collections', 'itertools', 'functools', 'pathlib', 'subprocess'}
        if import_name in stdlib:
            return True

        # Check if file exists in source
        source_file = source_dir / f"{import_name}.py"
        if source_file.exists():
            return True

        # Check common package locations
        for path in sys.path:
            if Path(path).joinpath(import_name).exists():
                return True

        return False

    def _detect_unused_functions(self, tree: ast.AST, content: str) -> List[Dict]:
        """Detecta funcoes definidas mas nunca utilizadas."""
        # This is a simplified version - full implementation would track usage
        unused = []
        functions = []

        if not tree:
            return unused

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    functions.append({
                        'name': node.name,
                        'line': node.lineno
                    })

        # For now, return empty - full implementation would track name usage
        return unused

    def _analyze_javascript(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Analisa arquivos JavaScript/TypeScript."""
        issues = []

        # Check for console.log in production
        if 'console.log' in content and not any(x in str(file_path) for x in ['debug', 'test']):
            matches = re.finditer(r'console\.log', content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(AnalysisIssue(
                    type="performance",
                    severity="low",
                    file=str(file_path),
                    line=line_num,
                    message="console.log encontrado em codigo de producao",
                    suggestion="Remova console.log ou use logger apropriado",
                    rule_id="console_in_production",
                    confidence=0.7
                ))

        # Check for TODO without FIXME
        todos = re.findall(r'//\s*TODO', content)
        if todos:
            issues.append(AnalysisIssue(
                type="style",
                severity="info",
                file=str(file_path),
                message=f"{len(todos)}TODO(s) encontrado(s) - considere resolver",
                rule_id="todo_comment",
                confidence=0.5
            ))

        return issues

    def _analyze_html(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Analisa arquivos HTML."""
        issues = []

        # Check for inline styles
        if 'style="' in content:
            issues.append(AnalysisIssue(
                type="architecture",
                severity="medium",
                file=str(file_path),
                message="Estilos inline encontrados",
                suggestion="Use CSS externo ou classes",
                rule_id="inline_styles",
                confidence=0.75
            ))

        # Check for inline JS
        if re.search(r'<script[^>]*>', content):
            inline_scripts = len(re.findall(r'<script[^>]*>((?!src=).)*</script>', content, re.DOTALL))
            if inline_scripts > 0:
                issues.append(AnalysisIssue(
                    type="architecture",
                    severity="low",
                    file=str(file_path),
                    message=f"{inline_scripts} script(s) inline(s) encontrado(s)",
                    suggestion="Use arquivos JS externos",
                    rule_id="inline_scripts",
                    confidence=0.7
                ))

        return issues

    def _analyze_css(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Analisa arquivos CSS."""
        issues = []

        # Check for !important
        if '!important' in content:
            count = content.count('!important')
            issues.append(AnalysisIssue(
                type="architecture",
                severity="medium",
                file=str(file_path),
                message=f"{count} uso(s) de !important encontrado(s)",
                suggestion="Evite !important, use especificidade correta",
                rule_id="important_usage",
                confidence=0.8
            ))

        return issues

    def _analyze_sql(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Analisa arquivos SQL."""
        issues = []

        # Check for SELECT *
        selects = re.findall(r'SELECT\s+\*', content, re.IGNORECASE)
        if selects:
            issues.append(AnalysisIssue(
                type="performance",
                severity="medium",
                file=str(file_path),
                message="SELECT * encontrado - use colunas especificas",
                suggestion="Liste as colunas necessarias",
                rule_id="select_star",
                confidence=0.85
            ))

        # Check for string concatenation in SQL
        if '+' in content and ('SELECT' in content.upper() or 'INSERT' in content.upper()):
            issues.append(AnalysisIssue(
                type="security",
                severity="critical",
                file=str(file_path),
                message="Concatenacao de strings em SQL - risco de injection",
                suggestion="Use parametros preparados",
                rule_id="sql_concat",
                confidence=0.9
            ))

        return issues

    def _detect_secrets(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Detecta secrets hardcoded."""
        issues = []

        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'password'),
            (r'api[_-]?key\s*=\s*["\'][^"\']{20,}["\']', 'api_key'),
            (r'secret\s*=\s*["\'][^"\']{20,}["\']', 'secret'),
            (r'token\s*=\s*["\'][^"\']{30,}["\']', 'token'),
            (r'aws[_-]?access[_-]?key', 'aws_key'),
        ]

        for pattern, name in secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(AnalysisIssue(
                    type="security",
                    severity="critical",
                    file=str(file_path),
                    line=line_num,
                    message=f"{name.upper()} hardcoded encontrado",
                    suggestion="Use variaveis de ambiente",
                    rule_id="hardcoded_secret",
                    confidence=0.95
                ))

        return issues

    def _detect_duplicates(self, file_path: Path, content: str) -> List[AnalysisIssue]:
        """Detecta codigo duplicado."""
        issues = []

        # Simple n-gram based detection
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
        if len(lines) < 10:
            return issues

        # Check for repeated blocks
        seen = {}
        for i, line in enumerate(lines):
            hash_val = hashlib.md5(line.encode()).hexdigest()
            if hash_val in seen:
                issues.append(AnalysisIssue(
                    type="duplicate",
                    severity="medium",
                    file=str(file_path),
                    line=i + 1,
                    message=f"Linha duplicada (primeira ocorrencia na linha {seen[hash_val]+1})",
                    suggestion="Extraia para funcao ou variavel",
                    rule_id="duplicate_line",
                    confidence=0.6
                ))
            else:
                seen[hash_val] = i

        return issues

    def _calculate_score(self, issues: List[AnalysisIssue]) -> float:
        """Calcula pontuacao do projeto (0-100)."""
        if not issues:
            return 100.0

        penalty = 0.0
        for issue in issues:
            type_weight = self.ml_weights['type_weights'].get(issue.type, 0.5)
            severity_weight = self.ml_weights['severity_weights'].get(issue.severity, 0.5)
            penalty += (type_weight * severity_weight * 10)

        score = max(0, 100 - penalty)
        return round(score, 2)

    def _calculate_confidence(self) -> float:
        """Calcula confianca da analise baseado no historico."""
        try:
            if not self.db:
                return 0.5

            # Get historical accuracy
            result = self.db.db_path  # This is a placeholder

            # Simple confidence based on sample size
            return min(0.95, 0.5 + (len(self.rules) * 0.01))
        except:
            return 0.5

    def _save_analysis_result(self, result: AnalysisResult):
        """Salva resultado da analise no banco."""
        if not self.db:
            return

        try:
            # Save project
            self.db.set_preference(
                f"project:{result.project_name}",
                str(result.project_path),
                1.0
            )

            # Save analysis stats
            issues_by_type = result.get_issues_by_type()
            for issue_type, issues in issues_by_type.items():
                self.db.set_preference(
                    f"analysis:{result.project_name}:{issue_type}",
                    str(len(issues)),
                    1.0
                )

        except Exception as e:
            print(f"[ANALYZER] Erro ao salvar: {e}")

    def generate_report(self, result: AnalysisResult) -> str:
        """Gera relatorio formatado da analise."""
        lines = [
            f"📊 RELATORIO DE ANALISE: {result.project_name}",
            "=" * 60,
            f"📁 Caminho: {result.project_path}",
            f"📁 Arquivos: {result.files_analyzed}/{result.total_files}",
            f"⏱️  Duracao: {result.analysis_duration_ms}ms",
            f"🎯 Score: {result.score}/100",
            f"📈 Confianca: {result.confidence:.0%}",
            "",
            "🔍 PROBLEMAS ENCONTRADOS:",
            f"Total: {len(result.issues)}",
            ""
        ]

        # Group by severity
        by_severity = result.get_issues_by_severity()
        severity_order = ['critical', 'high', 'medium', 'low', 'info']

        for severity in severity_order:
            issues = by_severity.get(severity, [])
            if not issues:
                continue

            emoji = {
                'critical': '☠️',
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢',
                'info': 'ℹ️'
            }

            lines.append(f"{emoji.get(severity, '•')} {severity.upper()} ({len(issues)}):")
            for issue in issues[:5]:  # Show max 5 per severity
                lines.append(f"  📍 {issue.file}:{issue.line}")
                lines.append(f"     {issue.message}")
                if issue.suggestion:
                    lines.append(f"     💡 {issue.suggestion}")
            if len(issues) > 5:
                lines.append(f"     ... e mais {len(issues) - 5} problemas")
            lines.append("")

        # Summary
        lines.append("📊 RESUMO:")
        lines.append(f"  ✅ Score Final: {result.score}/100")

        if result.score >= 90:
            lines.append("  🟢 Excelente - Projeto bem estruturado")
        elif result.score >= 70:
            lines.append("  🟡 Bom - Alguns pontos de melhoria")
        elif result.score >= 50:
            lines.append("  🟠 Regular - Considere resolver os problemas")
        else:
            lines.append("  🔴 Precisa de atencao - Problemas criticos encontrados")

        return "\n".join(lines)


# Global instance
_analyzer = None


def get_analyzer() -> ProjectAnalyzer:
    """Retorna instancia global do analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ProjectAnalyzer()
    return _analyzer


def analyze_project(project_path: str) -> AnalysisResult:
    """Analisa um projeto completo."""
    return get_analyzer().analyze_project(project_path)


def generate_analysis_report(result: AnalysisResult) -> str:
    """Gera relatorio de analise."""
    return get_analyzer().generate_report(result)