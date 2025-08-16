#!/usr/bin/env python3
"""
DrawBot Sketchbook CLI entry point.
"""

import sys
import os

# Add the parent directory to Python path to make src imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

def main():
    """Entry point for the sketchbook command."""
    from src.cli.main import main as cli_main
    return cli_main()

if __name__ == '__main__':
    sys.exit(main())