#!/usr/bin/env python3
"""
RLS Audit Script — Automated Row-Level Security Violation Detection

This script scans Python route files in app/rutas/ for RLS violations using AST parsing.
It detects:
- CRITICAL: Queries on multi-tenant tables without taller_id filter
- HIGH: Route handlers without @require_auth decorator
- HIGH: Repository instantiation without taller_id parameter

Usage:
    python scripts/rls_audit.py
    pytest tests/test_rls_audit.py

Exit codes:
    0: No violations found
    1: Critical or high violations found
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class RLSViolation:
    """
    Represents a Row-Level Security violation detected in code.
    
    Attributes:
        file_path: Relative path to the file containing the violation
        line_number: Line number where the violation occurs
        severity: Severity level (CRITICAL, HIGH, MEDIUM)
        violation_type: Type of violation detected
        description: Human-readable description of the violation
        code_snippet: Code snippet showing the violation
    """
    file_path: str
    line_number: int
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    violation_type: str
    description: str
    code_snippet: str


class RLSAuditor:
    """
    AST-based auditor for detecting Row-Level Security violations in FastAPI routes.
    
    This auditor scans Python files in app/rutas/ and detects:
    1. Queries on multi-tenant tables without taller_id filter (CRITICAL)
    2. Route handlers without @require_auth decorator (HIGH)
    3. Repository instantiation without taller_id parameter (HIGH)
    """
    
    # Multi-tenant tables that MUST have taller_id filter
    MULTI_TENANT_TABLES = [
        "Ticket",
        "MovimientoCaja",
        "LogNotificacion",
        "Vehiculo",
        "Cliente",
        "Mecanico",
        "TicketProceso",
        "TicketRepuesto",
        "TicketFoto",
        "TicketCompra",
        "TicketCobro",
        "Cita",
        "ConfiguracionTaller",
        "ConfiguracionCobroRapido",
        "Notificacion",
        "CambioMovimientoCaja",
        "User",
    ]
    
    # Repositories that require taller_id parameter
    TENANT_REPOSITORIES = [
        "TicketRepository",
        "VehiculoRepository",
        "MecanicoRepository",
        "CitaRepository",
    ]
    
    # HTTP methods that define route handlers
    ROUTE_DECORATORS = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
    ]
    
    def __init__(self):
        """Initialize the RLS auditor."""
        self.violations: list[RLSViolation] = []
    
    def scan_routes(self, routes_dir: str) -> list[RLSViolation]:
        """
        Scans all Python files in routes_dir for RLS violations.
        
        Args:
            routes_dir: Path to the routes directory (e.g., "app/rutas/")
        
        Returns:
            List of RLSViolation objects found during scanning
        """
        self.violations = []
        routes_path = Path(routes_dir)
        
        if not routes_path.exists():
            raise FileNotFoundError(f"Routes directory not found: {routes_dir}")
        
        # Scan all Python files in the directory
        for py_file in routes_path.rglob("*.py"):
            # Skip __init__.py and __pycache__
            if py_file.name.startswith("__"):
                continue
            
            self._scan_file(py_file)
        
        return self.violations
    
    def _scan_file(self, file_path: Path) -> None:
        """
        Scans a single Python file for RLS violations using AST parsing.
        
        Args:
            file_path: Path to the Python file to scan
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
                source_lines = source_code.splitlines()
            
            # Parse the file into an AST
            tree = ast.parse(source_code, filename=str(file_path))
            
            # Check if router has global auth dependency
            has_router_auth = self._has_router_level_auth(source_code)
            
            # Analyze the AST
            # Use forward slashes for consistency across platforms
            relative_path = str(file_path).replace("\\", "/")
            self._analyze_ast(tree, relative_path, source_lines, has_router_auth)
            
        except SyntaxError as e:
            # Skip files with syntax errors (they won't run anyway)
            print(f"Warning: Syntax error in {file_path}: {e}")
        except Exception as e:
            import traceback
            print(f"Warning: Error scanning {file_path}: {e}")
            # Uncomment for debugging:
            # traceback.print_exc()
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, source_lines: list[str], has_router_auth: bool = False) -> None:
        """
        Analyzes an AST tree for RLS violations.
        
        Args:
            tree: AST tree to analyze
            file_path: Relative path to the file being analyzed
            source_lines: Source code lines for extracting snippets
            has_router_auth: Whether the router has global auth dependency
        """
        # Find all function definitions (potential route handlers)
        # Note: FastAPI routes can be either sync (FunctionDef) or async (AsyncFunctionDef)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_route_handler(node, file_path, source_lines, has_router_auth)
                self._check_queries_in_function(node, file_path, source_lines)
                self._check_repository_instantiation(node, file_path, source_lines)
    
    def _check_route_handler(
        self, func_node: ast.FunctionDef, file_path: str, source_lines: list[str], has_router_auth: bool = False
    ) -> None:
        """
        Checks if a route handler has @require_auth decorator.
        
        Args:
            func_node: AST node representing a function definition
            file_path: Relative path to the file
            source_lines: Source code lines for extracting snippets
            has_router_auth: Whether the router has global auth dependency
        """
        # Check if function has route decorator (@router.get, @router.post, etc.)
        has_route_decorator = False
        has_require_auth = False
        
        for decorator in func_node.decorator_list:
            # Check for @router.get, @router.post, etc.
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "router"
                        and decorator.func.attr in self.ROUTE_DECORATORS
                    ):
                        has_route_decorator = True
            
            # Check for @require_auth
            if isinstance(decorator, ast.Name) and decorator.id == "require_auth":
                has_require_auth = True
        
        # If router has global auth, consider all endpoints protected
        if has_router_auth:
            has_require_auth = True
        
        # If it's a route handler without @require_auth, report violation
        # Exception: webhook endpoints and public endpoints
        if has_route_decorator and not has_require_auth:
            # Check if it's a public endpoint (webhook, health, etc.)
            func_name = func_node.name
            if self._is_public_endpoint(func_name):
                return
            
            line_number = func_node.lineno
            code_snippet = self._get_code_snippet(source_lines, line_number)
            
            self.violations.append(
                RLSViolation(
                    file_path=file_path,
                    line_number=line_number,
                    severity="HIGH",
                    violation_type="MISSING_AUTH",
                    description=f"Route handler '{func_name}' missing @require_auth decorator",
                    code_snippet=code_snippet,
                )
            )
    
    def _check_queries_in_function(
        self, func_node: ast.FunctionDef, file_path: str, source_lines: list[str]
    ) -> None:
        """
        Checks if queries on multi-tenant tables have taller_id filter.
        
        Args:
            func_node: AST node representing a function definition
            file_path: Relative path to the file
            source_lines: Source code lines for extracting snippets
        """
        # Walk through all nodes in the function
        for node in ast.walk(func_node):
            # Look for db.query(Table) calls
            if isinstance(node, ast.Call):
                if self._is_db_query_call(node):
                    table_name = self._extract_table_name(node)
                    
                    if table_name in self.MULTI_TENANT_TABLES:
                        # Check if there's a taller_id filter in the query chain
                        if not self._has_taller_id_filter(node, func_node):
                            line_number = node.lineno
                            code_snippet = self._get_code_snippet(source_lines, line_number)
                            
                            self.violations.append(
                                RLSViolation(
                                    file_path=file_path,
                                    line_number=line_number,
                                    severity="CRITICAL",
                                    violation_type="MISSING_TALLER_FILTER",
                                    description=f"Query on {table_name} without taller_id filter",
                                    code_snippet=code_snippet,
                                )
                            )
                
                # Also check for helper function calls that might need taller_id
                # Look for calls to functions that query multi-tenant data
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    # Check if it's a helper function that queries multi-tenant data
                    if any(pattern in func_name.lower() for pattern in ["_base_query", "_sumar_por_tipo", "_detalle"]):
                        # Check if taller_id is passed as argument
                        has_taller_id_arg = False
                        for keyword in node.keywords:
                            if keyword.arg == "taller_id":
                                has_taller_id_arg = True
                                break
                        
                        # Also check positional args (look for request.state.taller_id)
                        for arg in node.args:
                            try:
                                arg_source = ast.unparse(arg)
                                if "taller_id" in arg_source:
                                    has_taller_id_arg = True
                                    break
                            except Exception:
                                pass
                        
                        if not has_taller_id_arg:
                            line_number = node.lineno
                            code_snippet = self._get_code_snippet(source_lines, line_number)
                            
                            self.violations.append(
                                RLSViolation(
                                    file_path=file_path,
                                    line_number=line_number,
                                    severity="CRITICAL",
                                    violation_type="MISSING_TALLER_PARAM",
                                    description=f"Helper function '{func_name}' called without taller_id parameter",
                                    code_snippet=code_snippet,
                                )
                            )
    
    def _check_repository_instantiation(
        self, func_node: ast.FunctionDef, file_path: str, source_lines: list[str]
    ) -> None:
        """
        Checks if repository instantiation includes taller_id parameter.
        
        Args:
            func_node: AST node representing a function definition
            file_path: Relative path to the file
            source_lines: Source code lines for extracting snippets
        """
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Check if it's a repository instantiation
                if isinstance(node.func, ast.Name):
                    repo_name = node.func.id
                    
                    if repo_name in self.TENANT_REPOSITORIES:
                        # Check if taller_id is passed as argument
                        has_taller_id = False
                        
                        # Check keyword arguments
                        for keyword in node.keywords:
                            if keyword.arg == "taller_id":
                                has_taller_id = True
                                break
                        
                        if not has_taller_id:
                            line_number = node.lineno
                            code_snippet = self._get_code_snippet(source_lines, line_number)
                            
                            self.violations.append(
                                RLSViolation(
                                    file_path=file_path,
                                    line_number=line_number,
                                    severity="HIGH",
                                    violation_type="MISSING_TALLER_PARAM",
                                    description=f"{repo_name} instantiated without taller_id parameter",
                                    code_snippet=code_snippet,
                                )
                            )
    
    def _is_db_query_call(self, node: ast.Call) -> bool:
        """
        Checks if a call node is a db.query() call.
        
        Args:
            node: AST Call node
        
        Returns:
            True if it's a db.query() call
        """
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
                and node.func.attr == "query"
            ):
                return True
        return False
    
    def _extract_table_name(self, node: ast.Call) -> str | None:
        """
        Extracts the table name from a db.query(Table) call.
        
        Args:
            node: AST Call node representing db.query()
        
        Returns:
            Table name or None if not found
        """
        if node.args and len(node.args) > 0:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Name):
                return first_arg.id
        return None
    
    def _has_taller_id_filter(self, query_node: ast.Call, func_node: ast.FunctionDef) -> bool:
        """
        Checks if a query has a taller_id filter in its chain.
        
        This is a heuristic check that looks for:
        - .filter(...taller_id...) in the same statement or nearby
        - TenantRepository usage (which auto-filters)
        - SUPER_ADMIN context (which doesn't need tenant filtering)
        - Helper functions that accept taller_id parameter AND use it in filters
        
        Args:
            query_node: AST Call node representing db.query()
            func_node: AST FunctionDef node containing the query
        
        Returns:
            True if taller_id filter is present or not needed
        """
        # Check if function uses TenantRepository (auto-filters)
        try:
            func_source = ast.unparse(func_node)
            if "Repository(" in func_source and "taller_id" in func_source:
                return True
        except Exception:
            pass
        
        # Check if it's in a SUPER_ADMIN context
        if "super_admin" in func_node.name.lower():
            return True
        
        # Check if function has taller_id parameter AND uses it in a filter
        has_taller_id_param = False
        for arg in func_node.args.args:
            if arg.arg == "taller_id":
                has_taller_id_param = True
                break
        
        # If function has taller_id parameter, check if it's used in a filter
        if has_taller_id_param:
            for node in ast.walk(func_node):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "filter":
                        try:
                            filter_source = ast.unparse(node)
                            if "taller_id" in filter_source:
                                return True
                        except Exception:
                            pass
        
        # Check if there's a .filter() call with taller_id in the same statement
        # We need to find the statement containing this query and check if it has a filter
        try:
            # Get the line number of the query
            query_line = query_node.lineno
            
            # Look for filter calls on nearby lines (within 5 lines)
            for node in ast.walk(func_node):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "filter":
                        if abs(node.lineno - query_line) <= 5:
                            try:
                                filter_source = ast.unparse(node)
                                if "taller_id" in filter_source:
                                    return True
                            except Exception:
                                pass
        except Exception:
            pass
        
        return False
    
    def _is_public_endpoint(self, func_name: str) -> bool:
        """
        Checks if a function is a known public endpoint that doesn't need auth.
        
        Args:
            func_name: Name of the function
        
        Returns:
            True if it's a public endpoint
        """
        public_patterns = [
            "webhook",
            "verificar_webhook",
            "health",
            "login",
            "refresh",
            "forgot_password",
            "reset_password",
        ]
        
        func_lower = func_name.lower()
        return any(pattern in func_lower for pattern in public_patterns)
    
    def _has_router_level_auth(self, source_code: str) -> bool:
        """
        Checks if the router has global authentication dependency.
        
        Args:
            source_code: Source code of the file
        
        Returns:
            True if router has dependencies=[Depends(require_jwt_auth)] or similar
        """
        # Check for router-level auth patterns
        auth_patterns = [
            "dependencies=[Depends(require_jwt_auth)]",
            "dependencies=[Depends(requerir_password_admin)]",
        ]
        
        return any(pattern in source_code for pattern in auth_patterns)
    
    def _get_code_snippet(self, source_lines: list[str], line_number: int) -> str:
        """
        Extracts a code snippet around the given line number.
        
        Args:
            source_lines: List of source code lines
            line_number: Line number (1-indexed)
        
        Returns:
            Code snippet (up to 3 lines)
        """
        if not source_lines:
            return ""
        
        # Convert to 0-indexed
        idx = line_number - 1
        
        # Ensure idx is within bounds
        if idx < 0 or idx >= len(source_lines):
            return ""
        
        # Get up to 3 lines of context
        start = max(0, idx)
        end = min(len(source_lines), idx + 3)
        
        snippet_lines = source_lines[start:end]
        return "\n".join(snippet_lines).strip()
    
    def generate_report(self, violations: list[RLSViolation]) -> str:
        """
        Generates a human-readable report of violations.
        
        Args:
            violations: List of RLSViolation objects
        
        Returns:
            Formatted report string
        """
        if not violations:
            return "NO RLS VIOLATIONS FOUND\n"
        
        # Group violations by severity
        critical = [v for v in violations if v.severity == "CRITICAL"]
        high = [v for v in violations if v.severity == "HIGH"]
        medium = [v for v in violations if v.severity == "MEDIUM"]
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RLS AUDIT REPORT — Row-Level Security Violations")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Total violations: {len(violations)}")
        report_lines.append(f"  CRITICAL: {len(critical)}")
        report_lines.append(f"  HIGH: {len(high)}")
        report_lines.append(f"  MEDIUM: {len(medium)}")
        report_lines.append("")
        
        # Report critical violations
        if critical:
            report_lines.append("CRITICAL VIOLATIONS")
            report_lines.append("-" * 80)
            for v in critical:
                report_lines.append(f"  File: {v.file_path}:{v.line_number}")
                report_lines.append(f"  Type: {v.violation_type}")
                report_lines.append(f"  Description: {v.description}")
                report_lines.append(f"  Code: {v.code_snippet}")
                report_lines.append("")
        
        # Report high violations
        if high:
            report_lines.append("HIGH VIOLATIONS")
            report_lines.append("-" * 80)
            for v in high:
                report_lines.append(f"  File: {v.file_path}:{v.line_number}")
                report_lines.append(f"  Type: {v.violation_type}")
                report_lines.append(f"  Description: {v.description}")
                report_lines.append(f"  Code: {v.code_snippet}")
                report_lines.append("")
        
        # Report medium violations
        if medium:
            report_lines.append("MEDIUM VIOLATIONS")
            report_lines.append("-" * 80)
            for v in medium:
                report_lines.append(f"  File: {v.file_path}:{v.line_number}")
                report_lines.append(f"  Type: {v.violation_type}")
                report_lines.append(f"  Description: {v.description}")
                report_lines.append(f"  Code: {v.code_snippet}")
                report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("RECOMMENDATIONS:")
        report_lines.append("=" * 80)
        report_lines.append("1. Add @require_auth decorator to all route handlers")
        report_lines.append("2. Add .filter(Table.taller_id == taller_id) to all multi-tenant queries")
        report_lines.append("3. Pass taller_id=request.state.taller_id when instantiating repositories")
        report_lines.append("4. Use TenantRepository base class for automatic filtering")
        report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Main entry point for the RLS audit script."""
    auditor = RLSAuditor()
    
    # Scan the routes directory
    routes_dir = os.path.join("app", "rutas")
    violations = auditor.scan_routes(routes_dir)
    
    # Generate and print report
    report = auditor.generate_report(violations)
    print(report)
    
    # Exit with non-zero code if violations found
    if violations:
        critical_or_high = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
        if critical_or_high:
            exit(1)
    
    exit(0)


if __name__ == "__main__":
    main()
