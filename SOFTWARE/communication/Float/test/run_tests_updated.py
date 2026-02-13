#!/usr/bin/env python3
"""
Test Runner for MQTT Schema System

This script:
1. Checks for MQTT broker availability
2. Sets up the test environment
3. Runs all tests
4. Generates a test report
5. Cleans up temporary files

Uses only public-facing APIs from the MQTT schema system.
"""

import sys
import time
import socket
import subprocess
import logging
from pathlib import Path
from typing import Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_mqtt_broker(host: str = 'localhost', port: int = 1883, timeout: int = 5) -> bool:
    """Check if MQTT broker is accessible"""
    logger.info(f"Checking MQTT broker at {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info("✓ MQTT broker is accessible")
            return True
        else:
            logger.error("✗ MQTT broker is not accessible")
            return False
    except Exception as e:
        logger.error(f"✗ Error checking MQTT broker: {e}")
        return False


def check_dependencies() -> Tuple[bool, list]:
    """Check if required Python packages are installed"""
    logger.info("Checking dependencies...")
    required = ['paho.mqtt', 'yaml']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} is installed")
        except ImportError:
            logger.error(f"✗ {package} is not installed")
            missing.append(package)
    
    return len(missing) == 0, missing


def check_modules() -> Tuple[bool, list]:
    """Check if required MQTT schema modules are available"""
    logger.info("Checking MQTT schema modules...")
    # Only check public-facing modules
    required_modules = [
        'base_types',
        'mqtt',
        'config_manager',
        'mqtt_schema_adapter',
        'mqtt_schema_types'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✓ {module}.py is available")
        except ImportError:
            logger.error(f"✗ {module}.py is not available")
            missing.append(module)
    
    return len(missing) == 0, missing


def run_unit_tests() -> int:
    """Run the comprehensive unit tests"""
    logger.info("\n" + "="*70)
    logger.info("Running Unit Tests")
    logger.info("="*70)
    
    try:
        import test_mqtt_schema_updated as test_mqtt_schema
        return test_mqtt_schema.main()
    except Exception as e:
        logger.error(f"Failed to run unit tests: {e}")
        return 1


def run_real_world_examples() -> int:
    """Run the real-world usage examples"""
    logger.info("\n" + "="*70)
    logger.info("Running Real-World Examples")
    logger.info("="*70)
    
    try:
        import test_real_world_examples_updated as test_real_world_examples
        test_real_world_examples.main()
        return 0
    except Exception as e:
        logger.error(f"Failed to run real-world examples: {e}")
        return 1


def cleanup_temp_files():
    """Clean up temporary test files"""
    logger.info("\nCleaning up temporary files...")
    
    temp_files = [
        '/tmp/test_mqtt_config.yaml',
        '/tmp/test_integration_config.yaml',
        '/tmp/smart_home_config.yaml',
        '/tmp/industrial_config.yaml',
        '/tmp/fleet_config.yaml'
    ]
    
    removed = 0
    for file_path in temp_files:
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()
                removed += 1
                logger.info(f"Removed: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove {file_path}: {e}")
    
    if removed > 0:
        logger.info(f"✓ Cleaned up {removed} temporary file(s)")
    else:
        logger.info("No temporary files to clean up")


def generate_report(unit_test_result: int, examples_result: int):
    """Generate a test report"""
    logger.info("\n" + "="*70)
    logger.info("TEST REPORT")
    logger.info("="*70)
    
    logger.info(f"\nUnit Tests:           {'PASSED' if unit_test_result == 0 else 'FAILED'}")
    logger.info(f"Real-World Examples:  {'PASSED' if examples_result == 0 else 'FAILED'}")
    
    overall = "PASSED" if (unit_test_result == 0 and examples_result == 0) else "FAILED"
    logger.info(f"\nOverall Result:       {overall}")
    logger.info("="*70)
    
    return 0 if overall == "PASSED" else 1


def print_help():
    """Print help information"""
    help_text = """
MQTT Schema System - Test Runner

Usage:
    python run_tests_updated.py [options]

Options:
    --unit-only         Run only unit tests
    --examples-only     Run only real-world examples
    --no-cleanup        Don't clean up temporary files after tests
    --skip-broker-check Skip MQTT broker availability check
    --help, -h          Show this help message

Examples:
    python run_tests_updated.py                    # Run all tests
    python run_tests_updated.py --unit-only        # Run only unit tests
    python run_tests_updated.py --no-cleanup       # Keep temporary files
    
Environment:
    MQTT_HOST           MQTT broker hostname (default: localhost)
    MQTT_PORT           MQTT broker port (default: 1883)
    
Requirements:
    - MQTT broker running (e.g., Mosquitto)
    - Python packages: paho-mqtt, pyyaml
    - MQTT schema modules in Python path
    
Note: Uses only public-facing APIs. Abstract schema modules are internal implementation.
"""
    print(help_text)


def main():
    """Main test runner"""
    # Parse command line arguments
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print_help()
        return 0
    
    unit_only = '--unit-only' in args
    examples_only = '--examples-only' in args
    no_cleanup = '--no-cleanup' in args
    skip_broker_check = '--skip-broker-check' in args
    
    logger.info("="*70)
    logger.info("MQTT Schema System - Test Runner")
    logger.info("Using Public APIs Only")
    logger.info("="*70)
    
    # Pre-flight checks
    logger.info("\nPre-flight Checks:")
    logger.info("-" * 70)
    
    # Check MQTT broker
    if not skip_broker_check:
        mqtt_available = check_mqtt_broker()
        if not mqtt_available:
            logger.error("\n✗ MQTT broker is not available!")
            logger.error("Please start your MQTT broker (e.g., mosquitto) and try again.")
            logger.error("\nTo start Mosquitto:")
            logger.error("  sudo systemctl start mosquitto")
            logger.error("  or")
            logger.error("  mosquitto -v")
            logger.error("\nOr skip this check with --skip-broker-check")
            return 1
    else:
        logger.info("Skipping MQTT broker check (--skip-broker-check)")
    
    # Check dependencies
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        logger.error(f"\n✗ Missing dependencies: {', '.join(missing_deps)}")
        logger.error("\nInstall with:")
        logger.error("  pip install paho-mqtt pyyaml")
        return 1
    
    # Check modules
    modules_ok, missing_modules = check_modules()
    if not modules_ok:
        logger.error(f"\n✗ Missing modules: {', '.join(missing_modules)}")
        logger.error("\nMake sure all MQTT schema modules are in the Python path:")
        logger.error("  export PYTHONPATH=\"${PYTHONPATH}:$(pwd)\"")
        return 1
    
    logger.info("\n✓ All pre-flight checks passed!")
    
    # Run tests
    unit_test_result = 0
    examples_result = 0
    
    try:
        if not examples_only:
            unit_test_result = run_unit_tests()
            time.sleep(1)  # Brief pause between test suites
        
        if not unit_only:
            examples_result = run_real_world_examples()
        
    except KeyboardInterrupt:
        logger.warning("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n\nUnexpected error during tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Cleanup
    if not no_cleanup:
        cleanup_temp_files()
    else:
        logger.info("\nSkipping cleanup (--no-cleanup)")
    
    # Generate report
    return generate_report(unit_test_result, examples_result)


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
