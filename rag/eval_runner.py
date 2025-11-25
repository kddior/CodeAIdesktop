# -*- coding: utf-8 -*-
"""
RAG Evaluation Runner
Tests the multi-document RAG system against golden test set
Includes web search augmentation using Google Custom Search
"""

import os
import sys
import yaml
import json
import logging
from typing import List, Dict
from datetime import datetime
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_manager import RAGManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleCustomSearch:
    """Google Custom Search API integration"""

    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search using Google Custom Search API

        Args:
            query: Search query
            num_results: Number of results to return (max 10)

        Returns:
            List of search results with title, snippet, link
        """
        try:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'num': min(num_results, 10)
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'items' not in data:
                return []

            results = []
            for item in data['items']:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'source': 'google_search'
                })

            return results

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []


class RAGEvaluator:
    """Evaluate RAG system against golden test set"""

    def __init__(self,
                 rag_manager: RAGManager,
                 test_set_path: str = "rag/golden_test_set_simple.yaml",
                 google_api_key: str = None,
                 google_cse_id: str = None):
        """
        Initialize evaluator

        Args:
            rag_manager: RAG manager instance
            test_set_path: Path to golden test set YAML
            google_api_key: Google Custom Search API key (optional)
            google_cse_id: Google Custom Search Engine ID (optional)
        """
        self.rag_manager = rag_manager
        self.test_set_path = test_set_path

        # Load test set
        with open(test_set_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                self.test_questions = [q for q in data if isinstance(q, dict) and 'id' in q]
                self.metadata = {}
            else:
                self.test_questions = [q for q in data if isinstance(q, dict) and 'id' in q]
                self.metadata = data.get('metadata', {})

        # Initialize Google Search (optional)
        self.google_search = None
        if google_api_key and google_cse_id:
            self.google_search = GoogleCustomSearch(google_api_key, google_cse_id)
            logger.info("Google Custom Search enabled")
        else:
            logger.info("Google Custom Search disabled (no credentials)")

    def run_evaluation(self,
                      use_web_search: bool = False,
                      top_k: int = 5,
                      save_results: bool = True) -> Dict:
        """
        Run full evaluation on all test questions

        Args:
            use_web_search: Whether to augment with Google search
            top_k: Number of RAG results to retrieve
            save_results: Save results to JSON file

        Returns:
            Evaluation results dict
        """
        logger.info("="*80)
        logger.info("RAG EVALUATION STARTED")
        logger.info("="*80)
        logger.info(f"Test set: {len(self.test_questions)} questions")
        logger.info(f"Web search: {'Enabled' if use_web_search else 'Disabled'}")
        logger.info(f"Top-k: {top_k}")
        logger.info("="*80)

        results = {
            'metadata': {
                'test_set': self.test_set_path,
                'total_questions': len(self.test_questions),
                'timestamp': datetime.now().isoformat(),
                'web_search_enabled': use_web_search,
                'top_k': top_k
            },
            'test_results': [],
            'summary': {}
        }

        for i, test in enumerate(self.test_questions, 1):
            logger.info(f"\n[{i}/{len(self.test_questions)}] Testing: {test['id']}")
            logger.info(f"  Question: {test['question']}")

            result = self.evaluate_question(test, use_web_search, top_k)
            results['test_results'].append(result)

            # Print result
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"  {status}")
            logger.info(f"  RAG results: {result['rag_num_results']}")
            if use_web_search:
                logger.info(f"  Web results: {result['web_num_results']}")
            logger.info(f"  Keywords found: {result['keywords_found']}/{result['keywords_expected']}")

        # Calculate summary
        results['summary'] = self.calculate_summary(results['test_results'])

        # Save results
        if save_results:
            output_path = f"rag/eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"\nResults saved to: {output_path}")

        # Print summary
        self.print_summary(results['summary'])

        return results

    def evaluate_question(self,
                         test: Dict,
                         use_web_search: bool,
                         top_k: int) -> Dict:
        """
        Evaluate a single test question

        Args:
            test: Test question dict
            use_web_search: Whether to use web search
            top_k: Number of results

        Returns:
            Evaluation result dict
        """
        question = test['question']

        # 1. RAG retrieval
        rag_results = self.rag_manager.retrieve_multi_document(
            query=question,
            top_k=top_k
        )

        # 2. Web search (optional)
        web_results = []
        if use_web_search and self.google_search:
            web_results = self.google_search.search(
                query=f"AFG Bank {question}",
                num_results=3
            )

        # 3. Combine context
        combined_context = self._combine_contexts(rag_results, web_results)

        # 4. Check evaluation criteria
        must_contain = test.get('must_contain', [])
        keywords_found = sum(1 for kw in must_contain if kw.lower() in combined_context.lower())
        keywords_expected = len(must_contain)

        # 5. Check document types (if RAG results available)
        expected_doc_types = test.get('expected_doc_types', [])
        actual_doc_types = list(set([r['metadata']['doc_type'] for r in rag_results if 'metadata' in r]))
        doc_type_match = any(dt in actual_doc_types for dt in expected_doc_types) if expected_doc_types else True

        # 6. Determine pass/fail
        passed = (keywords_found >= keywords_expected * 0.5) and (len(rag_results) > 0 or len(web_results) > 0)

        return {
            'test_id': test['id'],
            'question': question,
            'category': test.get('category', 'unknown'),
            'passed': passed,
            'rag_num_results': len(rag_results),
            'web_num_results': len(web_results),
            'keywords_expected': keywords_expected,
            'keywords_found': keywords_found,
            'expected_doc_types': expected_doc_types,
            'actual_doc_types': actual_doc_types,
            'doc_type_match': doc_type_match,
            'combined_context_length': len(combined_context),
            'top_rag_sources': [r['metadata'].get('doc_name', 'Unknown') for r in rag_results[:3]],
            'top_web_sources': [r['title'] for r in web_results[:3]]
        }

    def _combine_contexts(self, rag_results: List[Dict], web_results: List[Dict]) -> str:
        """Combine RAG and web search contexts"""
        context = ""

        # Add RAG results
        for result in rag_results:
            context += result.get('text', '') + "\n\n"

        # Add web results
        for result in web_results:
            context += f"{result['title']}: {result['snippet']}\n\n"

        return context

    def calculate_summary(self, test_results: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        total = len(test_results)
        passed = sum(1 for r in test_results if r['passed'])
        failed = total - passed

        # By category
        by_category = {}
        for result in test_results:
            cat = result['category']
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'passed': 0}
            by_category[cat]['total'] += 1
            if result['passed']:
                by_category[cat]['passed'] += 1

        # Calculate pass rates
        for cat in by_category:
            by_category[cat]['pass_rate'] = by_category[cat]['passed'] / by_category[cat]['total']

        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total if total > 0 else 0,
            'by_category': by_category,
            'avg_rag_results': sum(r['rag_num_results'] for r in test_results) / total if total > 0 else 0,
            'avg_web_results': sum(r['web_num_results'] for r in test_results) / total if total > 0 else 0
        }

    def print_summary(self, summary: Dict):
        """Print evaluation summary"""
        logger.info("\n" + "="*80)
        logger.info("EVALUATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed']} ✅")
        logger.info(f"Failed: {summary['failed']} ❌")
        logger.info(f"Pass rate: {summary['pass_rate']*100:.1f}%")
        logger.info(f"Avg RAG results: {summary['avg_rag_results']:.1f}")
        logger.info(f"Avg Web results: {summary['avg_web_results']:.1f}")

        logger.info("\nBy Category:")
        for cat, stats in summary['by_category'].items():
            logger.info(f"  {cat}: {stats['passed']}/{stats['total']} ({stats['pass_rate']*100:.1f}%)")
        logger.info("="*80)


def main():
    """Run evaluation"""
    import argparse

    parser = argparse.ArgumentParser(description='Run RAG evaluation')
    parser.add_argument('--web-search', action='store_true', help='Enable web search augmentation')
    parser.add_argument('--top-k', type=int, default=5, help='Number of RAG results (default: 5)')
    parser.add_argument('--google-api-key', type=str, help='Google API key')
    parser.add_argument('--google-cse-id', type=str, help='Google Custom Search Engine ID')

    args = parser.parse_args()

    # Get API credentials from args or environment
    google_api_key = args.google_api_key or os.environ.get('GOOGLE_API_KEY')
    google_cse_id = args.google_cse_id or os.environ.get('GOOGLE_CSE_ID')

    # Initialize RAG Manager
    logger.info("Initializing RAG Manager...")
    rag_manager = RAGManager()

    # Initialize Evaluator
    evaluator = RAGEvaluator(
        rag_manager=rag_manager,
        test_set_path="rag/golden_test_set_simple.yaml",
        google_api_key=google_api_key,
        google_cse_id=google_cse_id
    )

    # Run evaluation
    results = evaluator.run_evaluation(
        use_web_search=args.web_search and google_api_key is not None,
        top_k=args.top_k,
        save_results=True
    )

    # Exit with appropriate code
    pass_rate = results['summary']['pass_rate']
    sys.exit(0 if pass_rate >= 0.7 else 1)


if __name__ == "__main__":
    main()
