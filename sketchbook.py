#!/usr/bin/env python3
"""
DrawBot Sketchbook entry point.
"""

import sys
import os

# Add the current directory to Python path to make src imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Entry point for the sketchbook command."""
    from src.cli.main import main as cli_main
    return cli_main()

if __name__ == '__main__':
    sys.exit(main())