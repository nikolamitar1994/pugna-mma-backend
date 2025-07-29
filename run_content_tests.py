#!/usr/bin/env python
"""
Comprehensive test runner for EPIC-09 Content Management System.

This script runs all tests for the content management system and provides
detailed reporting on test results, coverage, and system functionality.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_django():
    """Set up Django environment for testing"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.test')
    django.setup()


def run_content_tests():
    """Run all content management system tests"""
    print("=" * 80)
    print("EPIC-09 CONTENT MANAGEMENT SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    # Test categories to run
    test_categories = [
        {
            'name': 'Model Tests',
            'command': ['test', 'content.tests.test_models', '-v', '2'],
            'description': 'Testing all content models, validation, and relationships'
        },
        {
            'name': 'API Tests',
            'command': ['test', 'content.tests.test_api', '-v', '2'],
            'description': 'Testing REST API endpoints, permissions, and CRUD operations'
        },
        {
            'name': 'Admin Interface Tests',
            'command': ['test', 'content.tests.test_admin', '-v', '2'],
            'description': 'Testing Django admin functionality and workflow actions'
        },
        {
            'name': 'SEO Features Tests',
            'command': ['test', 'content.tests.test_seo', '-v', '2'],
            'description': 'Testing sitemaps, RSS feeds, structured data, and meta tags'
        },
        {
            'name': 'Integration Tests',
            'command': ['test', 'content.tests.test_integration', '-v', '2'],
            'description': 'Testing system integration, workflows, and cross-component functionality'
        }
    ]
    
    results = {}
    
    for category in test_categories:
        print(f"\n📋 Running {category['name']}")
        print(f"Description: {category['description']}")
        print("-" * 60)
        
        try:
            # Run the test command
            result = execute_from_command_line(['manage.py'] + category['command'])
            results[category['name']] = 'PASSED'
            print(f"✅ {category['name']} - PASSED")
            
        except SystemExit as e:
            if e.code != 0:
                results[category['name']] = 'FAILED'
                print(f"❌ {category['name']} - FAILED")
            else:
                results[category['name']] = 'PASSED'
                print(f"✅ {category['name']} - PASSED")
        except Exception as e:
            results[category['name']] = f'ERROR: {str(e)}'
            print(f"🔥 {category['name']} - ERROR: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    total_tests = len(test_categories)
    passed_tests = sum(1 for result in results.values() if result == 'PASSED')
    failed_tests = total_tests - passed_tests
    
    for name, result in results.items():
        status_icon = "✅" if result == "PASSED" else "❌"
        print(f"{status_icon} {name}: {result}")
    
    print(f"\nTotal: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! EPIC-09 Content Management System is ready for production!")
        return True
    else:
        print(f"\n⚠️  {failed_tests} test categories failed. Please review and fix issues.")
        return False


def run_specific_test_suite():
    """Run a specific test suite based on command line argument"""
    if len(sys.argv) < 2:
        print("Usage: python run_content_tests.py [models|api|admin|seo|integration|all]")
        return
    
    test_type = sys.argv[1].lower()
    
    test_commands = {
        'models': ['test', 'content.tests.test_models', '-v', '2'],
        'api': ['test', 'content.tests.test_api', '-v', '2'],
        'admin': ['test', 'content.tests.test_admin', '-v', '2'],
        'seo': ['test', 'content.tests.test_seo', '-v', '2'],
        'integration': ['test', 'content.tests.test_integration', '-v', '2'],
        'all': ['test', 'content.tests', '-v', '2']
    }
    
    if test_type not in test_commands:
        print(f"Unknown test type: {test_type}")
        print("Available options: models, api, admin, seo, integration, all")
        return
    
    print(f"Running {test_type} tests...")
    execute_from_command_line(['manage.py'] + test_commands[test_type])


def run_with_coverage():
    """Run tests with coverage reporting"""
    try:
        import coverage
    except ImportError:
        print("Coverage.py not installed. Install with: pip install coverage")
        return
    
    print("Running tests with coverage analysis...")
    
    # Start coverage
    cov = coverage.Coverage(source=['content'])
    cov.start()
    
    # Run tests
    success = run_content_tests()
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "=" * 80)
    print("COVERAGE REPORT")
    print("=" * 80)
    
    cov.report()
    
    # Generate HTML report
    cov.html_report(directory='htmlcov')
    print("\nHTML coverage report generated in 'htmlcov' directory")
    
    return success


def create_test_data():
    """Create comprehensive test data for manual testing"""
    print("Creating comprehensive test data...")
    
    try:
        from content.tests.test_data import create_comprehensive_test_data
        summary = create_comprehensive_test_data()
        
        print("\nTest data created successfully!")
        print("Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
        print("\nYou can now:")
        print("1. Access Django admin at /admin/ with created users")
        print("2. Test API endpoints with various data")
        print("3. View content pages with realistic data")
        
    except Exception as e:
        print(f"Error creating test data: {str(e)}")


def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    
    try:
        from content.tests.test_data import cleanup_test_data
        cleanup_test_data()
        print("Test data cleaned up successfully!")
        
    except Exception as e:
        print(f"Error cleaning up test data: {str(e)}")


def show_help():
    """Show help information"""
    print("""
EPIC-09 Content Management System Test Runner

Usage:
    python run_content_tests.py [command] [options]

Commands:
    (no args)           Run all test suites with detailed reporting
    models              Run only model tests
    api                 Run only API tests
    admin               Run only admin interface tests
    seo                 Run only SEO feature tests
    integration         Run only integration tests
    all                 Run all content tests
    
    coverage            Run all tests with coverage analysis
    create-data         Create comprehensive test data
    cleanup-data        Clean up test data
    help                Show this help message

Examples:
    python run_content_tests.py                    # Run all test suites
    python run_content_tests.py models             # Run only model tests
    python run_content_tests.py coverage           # Run with coverage
    python run_content_tests.py create-data        # Create test data

Test Categories:
    📋 Model Tests - Test all content models, validation, and relationships
    🔌 API Tests - Test REST API endpoints, permissions, and CRUD operations  
    🛠️  Admin Tests - Test Django admin functionality and workflow actions
    🔍 SEO Tests - Test sitemaps, RSS feeds, structured data, and meta tags
    🔄 Integration Tests - Test system integration and workflows

For detailed test output, all tests run with verbosity level 2.
    """)


def main():
    """Main entry point"""
    setup_django()
    
    if len(sys.argv) == 1:
        # No arguments - run all tests
        success = run_content_tests()
        sys.exit(0 if success else 1)
    
    command = sys.argv[1].lower()
    
    if command == 'help':
        show_help()
    elif command == 'coverage':
        success = run_with_coverage()
        sys.exit(0 if success else 1)
    elif command == 'create-data':
        create_test_data()
    elif command == 'cleanup-data':
        cleanup_test_data()
    elif command in ['models', 'api', 'admin', 'seo', 'integration', 'all']:
        run_specific_test_suite()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python run_content_tests.py help' for usage information")
        sys.exit(1)


if __name__ == '__main__':
    main()