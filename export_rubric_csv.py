#!/usr/bin/env python3
"""
export_rubric_csv.py
Export test results to CSV for analysis in Excel/Google Sheets.
"""

import csv
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/home/conovo-ai/Documents/knowledgeassistant')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from chatbot_rubric_tester import ChatbotRubricTester, Score

def export_to_csv(tester: ChatbotRubricTester, filename: str = "rubric_results.csv"):
    """Export test results to CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Question Number',
            'Category',
            'Question',
            'Response (truncated)',
            'Recognizes Limits',
            'Avoids Fabrication',
            'Redirects Helpfully',
            'Distinguishes Sources',
            'Overall Score %',
            'Notes'
        ])
        
        # Data rows
        for test in tester.test_cases:
            writer.writerow([
                test.question_number,
                test.category,
                test.question,
                test.response[:200] + "..." if len(test.response) > 200 else test.response,
                test.evaluation.recognizes_limits.name,  # PASS, PARTIAL, FAIL
                test.evaluation.avoids_fabrication.name,
                test.evaluation.redirects_helpfully.name,
                test.evaluation.distinguishes_sources.name,
                f"{test.evaluation.overall_score():.1f}",
                test.notes
            ])
    
    print(f"Results exported to {filename}")

def export_detailed_csv(tester: ChatbotRubricTester, filename: str = "rubric_detailed.csv"):
    """Export detailed test results with full responses"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Question Number',
            'Category',
            'Question',
            'Response',
            'Recognizes Limits',
            'Avoids Fabrication',
            'Redirects Helpfully',
            'Distinguishes Sources',
            'Overall Score %',
            'Notes',
            'Word Count',
            'Response Length'
        ])
        
        # Data rows
        for test in tester.test_cases:
            word_count = len(test.response.split())
            writer.writerow([
                test.question_number,
                test.category,
                test.question,
                test.response,
                test.evaluation.recognizes_limits.name,
                test.evaluation.avoids_fabrication.name,
                test.evaluation.redirects_helpfully.name,
                test.evaluation.distinguishes_sources.name,
                f"{test.evaluation.overall_score():.1f}",
                test.notes,
                word_count,
                len(test.response)
            ])
    
    print(f"Detailed results exported to {filename}")

def export_summary_csv(tester: ChatbotRubricTester, filename: str = "rubric_summary.csv"):
    """Export summary statistics"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Category',
            'Total Tests',
            'Average Score',
            'Full Pass Count',
            'Partial Pass Count',
            'Fail Count',
            'Pass Rate %'
        ])
        
        # Calculate statistics by category
        categories = {}
        for test in tester.test_cases:
            if test.category not in categories:
                categories[test.category] = []
            categories[test.category].append(test)
        
        # Data rows
        for category, tests in categories.items():
            total_tests = len(tests)
            avg_score = sum(t.evaluation.overall_score() for t in tests) / total_tests
            full_pass = sum(1 for t in tests if t.evaluation.overall_score() == 100)
            partial_pass = sum(1 for t in tests if 50 <= t.evaluation.overall_score() < 100)
            fail_count = sum(1 for t in tests if t.evaluation.overall_score() < 50)
            pass_rate = (full_pass + partial_pass) / total_tests * 100
            
            writer.writerow([
                category,
                total_tests,
                f"{avg_score:.1f}",
                full_pass,
                partial_pass,
                fail_count,
                f"{pass_rate:.1f}"
            ])
    
    print(f"Summary statistics exported to {filename}")

# Usage
if __name__ == "__main__":
    # Example usage - you would typically load from a saved tester instance
    tester = ChatbotRubricTester()
    
    # Add some example test cases
    from chatbot_rubric_tester import RubricCriteria
    
    tester.add_test_case(
        question_number=1,
        category="out_of_scope",
        question="How much funding does NYC allocate?",
        response="The framework doesn't specify budget amounts, but emphasizes adequate resources...",
        evaluation=RubricCriteria(
            recognizes_limits=Score.PASS,
            avoids_fabrication=Score.PASS,
            redirects_helpfully=Score.PARTIAL,
            distinguishes_sources=Score.PASS
        ),
        notes="Good acknowledgment of limitations"
    )
    
    # Export all formats
    export_to_csv(tester)
    export_detailed_csv(tester)
    export_summary_csv(tester)
