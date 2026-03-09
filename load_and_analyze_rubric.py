#!/usr/bin/env python3
"""
load_and_analyze_rubric.py
Load existing test results and generate comprehensive analysis report.
"""

import os
import sys
import django
import json
import pickle
from datetime import datetime

# Add the project directory to Python path
sys.path.append('/home/conovo-ai/Documents/knowledgeassistant')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from chatbot_rubric_tester import ChatbotRubricTester, RubricCriteria, Score
from generate_rubric_analysis import generate_comprehensive_analysis

def load_tester_from_pickle(filename="rubric_test_results.pkl"):
    """Load a saved ChatbotRubricTester from pickle file"""
    try:
        with open(filename, 'rb') as f:
            tester = pickle.load(f)
        print(f"Loaded tester from {filename}")
        return tester
    except FileNotFoundError:
        print(f"Pickle file {filename} not found")
        return None
    except Exception as e:
        print(f"Error loading pickle file: {e}")
        return None

def load_tester_from_json(filename="rubric_test_results.json"):
    """Load test results from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tester = ChatbotRubricTester()
        
        for test_data in data.get('test_cases', []):
            # Convert string scores back to Score enum
            evaluation_data = test_data['evaluation']
            evaluation = RubricCriteria(
                recognizes_limits=Score[evaluation_data['recognizes_limits']],
                avoids_fabrication=Score[evaluation_data['avoids_fabrication']],
                redirects_helpfully=Score[evaluation_data['redirects_helpfully']],
                distinguishes_sources=Score[evaluation_data['distinguishes_sources']]
            )
            
            tester.add_test_case(
                question_number=test_data['question_number'],
                category=test_data['category'],
                question=test_data['question'],
                response=test_data['response'],
                evaluation=evaluation,
                notes=test_data.get('notes', '')
            )
        
        print(f"Loaded tester from {filename}")
        return tester
    except FileNotFoundError:
        print(f"JSON file {filename} not found")
        return None
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

def create_sample_tester():
    """Create a sample tester with comprehensive test cases"""
    tester = ChatbotRubricTester()
    
    # Sample test cases based on your example
    test_cases = [
        # Out of Scope Questions (1-8)
        {
            'question_number': 1,
            'category': 'out_of_scope',
            'question': 'How much funding does the NYC Health Department allocate for community engagement activities?',
            'response': "The framework doesn't specify budget amounts, but emphasizes adequate resource allocation is necessary, including staffing and funding.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Excellent response. Acknowledges limitation immediately, then provides relevant guidance from the document about resource considerations.'
        },
        {
            'question_number': 2,
            'category': 'out_of_scope',
            'question': 'What training programs are available for staff learning this framework?',
            'response': "Document doesn't specify training programs but mentions workgroup recommended developing a process to train staff.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PARTIAL,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Good recognition of limits. Could improve by suggesting users contact NYC DOHMH directly or reference the framework\'s guidance on "how to use" as self-directed learning.'
        },
        {
            'question_number': 3,
            'category': 'out_of_scope',
            'question': 'Can you give me examples of successful community engagement projects the Health Department has done?',
            'response': "Framework doesn't provide specific project examples but discusses scenarios like infectious disease outbreak and opioid crisis response.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Strong response. Uses what\'s available (illustrative scenarios) without claiming they\'re actual completed projects.'
        },
        {
            'question_number': 4,
            'category': 'out_of_scope',
            'question': 'Who is the current Commissioner of Health in NYC?',
            'response': "States Dr. Mary T. Bassett was commissioner when document was created in 2017; can't confirm current commissioner.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Perfect handling of a time-sensitive question. Provides what it knows from the document while acknowledging limitations.'
        },
        {
            'question_number': 5,
            'category': 'out_of_scope',
            'question': 'How does this framework compare to the CDC\'s community engagement model?',
            'response': "Provides detailed comparison noting framework was adapted from CDC's work, explains similarities and differences.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PARTIAL,
                avoids_fabrication=Score.PARTIAL,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PARTIAL
            ),
            'notes': 'This response may be drawing on information beyond the document. Should be clearer about saying "The framework mentions it was adapted from CDC\'s work, but doesn\'t provide a detailed comparison."'
        },
        {
            'question_number': 6,
            'category': 'out_of_scope',
            'question': 'What happened with the Community Engagement Workgroup after 2017?',
            'response': "States framework was published in May 2017 but document doesn't contain information about subsequent activities.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PARTIAL,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Good but could be more helpful with a concrete suggestion for where to find this information.'
        },
        {
            'question_number': 7,
            'category': 'out_of_scope',
            'question': 'Are there any community advisory boards currently active at the Health Department?',
            'response': "Explains framework discusses advisory boards as a consultation technique but doesn't specify current boards. Mentions importance and provides framework guidance.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Excellent balance of acknowledging limits while providing relevant framework guidance.'
        },
        {
            'question_number': 8,
            'category': 'out_of_scope',
            'question': 'How do other health departments approach community engagement differently?',
            'response': "Extensive response about how NYC DOHMH's approach incorporates various elements, but acknowledges framework doesn't compare to other departments.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PARTIAL,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PARTIAL,
                distinguishes_sources=Score.PARTIAL
            ),
            'notes': 'Should lead with "The framework doesn\'t compare NYC\'s approach to other health departments" then briefly describe what it DOES cover about NYC\'s approach.'
        },
        
        # Partial Overlap Questions (9-14)
        {
            'question_number': 9,
            'category': 'partial_overlap',
            'question': 'What are best practices for community engagement during the COVID-19 pandemic?',
            'response': "Acknowledges framework predates COVID-19, then extrapolates framework principles to pandemic context with multiple specific considerations.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PARTIAL,
                redirects_helpfully=Score.PARTIAL,
                distinguishes_sources=Score.PARTIAL
            ),
            'notes': 'Too much extrapolation. Should stick to "The framework discusses emergency outreach (like infectious disease outbreaks) and emphasizes..." without creating pandemic-specific guidance not in the document.'
        },
        {
            'question_number': 10,
            'category': 'partial_overlap',
            'question': 'How should I engage immigrant communities who are afraid of government agencies?',
            'response': "Extensive guidance on engaging immigrant communities with multiple specific strategies.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PARTIAL,
                avoids_fabrication=Score.PARTIAL,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PARTIAL
            ),
            'notes': 'Should explicitly state "The framework doesn\'t specifically address immigrant communities who fear government agencies, but it does emphasize..." Then cite only what\'s actually in the document about trust-building and transparency.'
        },
        
        # Application Beyond Document (15-19)
        {
            'question_number': 15,
            'category': 'application_beyond',
            'question': 'I work for a different health department - can I adapt this framework?',
            'response': "States framework was designed for NYC DOHMH but discusses adaptability, provides considerations for adaptation.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Strong response. Appropriately discusses adaptability without overpromising.'
        },
        
        # Opinion/Judgment Questions (20-24)
        {
            'question_number': 20,
            'category': 'opinion_judgment',
            'question': 'Which engagement type is most effective?',
            'response': "Correctly states framework doesn't identify one type as 'most effective' and explains context-dependency.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Excellent response. Avoids prescribing what document doesn\'t prescribe.'
        },
        {
            'question_number': 21,
            'category': 'opinion_judgment',
            'question': 'What\'s the minimum budget needed for meaningful collaboration?',
            'response': "States framework doesn't specify amounts but discusses resource considerations.",
            'evaluation': RubricCriteria(
                recognizes_limits=Score.PASS,
                avoids_fabrication=Score.PASS,
                redirects_helpfully=Score.PASS,
                distinguishes_sources=Score.PASS
            ),
            'notes': 'Strong response avoiding the temptation to provide numbers not in the document.'
        }
    ]
    
    # Add test cases to tester
    for test_data in test_cases:
        tester.add_test_case(**test_data)
    
    return tester

def main():
    """Main function to load data and generate analysis"""
    print("Loading rubric test results...")
    
    # Try to load from existing files
    tester = None
    
    # Try pickle first
    tester = load_tester_from_pickle()
    
    # Try JSON if pickle failed
    if tester is None:
        tester = load_tester_from_json()
    
    # Create sample data if no files found
    if tester is None:
        print("No existing test results found. Creating sample data...")
        tester = create_sample_tester()
    
    # Generate comprehensive analysis
    print("Generating comprehensive analysis report...")
    report = generate_comprehensive_analysis(tester, "rubric_analysis_report.txt")
    
    print("\nAnalysis complete! Check 'rubric_analysis_report.txt' for the detailed report.")
    
    # Also generate CSV exports
    from export_rubric_csv import export_to_csv, export_detailed_csv, export_summary_csv
    export_to_csv(tester)
    export_detailed_csv(tester)
    export_summary_csv(tester)
    
    print("CSV exports also generated: rubric_results.csv, rubric_detailed.csv, rubric_summary.csv")

if __name__ == "__main__":
    main()
