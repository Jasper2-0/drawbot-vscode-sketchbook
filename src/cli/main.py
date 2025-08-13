#!/usr/bin/env python3
"""
DrawBot Sketchbook CLI
A command-line interface for managing and running DrawBot sketches.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from ..core.project_structure import ProjectStructure
from ..core.sketch_manager import SketchManager
from ..core.sketch_runner import SketchRunner


def init_project(args):
    """Initialize a new DrawBot sketchbook project."""
    project_path = Path(args.path) if args.path else Path.cwd()
    
    print(f"Initializing DrawBot sketchbook in: {project_path}")
    
    try:
        ps = ProjectStructure(project_path)
        ps.create_directories()
        
        print("✅ Project structure created successfully!")
        print("\nDirectories created:")
        for directory in sorted(ProjectStructure.REQUIRED_DIRECTORIES):
            print(f"  📁 {directory}/")
        
        print(f"\n🎨 Your DrawBot sketchbook is ready!")
        print(f"📍 Location: {project_path}")
        print("\nNext steps:")
        print("  • Create a new sketch: python -m src.cli.main new my_first_sketch")
        print("  • List templates: python -m src.cli.main templates")
        
    except Exception as e:
        print(f"❌ Error initializing project: {e}")
        return 1
    
    return 0


def create_sketch(args):
    """Create a new sketch from template."""
    project_path = Path.cwd()
    
    try:
        # Validate project structure
        ps = ProjectStructure(project_path)
        if not ps.validate_structure():
            print("❌ Not a valid DrawBot sketchbook project.")
            print("Run 'python -m src.cli.main init' to initialize a project.")
            return 1
        
        sm = SketchManager(project_path)
        sketch_path = sm.create_sketch(args.name, template=args.template)
        
        print(f"✅ Created new sketch: {sketch_path}")
        
        if args.template:
            print(f"📝 Using template: {args.template}")
        
        print(f"🎨 Ready to start creating!")
        print(f"   Edit: {sketch_path}")
        print(f"   Run:  python -m src.cli.main run {args.name}")
        
    except Exception as e:
        print(f"❌ Error creating sketch: {e}")
        return 1
    
    return 0


def list_templates(args):
    """List available sketch templates."""
    project_path = Path.cwd()
    
    try:
        ps = ProjectStructure(project_path)
        if not ps.validate_structure():
            print("❌ Not a valid DrawBot sketchbook project.")
            return 1
        
        templates_dir = project_path / 'templates'
        templates = list(templates_dir.glob('*.py'))
        
        if not templates:
            print("📝 No templates found.")
            return 0
        
        print("📝 Available templates:")
        print()
        
        for template in sorted(templates):
            template_name = template.stem
            print(f"  🎨 {template_name}")
            
            # Try to extract description from template
            try:
                content = template.read_text()
                first_line = content.strip().split('\n')[0]
                if first_line.startswith('#'):
                    description = first_line[1:].strip()
                    print(f"     {description}")
            except:
                pass
            print()
        
        print("Usage: python -m src.cli.main new my_sketch --template <template_name>")
        
    except Exception as e:
        print(f"❌ Error listing templates: {e}")
        return 1
    
    return 0


def list_sketches(args):
    """List all sketches in the project."""
    project_path = Path.cwd()
    
    try:
        ps = ProjectStructure(project_path)
        if not ps.validate_structure():
            print("❌ Not a valid DrawBot sketchbook project.")
            return 1
        
        sm = SketchManager(project_path)
        sketches = sm.list_all_sketches()
        
        if not sketches:
            print("📝 No sketches found.")
            print("Create one with: python -m src.cli.main new my_sketch")
            return 0
        
        print(f"📝 Found {len(sketches)} sketches:")
        print()
        
        for sketch in sorted(sketches):
            rel_path = sketch.relative_to(project_path / 'sketches')
            print(f"  🎨 {rel_path}")
            
            # Try to get metadata
            try:
                metadata = sm.get_sketch_metadata(sketch)
                if metadata.get('description'):
                    print(f"     {metadata['description']}")
            except:
                pass
            print()
        
    except Exception as e:
        print(f"❌ Error listing sketches: {e}")
        return 1
    
    return 0


def run_sketch(args):
    """Run a sketch file."""
    project_path = Path.cwd()
    
    try:
        ps = ProjectStructure(project_path)
        if not ps.validate_structure():
            print("❌ Not a valid DrawBot sketchbook project.")
            return 1
        
        sm = SketchManager(project_path)
        sketch_path = sm.find_sketch(args.name)
        
        if not sketch_path:
            print(f"❌ Sketch not found: {args.name}")
            print("List available sketches: python -m src.cli.main list")
            return 1
        
        print(f"🚀 Running sketch: {sketch_path.name}")
        print()
        
        # Validate syntax first
        sr = SketchRunner(project_path, timeout=args.timeout)
        validation = sr.validate_sketch_before_run(sketch_path)
        
        if not validation.success:
            print(f"❌ Syntax error in sketch:")
            print(f"   {validation.error}")
            return 1
        
        # Run the sketch
        result = sr.run_sketch(sketch_path)
        
        if result.success:
            print(f"✅ Sketch completed successfully!")
            print(f"⏱️  Execution time: {result.execution_time:.2f}s")
            
            if result.stdout:
                print("\n📄 Output:")
                print(result.stdout)
            
            if result.output_path:
                print(f"🖼️  Generated: {result.output_path}")
        else:
            print(f"❌ Sketch execution failed:")
            print(f"   {result.error}")
            
            if result.stderr:
                print(f"\n📄 Error details:")
                print(result.stderr)
            
            return 1
        
    except Exception as e:
        print(f"❌ Error running sketch: {e}")
        return 1
    
    return 0


def validate_sketch(args):
    """Validate a sketch for syntax errors."""
    project_path = Path.cwd()
    
    try:
        ps = ProjectStructure(project_path)
        if not ps.validate_structure():
            print("❌ Not a valid DrawBot sketchbook project.")
            return 1
        
        sm = SketchManager(project_path)
        sketch_path = sm.find_sketch(args.name)
        
        if not sketch_path:
            print(f"❌ Sketch not found: {args.name}")
            return 1
        
        sr = SketchRunner(project_path)
        result = sr.validate_sketch_before_run(sketch_path)
        
        if result.success:
            print(f"✅ Sketch syntax is valid: {sketch_path.name}")
        else:
            print(f"❌ Syntax errors found:")
            print(f"   {result.error}")
            return 1
        
    except Exception as e:
        print(f"❌ Error validating sketch: {e}")
        return 1
    
    return 0


def project_info(args):
    """Show project information and status."""
    project_path = Path.cwd()
    
    try:
        ps = ProjectStructure(project_path)
        
        print(f"📍 Project path: {project_path}")
        print()
        
        if ps.validate_structure():
            print("✅ Valid DrawBot sketchbook project")
            
            # Count sketches
            sm = SketchManager(project_path)
            sketches = sm.list_all_sketches()
            print(f"🎨 Sketches: {len(sketches)}")
            
            # Count templates
            templates_dir = project_path / 'templates'
            templates = list(templates_dir.glob('*.py')) if templates_dir.exists() else []
            print(f"📝 Templates: {len(templates)}")
            
        else:
            print("❌ Not a valid DrawBot sketchbook project")
            missing = ps.get_missing_directories()
            if missing:
                print(f"📁 Missing directories: {', '.join(missing)}")
            print("Run 'python -m src.cli.main init' to set up the project.")
            
    except Exception as e:
        print(f"❌ Error getting project info: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DrawBot Sketchbook - A creative coding environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli.main init                    # Initialize new project
  python -m src.cli.main new my_sketch           # Create new sketch
  python -m src.cli.main new art --template basic_shapes   # Create from template
  python -m src.cli.main run my_sketch           # Run a sketch
  python -m src.cli.main list                    # List all sketches
  python -m src.cli.main templates               # List templates
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize a new DrawBot sketchbook project')
    init_parser.add_argument('path', nargs='?', help='Project directory (default: current directory)')
    init_parser.set_defaults(func=init_project)
    
    # New sketch command
    new_parser = subparsers.add_parser('new', help='Create a new sketch')
    new_parser.add_argument('name', help='Name of the sketch')
    new_parser.add_argument('--template', '-t', help='Template to use')
    new_parser.set_defaults(func=create_sketch)
    
    # Templates command
    templates_parser = subparsers.add_parser('templates', help='List available templates')
    templates_parser.set_defaults(func=list_templates)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all sketches')
    list_parser.set_defaults(func=list_sketches)
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a sketch')
    run_parser.add_argument('name', help='Name of the sketch to run')
    run_parser.add_argument('--timeout', '-T', type=float, default=30.0, 
                           help='Execution timeout in seconds (default: 30)')
    run_parser.set_defaults(func=run_sketch)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate sketch syntax')
    validate_parser.add_argument('name', help='Name of the sketch to validate')
    validate_parser.set_defaults(func=validate_sketch)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show project information')
    info_parser.set_defaults(func=project_info)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())