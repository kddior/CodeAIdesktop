# tools/repo_read_tool.py

"""
Repo Read Tool - Read files from repository
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class RepoReadTool:
    """
    Read files from repository

    Handles:
    - Reading file content
    - Syntax highlighting metadata
    - File statistics
    - Error handling
    """

    def __init__(self, repo_path: str = None):
        """
        Initialize repo read tool

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path or os.getcwd()
        print(f"📖 Repo Read Tool initialized: {self.repo_path}")

    def read_file(
        self,
        file_path: str,
        max_lines: int = None,
        start_line: int = 1,
        end_line: int = None
    ) -> Dict[str, Any]:
        """
        Read file from repository

        Args:
            file_path: Relative or absolute path to file
            max_lines: Maximum lines to read (None = all)
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (None = end of file)

        Returns:
            {
                'success': bool,
                'content': str,
                'path': str,
                'language': str,
                'lines': int,
                'size_bytes': int,
                'error': str (if failed)
            }
        """
        try:
            # Resolve path
            if os.path.isabs(file_path):
                full_path = file_path
            else:
                full_path = os.path.join(self.repo_path, file_path)

            # Check file exists
            if not os.path.exists(full_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }

            # Check it's a file
            if not os.path.isfile(full_path):
                return {
                    'success': False,
                    'error': f'Path is not a file: {file_path}'
                }

            # Get file stats
            size_bytes = os.path.getsize(full_path)
            file_ext = os.path.splitext(file_path)[1]
            language = self._extension_to_language(file_ext)

            # Read content
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Apply line range
            if end_line is None:
                end_line = total_lines

            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)

            selected_lines = lines[start_idx:end_idx]

            # Apply max_lines limit
            if max_lines and len(selected_lines) > max_lines:
                selected_lines = selected_lines[:max_lines]

            content = ''.join(selected_lines)

            return {
                'success': True,
                'content': content,
                'path': file_path,
                'full_path': full_path,
                'language': language,
                'total_lines': total_lines,
                'lines_read': len(selected_lines),
                'start_line': start_line,
                'end_line': end_idx,
                'size_bytes': size_bytes,
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error reading file: {str(e)}',
                'path': file_path
            }

    def read_function(
        self,
        file_path: str,
        function_name: str
    ) -> Dict[str, Any]:
        """
        Read a specific function from file

        Note: Basic implementation. For production, use AST parsing.
        """
        try:
            file_result = self.read_file(file_path)

            if not file_result['success']:
                return file_result

            content = file_result['content']
            lines = content.split('\n')

            # Find function definition (basic pattern matching)
            function_patterns = [
                rf'def\s+{function_name}\s*\(',  # Python
                rf'function\s+{function_name}\s*\(',  # JS
                rf'const\s+{function_name}\s*=',  # JS arrow
                rf'{function_name}\s*\([^)]*\)\s*{{',  # C/C++/Go
            ]

            import re

            start_idx = None
            for i, line in enumerate(lines):
                for pattern in function_patterns:
                    if re.search(pattern, line):
                        start_idx = i
                        break
                if start_idx is not None:
                    break

            if start_idx is None:
                return {
                    'success': False,
                    'error': f'Function "{function_name}" not found in {file_path}'
                }

            # Find end of function (basic: next function def or end of file)
            end_idx = len(lines)
            for i in range(start_idx + 1, len(lines)):
                line = lines[i]
                # Check for next function definition
                if any(re.search(p.replace(function_name, r'\w+'), line) for p in function_patterns):
                    end_idx = i
                    break

            function_content = '\n'.join(lines[start_idx:end_idx])

            return {
                'success': True,
                'content': function_content,
                'function_name': function_name,
                'path': file_path,
                'start_line': start_idx + 1,
                'end_line': end_idx,
                'lines': end_idx - start_idx
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error reading function: {str(e)}'
            }

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata without reading content"""
        try:
            if os.path.isabs(file_path):
                full_path = file_path
            else:
                full_path = os.path.join(self.repo_path, file_path)

            if not os.path.exists(full_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }

            stats = os.stat(full_path)
            file_ext = os.path.splitext(file_path)[1]

            # Count lines
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)

            return {
                'success': True,
                'path': file_path,
                'full_path': full_path,
                'language': self._extension_to_language(file_ext),
                'size_bytes': stats.st_size,
                'lines': line_count,
                'modified_time': stats.st_mtime,
                'created_time': stats.st_ctime,
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error getting file info: {str(e)}'
            }

    def _extension_to_language(self, extension: str) -> str:
        """Map file extension to language"""
        mapping = {
            '.py': 'python',
            '.dart': 'dart',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.h': 'cpp',
            '.hpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
        }
        return mapping.get(extension, 'unknown')
