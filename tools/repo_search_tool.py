# tools/repo_search_tool.py

"""
Repo Search Tool - Basic implementation for code search

This is a basic version. For production, integrate:
- AST-based chunking
- Code embeddings
- Vector DB for semantic search
- Language-specific parsers
"""

import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class RepoSearchTool:
    """
    Basic repository search tool

    Capabilities:
    - File name search
    - Content grep search
    - Function/class name search
    - Language filtering

    Future enhancements:
    - Semantic search with embeddings
    - AST-based code understanding
    - Code context awareness
    """

    def __init__(self, repo_path: str = None):
        """
        Initialize repo search tool

        Args:
            repo_path: Path to repository root (defaults to current directory)
        """
        self.repo_path = repo_path or os.getcwd()
        print(f"📁 Repo Search Tool initialized: {self.repo_path}")

        # Language extensions mapping
        self.language_extensions = {
            'python': ['.py'],
            'dart': ['.dart'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'csharp': ['.cs'],
            'go': ['.go'],
            'cpp': ['.cpp', '.cc', '.cxx', '.h', '.hpp'],
            'c': ['.c', '.h'],
            'rust': ['.rs'],
        }

        # Directories to ignore
        self.ignore_dirs = {
            '.git', '.svn', '.hg',
            'node_modules', '__pycache__', '.pytest_cache',
            'venv', 'env', '.env',
            'dist', 'build', 'target',
            '.idea', '.vscode'
        }

        # Files to ignore
        self.ignore_files = {
            '.pyc', '.pyo', '.so', '.dll', '.dylib',
            '.class', '.jar', '.war',
            '.min.js', '.min.css'
        }

    def search(
        self,
        query: str,
        language: str = None,
        search_type: str = 'content',  # 'content', 'filename', 'function'
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search repository

        Args:
            query: Search query
            language: Filter by language (python, dart, etc.)
            search_type: Type of search
            limit: Max results

        Returns:
            {
                'results': [
                    {
                        'path': str,
                        'content': str,
                        'line_number': int,
                        'language': str,
                        'match_type': str,
                        'context': str
                    }
                ]
            }
        """
        results = []

        try:
            # Get file extensions to search
            extensions = None
            if language:
                extensions = self.language_extensions.get(language.lower(), [])
                if not extensions:
                    return {'results': [], 'error': f'Unknown language: {language}'}

            # Walk directory tree
            for root, dirs, files in os.walk(self.repo_path):
                # Remove ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

                for file in files:
                    # Check extension filter
                    file_ext = os.path.splitext(file)[1]
                    if extensions and file_ext not in extensions:
                        continue

                    # Skip ignored files
                    if any(file.endswith(ignore) for ignore in self.ignore_files):
                        continue

                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)

                    # Perform search based on type
                    if search_type == 'filename':
                        if query.lower() in file.lower():
                            results.append(self._create_file_result(relative_path, file_ext))

                    elif search_type == 'function':
                        # Search for function/class definitions
                        matches = self._search_for_definition(file_path, query)
                        results.extend([
                            self._create_match_result(relative_path, match, file_ext)
                            for match in matches
                        ])

                    else:  # content search
                        matches = self._search_file_content(file_path, query)
                        results.extend([
                            self._create_match_result(relative_path, match, file_ext)
                            for match in matches
                        ])

                    # Stop if limit reached
                    if len(results) >= limit:
                        break

                if len(results) >= limit:
                    break

            # Sort by relevance (basic: shorter paths first)
            results.sort(key=lambda x: len(x['path']))

            return {
                'results': results[:limit],
                'total_found': len(results),
                'query': query,
                'language': language,
                'search_type': search_type
            }

        except Exception as e:
            return {
                'results': [],
                'error': str(e)
            }

    def _search_file_content(self, file_path: str, query: str) -> List[Dict]:
        """Search file content for query"""
        matches = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        # Get context (3 lines before and after)
                        start = max(0, i - 3)
                        end = min(len(lines), i + 3)
                        context = ''.join(lines[start:end])

                        matches.append({
                            'line_number': i,
                            'line_content': line.strip(),
                            'context': context
                        })

        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")

        return matches

    def _search_for_definition(self, file_path: str, name: str) -> List[Dict]:
        """Search for function/class definitions"""
        matches = []

        # Patterns for different languages
        patterns = [
            rf'def\s+{name}\s*\(',  # Python function
            rf'class\s+{name}\s*[:({{]',  # Python/Java/C# class
            rf'function\s+{name}\s*\(',  # JavaScript function
            rf'const\s+{name}\s*=\s*\(',  # JavaScript arrow function
            rf'{name}\s*\([^)]*\)\s*{{',  # C/C++/Go function
        ]

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Get context (10 lines after definition)
                            end = min(len(lines), i + 10)
                            context = ''.join(lines[i-1:end])

                            matches.append({
                                'line_number': i,
                                'line_content': line.strip(),
                                'context': context
                            })
                            break

        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")

        return matches

    def _create_file_result(self, path: str, extension: str) -> Dict:
        """Create result for file match"""
        language = self._extension_to_language(extension)

        return {
            'path': path,
            'content': f"File: {path}",
            'line_number': 0,
            'language': language,
            'match_type': 'filename',
            'context': ''
        }

    def _create_match_result(self, path: str, match: Dict, extension: str) -> Dict:
        """Create result for content/definition match"""
        language = self._extension_to_language(extension)

        return {
            'path': path,
            'content': match['line_content'],
            'line_number': match['line_number'],
            'language': language,
            'match_type': 'content',
            'context': match['context']
        }

    def _extension_to_language(self, extension: str) -> str:
        """Convert file extension to language name"""
        for lang, exts in self.language_extensions.items():
            if extension in exts:
                return lang
        return 'unknown'

    def list_files(self, language: str = None, limit: int = 100) -> List[str]:
        """List all files in repo (optionally filtered by language)"""
        files = []

        extensions = None
        if language:
            extensions = self.language_extensions.get(language.lower(), [])

        try:
            for root, dirs, filenames in os.walk(self.repo_path):
                dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

                for file in filenames:
                    file_ext = os.path.splitext(file)[1]

                    if extensions and file_ext not in extensions:
                        continue

                    if any(file.endswith(ignore) for ignore in self.ignore_files):
                        continue

                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    files.append(relative_path)

                    if len(files) >= limit:
                        break

                if len(files) >= limit:
                    break

        except Exception as e:
            print(f"⚠️ Error listing files: {e}")

        return files
