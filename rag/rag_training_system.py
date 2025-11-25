# -*- coding: utf-8 -*-
"""
RAG Training System - Iterative Question Generation & Pipeline Improvement

This script:
1. Generates synthetic questions using GPT-4
2. Tests them against RAG system
3. Analyzes failures (retrieval misses, poor normalization, missing synonyms)
4. Suggests improvements (chunking, normalization rules, synonyms)
5. Iterates - generates new questions based on findings
6. Trains the PIPELINE (not the model) through iterative refinement

Goal: Strengthen intent classification, RAG retrieval, query understanding, and behavior
"""

import os
import sys
import json
import yaml
import logging
from typing import List, Dict, Tuple
from datetime import datetime
import time

# OpenAI for question generation
from openai import OpenAI

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_manager import RAGManager
from rag.comprehensive_prompts import (
    COMPREHENSIVE_PROMPTS,
    get_prompt,
    get_all_categories,
    get_total_question_count
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGTrainingSystem:
    """
    Iterative RAG training system
    Generates questions, tests RAG, analyzes failures, suggests improvements
    """

    def __init__(self,
                 rag_manager: RAGManager,
                 openai_api_key: str,
                 output_dir: str = "rag/training"):
        """
        Initialize training system

        Args:
            rag_manager: RAG manager instance
            openai_api_key: OpenAI API key for question generation
            output_dir: Directory to save training data and results
        """
        self.rag_manager = rag_manager
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        self.model = "gpt-4o"  # GPT-4o for best quality

        # Training state
        self.iteration = 0
        self.all_questions = []
        self.failure_patterns = []
        self.improvement_suggestions = []

        logger.info(f"RAG Training System initialized (output: {output_dir})")

    def generate_questions(self,
                          category: str,
                          count: int = 50,
                          noise_level: str = "mixed",
                          use_comprehensive_prompt: bool = True) -> List[Dict]:
        """
        Generate synthetic questions using GPT-4o

        Args:
            category: Question category or comprehensive prompt key
            count: Number of questions to generate (ignored if using comprehensive prompt)
            noise_level: clean / moderate / extreme / mixed (ignored if using comprehensive prompt)
            use_comprehensive_prompt: Use specialized prompts from comprehensive_prompts.py

        Returns:
            List of generated questions with metadata
        """
        # Check if category exists in comprehensive prompts
        if use_comprehensive_prompt and category in COMPREHENSIVE_PROMPTS:
            prompt_config = get_prompt(category)
            prompt = prompt_config['prompt']
            expected_count = prompt_config['count']
            logger.info(f"Using comprehensive prompt: {prompt_config['name']} ({expected_count} questions)")
        else:
            # Fallback to basic prompt generation
            logger.info(f"Generating {count} {noise_level} questions for category: {category}")

            # Build prompt based on noise level
            noise_instructions = {
                "clean": "Questions doivent être bien écrites, avec accents corrects, grammaire parfaite.",
                "moderate": "Mélange: 50% bien écrites, 50% avec fautes d'orthographe, sans accents, style WhatsApp.",
                "extreme": "Questions très bruitées: fautes graves, sans accents, style vocal transcrit, syntaxe cassée.",
                "mixed": "Mélange équilibré: 33% clean, 33% moderate, 33% extreme."
            }

            prompt = f"""
Tu es un générateur de questions clients pour une banque (AFG Bank CI).

Génère {count} questions naturelles sur la catégorie: {category}

Contraintes:
- {noise_instructions[noise_level]}
- Style varié: WhatsApp court, vocal long, corporate, client lambda
- Utilise expressions ivoiriennes (hein, svp, c'est combien là, même)
- Variantes orthographiques réalistes (cloture/clôture, cheque/chèque, attestasion/attestation)
- Reformulations vagues ("le papier pour fermer le compte")
- Questions directes ET indirectes

Catégories de questions à couvrir pour "{category}":
- Tarifs (prix exact)
- Procédures (comment faire)
- Conditions (qui peut, quand)
- Comparaisons (différence entre X et Y)
- Cas spéciaux (et si...)

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif|procedure|general"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON, rien d'autre.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un expert en génération de questions bancaires naturelles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,  # High creativity for diversity
                max_tokens=3000
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract JSON (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            questions = data.get('questions', [])

            logger.info(f"Generated {len(questions)} questions")
            return questions

        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return []

    def test_question(self, question: Dict) -> Dict:
        """
        Test a single question against RAG system

        Args:
            question: Question dict with text, noise_level, etc.

        Returns:
            Test result with retrieval success, analysis
        """
        query = question['text']

        # Retrieve from RAG
        results = self.rag_manager.retrieve_multi_document(
            query=query,
            top_k=5
        )

        # Analyze results
        expected_keywords = question.get('expected_keywords', [])
        expected_doc_type = question.get('expected_doc_type', None)

        # Check if keywords found
        context_text = " ".join([r['text'] for r in results]).lower()
        keywords_found = sum(1 for kw in expected_keywords if kw.lower() in context_text)
        keywords_total = len(expected_keywords)

        # Check if correct doc type retrieved
        doc_types_retrieved = list(set([r['metadata']['doc_type'] for r in results if 'metadata' in r]))
        doc_type_correct = expected_doc_type in doc_types_retrieved if expected_doc_type else True

        # Determine pass/fail
        passed = (
            len(results) > 0 and
            (keywords_found >= keywords_total * 0.5) and
            doc_type_correct
        )

        return {
            'question': question,
            'query': query,
            'passed': passed,
            'num_results': len(results),
            'keywords_found': keywords_found,
            'keywords_total': keywords_total,
            'doc_types_retrieved': doc_types_retrieved,
            'expected_doc_type': expected_doc_type,
            'doc_type_correct': doc_type_correct,
            'top_chunks': [r['metadata'].get('section_name', 'Unknown') for r in results[:3]]
        }

    def test_batch(self, questions: List[Dict]) -> List[Dict]:
        """Test a batch of questions"""
        logger.info(f"Testing {len(questions)} questions...")

        results = []
        for i, question in enumerate(questions, 1):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(questions)}")

            result = self.test_question(question)
            results.append(result)

        return results

    def analyze_failures(self, test_results: List[Dict]) -> Dict:
        """
        Analyze failed tests to identify patterns

        Returns:
            Analysis report with patterns and suggestions
        """
        logger.info("Analyzing failures...")

        failures = [r for r in test_results if not r['passed']]
        total = len(test_results)
        failed_count = len(failures)

        if failed_count == 0:
            logger.info("No failures! 100% pass rate.")
            return {
                'total': total,
                'failures': 0,
                'pass_rate': 1.0,
                'patterns': [],
                'suggestions': []
            }

        # Analyze patterns
        patterns = {
            'no_results': 0,
            'keywords_missing': 0,
            'wrong_doc_type': 0,
            'extreme_noise': 0,
            'accent_issues': 0,
            'typo_issues': 0
        }

        for failure in failures:
            if failure['num_results'] == 0:
                patterns['no_results'] += 1

            if failure['keywords_found'] < failure['keywords_total'] * 0.5:
                patterns['keywords_missing'] += 1

            if not failure['doc_type_correct']:
                patterns['wrong_doc_type'] += 1

            if failure['question'].get('noise_level') == 'extreme':
                patterns['extreme_noise'] += 1

            # Detect accent issues (é, è, à, ô removed)
            query = failure['query']
            if any(c in query for c in ['e', 'a', 'o', 'u']) and not any(c in query for c in ['é', 'è', 'à', 'ô', 'û']):
                patterns['accent_issues'] += 1

            # Detect typo issues
            if any(typo in query.lower() for typo in ['koi', 'combein', 'clotur', 'attestasion', 'signatir']):
                patterns['typo_issues'] += 1

        # Generate suggestions
        suggestions = []

        if patterns['accent_issues'] > failed_count * 0.3:
            suggestions.append({
                'type': 'normalization',
                'priority': 'high',
                'issue': 'Accent normalization insufficient',
                'suggestion': 'Improve NFD normalization in RAG pipeline. Add accent stripping for queries.'
            })

        if patterns['typo_issues'] > failed_count * 0.3:
            suggestions.append({
                'type': 'synonyms',
                'priority': 'high',
                'issue': 'Common typos not handled',
                'suggestion': 'Add typo variations to synonym map: clotur→clôture, attestasion→attestation, etc.'
            })

        if patterns['no_results'] > failed_count * 0.2:
            suggestions.append({
                'type': 'chunking',
                'priority': 'medium',
                'issue': 'Some queries return zero results',
                'suggestion': 'Review chunk size and overlap. Consider smaller chunks (600 chars) with more overlap (200 chars).'
            })

        if patterns['keywords_missing'] > failed_count * 0.4:
            suggestions.append({
                'type': 'embedding',
                'priority': 'medium',
                'issue': 'Keywords not found in retrieved chunks',
                'suggestion': 'Consider multi-query expansion: generate 2-3 reformulations per query before embedding.'
            })

        if patterns['wrong_doc_type'] > failed_count * 0.3:
            suggestions.append({
                'type': 'metadata',
                'priority': 'low',
                'issue': 'Wrong document types retrieved',
                'suggestion': 'Add document type hints to chunks. Consider doc-type-specific indexes.'
            })

        return {
            'total': total,
            'failures': failed_count,
            'pass_rate': (total - failed_count) / total,
            'patterns': patterns,
            'suggestions': suggestions
        }

    def save_iteration_results(self, iteration: int, questions: List[Dict],
                               test_results: List[Dict], analysis: Dict):
        """Save iteration results to disk"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"iteration_{iteration:02d}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        data = {
            'iteration': iteration,
            'timestamp': timestamp,
            'questions': questions,
            'test_results': test_results,
            'analysis': analysis
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved: {filepath}")

    def run_training_iteration(self,
                               category: str,
                               count: int = 50,
                               noise_level: str = "mixed",
                               use_comprehensive_prompt: bool = True) -> Dict:
        """
        Run one training iteration:
        1. Generate questions
        2. Test against RAG
        3. Analyze failures
        4. Suggest improvements

        Args:
            category: Category or comprehensive prompt key
            count: Number of questions (ignored if comprehensive prompt used)
            noise_level: Noise level (ignored if comprehensive prompt used)
            use_comprehensive_prompt: Use specialized comprehensive prompts

        Returns:
            Iteration results and suggestions
        """
        self.iteration += 1

        logger.info("="*80)
        logger.info(f"TRAINING ITERATION {self.iteration}")
        logger.info("="*80)

        # Step 1: Generate questions
        questions = self.generate_questions(category, count, noise_level, use_comprehensive_prompt)
        if not questions:
            logger.error("Question generation failed!")
            return None

        # Step 2: Test questions
        test_results = self.test_batch(questions)

        # Step 3: Analyze failures
        analysis = self.analyze_failures(test_results)

        # Step 4: Save results
        self.save_iteration_results(self.iteration, questions, test_results, analysis)

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("ITERATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total questions: {analysis['total']}")
        logger.info(f"Pass rate: {analysis['pass_rate']*100:.1f}%")
        logger.info(f"Failures: {analysis['failures']}")

        logger.info("\nFailure Patterns:")
        for pattern, count in analysis['patterns'].items():
            logger.info(f"  {pattern}: {count}")

        logger.info("\nSuggestions for Improvement:")
        for i, suggestion in enumerate(analysis['suggestions'], 1):
            logger.info(f"\n  [{i}] {suggestion['type'].upper()} (Priority: {suggestion['priority']})")
            logger.info(f"      Issue: {suggestion['issue']}")
            logger.info(f"      Fix: {suggestion['suggestion']}")

        logger.info("="*80)

        return analysis

    def run_all_comprehensive_prompts(self):
        """
        Run all 10 comprehensive prompts (1,240 total questions)
        This is the most exhaustive training approach
        """
        all_categories = get_all_categories()
        total_questions = get_total_question_count()

        logger.info("="*80)
        logger.info("RUNNING ALL COMPREHENSIVE PROMPTS")
        logger.info("="*80)
        logger.info(f"Total prompts: {len(all_categories)}")
        logger.info(f"Total questions: {total_questions}")
        logger.info(f"Categories: {all_categories}")
        logger.info("="*80)

        all_analyses = []

        for category in all_categories:
            prompt_config = get_prompt(category)
            logger.info(f"\n\n### PROMPT: {prompt_config['name']} ({prompt_config['count']} questions) ###\n")

            analysis = self.run_training_iteration(
                category=category,
                use_comprehensive_prompt=True
            )

            if analysis:
                all_analyses.append({
                    'prompt_name': prompt_config['name'],
                    'prompt_key': category,
                    'expected_count': prompt_config['count'],
                    'analysis': analysis
                })

            # Pause between prompts to avoid rate limiting
            time.sleep(3)

        # Final summary
        self._print_comprehensive_summary(all_analyses)

    def run_full_training_cycle(self,
                                categories: List[str] = None,
                                iterations_per_category: int = 3,
                                questions_per_iteration: int = 50,
                                use_comprehensive_prompts: bool = False):
        """
        Run full training cycle across multiple categories and iterations

        Args:
            categories: List of categories to train on
            iterations_per_category: Number of iterations per category
            questions_per_iteration: Questions per iteration
            use_comprehensive_prompts: Use comprehensive prompts instead of basic
        """
        if categories is None:
            categories = ['tarif', 'procedure', 'general', 'mobile', 'credit']

        logger.info("="*80)
        logger.info("STARTING FULL TRAINING CYCLE")
        logger.info("="*80)
        logger.info(f"Categories: {categories}")
        logger.info(f"Iterations per category: {iterations_per_category}")
        logger.info(f"Questions per iteration: {questions_per_iteration}")
        logger.info(f"Using comprehensive prompts: {use_comprehensive_prompts}")
        logger.info("="*80)

        all_analyses = []

        for category in categories:
            logger.info(f"\n\n### TRAINING CATEGORY: {category} ###\n")

            for i in range(iterations_per_category):
                # Vary noise level across iterations
                noise_levels = ['clean', 'moderate', 'extreme', 'mixed']
                noise_level = noise_levels[i % len(noise_levels)]

                analysis = self.run_training_iteration(
                    category=category,
                    count=questions_per_iteration,
                    noise_level=noise_level,
                    use_comprehensive_prompt=use_comprehensive_prompts
                )

                if analysis:
                    all_analyses.append({
                        'category': category,
                        'iteration': i + 1,
                        'noise_level': noise_level,
                        'analysis': analysis
                    })

                # Brief pause between iterations
                time.sleep(2)

        # Final summary
        self._print_final_summary(all_analyses)

    def _print_final_summary(self, all_analyses: List[Dict]):
        """Print final training summary"""
        logger.info("\n\n" + "="*80)
        logger.info("FINAL TRAINING SUMMARY")
        logger.info("="*80)

        total_questions = sum(a['analysis']['total'] for a in all_analyses)
        total_failures = sum(a['analysis']['failures'] for a in all_analyses)
        overall_pass_rate = (total_questions - total_failures) / total_questions if total_questions > 0 else 0

        logger.info(f"Total questions tested: {total_questions}")
        logger.info(f"Overall pass rate: {overall_pass_rate*100:.1f}%")
        logger.info(f"Total failures: {total_failures}")

        logger.info("\nPass Rates by Category:")
        by_category = {}
        for a in all_analyses:
            cat = a['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(a['analysis']['pass_rate'])

        for cat, rates in by_category.items():
            avg_rate = sum(rates) / len(rates)
            logger.info(f"  {cat}: {avg_rate*100:.1f}%")

        logger.info("\nTop Improvement Priorities:")
        all_suggestions = []
        for a in all_analyses:
            all_suggestions.extend(a['analysis']['suggestions'])

        # Count suggestion types
        suggestion_counts = {}
        for sugg in all_suggestions:
            key = f"{sugg['type']}: {sugg['issue']}"
            suggestion_counts[key] = suggestion_counts.get(key, 0) + 1

        for i, (key, count) in enumerate(sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            logger.info(f"  {i}. {key} (mentioned {count}x)")

        logger.info("="*80)

    def _print_comprehensive_summary(self, all_analyses: List[Dict]):
        """Print summary for comprehensive prompts run"""
        logger.info("\n\n" + "="*80)
        logger.info("COMPREHENSIVE PROMPTS SUMMARY")
        logger.info("="*80)

        total_questions = sum(a['analysis']['total'] for a in all_analyses)
        total_failures = sum(a['analysis']['failures'] for a in all_analyses)
        overall_pass_rate = (total_questions - total_failures) / total_questions if total_questions > 0 else 0

        logger.info(f"Total prompts run: {len(all_analyses)}")
        logger.info(f"Total questions tested: {total_questions}")
        logger.info(f"Overall pass rate: {overall_pass_rate*100:.1f}%")
        logger.info(f"Total failures: {total_failures}")

        logger.info("\nPass Rates by Prompt:")
        for a in all_analyses:
            pass_rate = a['analysis']['pass_rate']
            logger.info(f"  {a['prompt_name']}: {pass_rate*100:.1f}% ({a['analysis']['total']} questions)")

        logger.info("\nTop Improvement Priorities:")
        all_suggestions = []
        for a in all_analyses:
            all_suggestions.extend(a['analysis']['suggestions'])

        # Count suggestion types
        suggestion_counts = {}
        for sugg in all_suggestions:
            key = f"{sugg['type']}: {sugg['issue']}"
            suggestion_counts[key] = suggestion_counts.get(key, 0) + 1

        for i, (key, count) in enumerate(sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            logger.info(f"  {i}. {key} (mentioned {count}x)")

        logger.info("="*80)


def main():
    """Run RAG training system"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Train RAG system with synthetic questions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single comprehensive prompt (50 questions on attestation clôture)
  python rag/rag_training_system.py --openai-key "sk-..." --prompt attestation_cloture

  # All 10 comprehensive prompts (1,240 total questions)
  python rag/rag_training_system.py --openai-key "sk-..." --all-prompts

  # Full cycle with comprehensive prompts
  python rag/rag_training_system.py --openai-key "sk-..." --full-cycle --comprehensive

  # Basic prompt (legacy mode)
  python rag/rag_training_system.py --openai-key "sk-..." --category tarif --count 50 --noise mixed

Available comprehensive prompts:
  - attestation_cloture (50 questions)
  - changement_signature (50 questions)
  - carte_visa_business (50 questions)
  - all_tariff_lines (200 questions)
  - random_fuzzy (100 questions)
  - extremely_noisy (50 questions)
  - speech_to_text (100 questions)
  - long_context (40 questions)
  - extreme_variants (100 questions)
  - massive_stress_test (500 questions)
        """
    )
    parser.add_argument('--openai-key', type=str, help='OpenAI API key')
    parser.add_argument('--prompt', type=str, help='Comprehensive prompt key (see list above)')
    parser.add_argument('--all-prompts', action='store_true', help='Run all 10 comprehensive prompts (1,240 questions)')
    parser.add_argument('--category', type=str, default='tarif', help='Question category (basic mode)')
    parser.add_argument('--count', type=int, default=50, help='Questions per iteration (basic mode)')
    parser.add_argument('--iterations', type=int, default=1, help='Number of iterations')
    parser.add_argument('--noise', type=str, default='mixed', choices=['clean', 'moderate', 'extreme', 'mixed'])
    parser.add_argument('--full-cycle', action='store_true', help='Run full training cycle (all categories)')
    parser.add_argument('--comprehensive', action='store_true', help='Use comprehensive prompts in full cycle')
    parser.add_argument('--list-prompts', action='store_true', help='List all available comprehensive prompts')

    args = parser.parse_args()

    # List prompts and exit
    if args.list_prompts:
        print("\nAvailable Comprehensive Prompts:")
        print("="*80)
        for key in get_all_categories():
            config = get_prompt(key)
            print(f"  {key:25s} - {config['name']} ({config['count']} questions)")
        print(f"\nTotal questions across all prompts: {get_total_question_count()}")
        print("="*80)
        return

    # Require OpenAI key for actual training
    if not args.openai_key:
        parser.error("--openai-key is required for training (not needed for --list-prompts)")

    # Initialize RAG Manager
    logger.info("Initializing RAG Manager...")
    rag_manager = RAGManager()

    # Initialize Training System
    trainer = RAGTrainingSystem(
        rag_manager=rag_manager,
        openai_api_key=args.openai_key
    )

    if args.all_prompts:
        # Run all 10 comprehensive prompts
        trainer.run_all_comprehensive_prompts()
    elif args.prompt:
        # Run single comprehensive prompt
        if args.prompt not in get_all_categories():
            logger.error(f"Unknown prompt: {args.prompt}")
            logger.error(f"Available prompts: {', '.join(get_all_categories())}")
            sys.exit(1)
        trainer.run_training_iteration(
            category=args.prompt,
            use_comprehensive_prompt=True
        )
    elif args.full_cycle:
        # Run full training cycle
        trainer.run_full_training_cycle(
            iterations_per_category=args.iterations,
            questions_per_iteration=args.count,
            use_comprehensive_prompts=args.comprehensive
        )
    else:
        # Run single category (basic mode)
        for i in range(args.iterations):
            trainer.run_training_iteration(
                category=args.category,
                count=args.count,
                noise_level=args.noise,
                use_comprehensive_prompt=False
            )


if __name__ == "__main__":
    main()
