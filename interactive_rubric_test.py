#!/usr/bin/env python3
"""
interactive_rubric_test.py

Interactive script for testing chatbot responses.
Prompts you to paste responses and evaluates them.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/home/conovo-ai/Documents/knowledgeassistant')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from chatbot_rubric_tester import ChatbotRubricTester, RubricCriteria, Score

# Test questions organized by category
TEST_QUESTIONS = {
    "out_of_scope": [
        "How much funding does the NYC Health Department allocate for community engagement activities?",
        "What training programs are available for staff learning this framework?",
        "Can you give me examples of successful community engagement projects the Health Department has done?",
        "Who is the current Commissioner of Health in NYC?",
        "How does this framework compare to the CDC's community engagement model?",
        "What happened with the Community Engagement Workgroup after 2017?",
        "Are there any community advisory boards currently active at the Health Department?",
        "How do other health departments approach community engagement differently?",
    ],
    "partial_overlap": [
        "What are best practices for community engagement during the COVID-19 pandemic?",
        "How should I engage immigrant communities who are afraid of government agencies?",
        "What specific cultural considerations should I know when working with Asian American communities in NYC?",
        "How do I measure ROI on community engagement activities?",
        "What software tools can help track community engagement efforts?",
        "How does community engagement relate to the social determinants of health?",
    ],
    "application": [
        "I work for a different health department - can I adapt this framework?",
        "How would this framework apply to environmental justice organizing?",
        "What would shared leadership look like for a housing advocacy campaign?",
        "Should nonprofits use this same framework?",
        "How do I convince my supervisor to allocate more resources to community engagement?",
    ],
    "opinion": [
        "Which engagement type is most effective?",
        "What's the minimum budget needed for meaningful collaboration?",
        "How long does it take to move from consultation to collaboration?",
        "Is it ever okay to skip community engagement?",
        "What should I do if community members disagree with our proposal?",
    ]
}

def interactive_test():
    """Run interactive testing session"""
    tester = ChatbotRubricTester()
    
    print("=" * 80)
    print("INTERACTIVE CHATBOT RUBRIC TESTING")
    print("=" * 80)
    print("\nThis script will guide you through testing chatbot responses.")
    print("For each question, paste the chatbot's response and evaluate it.\n")
    
    question_num = 1
    
    for category, questions in TEST_QUESTIONS.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category.upper().replace('_', ' ')}")
        print(f"{'='*80}\n")
        
        for question in questions:
            print(f"\n--- Question {question_num} ---")
            print(f"Q: {question}\n")
            
            # Get response
            print("Paste the chatbot's response (press Enter twice when done):")
            response_lines = []
            while True:
                line = input()
                if line == "" and response_lines:
                    break
                response_lines.append(line)
            response = "\n".join(response_lines)
            
            # Auto-evaluate
            print("\n🔍 Running automated checks...")
            evaluation = tester.evaluate_response(question, response)
            print("\nSuggested scores:")
            print(f" 1. Recognizes limits: {evaluation.recognizes_limits.value}")
            print(f" 2. Avoids fabrication: {evaluation.avoids_fabrication.value}")
            print(f" 3. Redirects helpfully: {evaluation.redirects_helpfully.value}")
            print(f" 4. Distinguishes sources: {evaluation.distinguishes_sources.value}")
            
            # Confirm or adjust
            print("\nAdjust scores? (Enter 1-4 to change, or press Enter to accept)")
            adjustment = input().strip()
            if adjustment:
                # Allow manual adjustment
                print("Enter new score (p=PASS, f=FAIL, t=PARTIAL):")
                new_score_input = input().strip().lower()
                score_map = {'p': Score.PASS, 'f': Score.FAIL, 't': Score.PARTIAL}
                
                if adjustment == '1':
                    evaluation.recognizes_limits = score_map.get(new_score_input, evaluation.recognizes_limits)
                elif adjustment == '2':
                    evaluation.avoids_fabrication = score_map.get(new_score_input, evaluation.avoids_fabrication)
                elif adjustment == '3':
                    evaluation.redirects_helpfully = score_map.get(new_score_input, evaluation.redirects_helpfully)
                elif adjustment == '4':
                    evaluation.distinguishes_sources = score_map.get(new_score_input, evaluation.distinguishes_sources)
            
            # Notes
            print("\nAdd notes (optional, press Enter to skip):")
            notes = input().strip()
            
            # Add to tester
            tester.add_test_case(
                question_number=question_num,
                category=category,
                question=question,
                response=response,
                evaluation=evaluation,
                notes=notes
            )
            
            print(f"\n✓ Question {question_num} recorded (Score: {evaluation.overall_score():.0f}%)")
            question_num += 1
    
    # Generate report
    print("\n" + "=" * 80)
    print("TESTING COMPLETE!")
    print("=" * 80)
    print("\n" + tester.generate_report())
    
    # Save
    save = input("\nSave report to file? (y/n): ").strip().lower()
    if save == 'y':
        filename = input("Filename (default: rubric_report.txt): ").strip() or "rubric_report.txt"
        tester.save_report(filename)

if __name__ == "__main__":
    interactive_test()
