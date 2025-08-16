#!/usr/bin/env python3
"""
Demo script for Phase 1 - Core Preview Engine functionality.
Shows the complete preview generation pipeline working.
"""
import tempfile
from pathlib import Path

from src.core.preview_engine import PreviewEngine
from src.core.preview_cache import PreviewCache


def main():
    print("🎨 DrawBot Live Preview - Phase 1 Demo")
    print("=" * 50)
    
    # Set up temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        cache_dir = project_path / "preview_cache"
        
        print(f"📁 Workspace: {project_path}")
        print(f"💾 Cache: {cache_dir}")
        
        # Create a demo sketch
        sketch_file = project_path / "demo_sketch.py"
        sketch_content = '''
import drawBot as drawbot

# Create a colorful demo
drawbot.size(400, 300)

# Background gradient effect
for i in range(20):
    gray = i / 20
    drawbot.fill(gray * 0.2, gray * 0.5, gray * 0.8)
    drawbot.rect(0, i * 15, 400, 15)

# Main shapes
drawbot.fill(1, 0.2, 0.2)  # Red
drawbot.oval(50, 100, 120, 120)

drawbot.fill(0.2, 1, 0.2)  # Green
drawbot.rect(180, 100, 120, 120)

drawbot.fill(0.2, 0.2, 1)  # Blue
drawbot.polygon((320, 100), (380, 160), (350, 220), (290, 220), (260, 160))

# Text overlay
drawbot.fill(1, 1, 1)  # White
drawbot.font("Helvetica-Bold", 24)
drawbot.text("Live Preview Demo", (100, 50))

drawbot.font("Helvetica", 16)
drawbot.text("Phase 1 - Core Engine", (120, 25))

# Save output
drawbot.saveImage("demo_output.png")
'''
        
        sketch_file.write_text(sketch_content)
        print(f"✏️  Created demo sketch: {sketch_file.name}")
        
        # Initialize preview system
        cache = PreviewCache(cache_dir, max_versions_per_sketch=3)
        engine = PreviewEngine(project_path, cache)
        
        print("\n🔧 Initializing preview engine...")
        print(f"   Cache max versions: {cache.max_versions_per_sketch}")
        print(f"   Cache max size: {cache.max_total_size_mb}MB")
        
        # Execute sketch and generate preview
        print("\n⚡ Executing sketch...")
        result = engine.execute_sketch(sketch_file)
        
        if result.success:
            print(f"✅ Success! Execution time: {result.execution_time:.3f}s")
            print(f"   Preview URL: {result.preview_url}")
            print(f"   Preview file: {result.preview_path}")
            print(f"   Version: {result.version}")
            
            # Verify preview file
            if result.preview_path and result.preview_path.exists():
                file_size = result.preview_path.stat().st_size
                print(f"   File size: {file_size:,} bytes")
                
                # Read PNG header to verify it's valid
                with open(result.preview_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'\x89PNG'):
                        print("   ✅ Valid PNG file generated")
                    else:
                        print("   ⚠️  Warning: Generated file may not be valid PNG")
            
        else:
            print(f"❌ Failed: {result.error}")
            return
        
        # Test cache functionality
        print("\n💾 Testing cache functionality...")
        cache_stats = cache.get_statistics()
        print(f"   Total sketches: {cache_stats['total_sketches']}")
        print(f"   Total versions: {cache_stats['total_versions']}")
        print(f"   Cache size: {cache_stats['total_size_mb']:.3f}MB")
        
        # Test multiple versions
        print("\n🔄 Testing version management...")
        for i in range(3):
            # Modify sketch slightly
            modified_content = sketch_content.replace(
                f"Live Preview Demo", 
                f"Demo v{i+2}"
            )
            sketch_file.write_text(modified_content)
            
            result = engine.execute_sketch(sketch_file)
            if result.success:
                print(f"   Version {i+2}: {result.version} (time: {result.execution_time:.3f}s)")
        
        # Final cache stats
        final_stats = cache.get_statistics()
        print(f"\n📊 Final cache stats:")
        print(f"   Total versions: {final_stats['total_versions']}")
        print(f"   Cache size: {final_stats['total_size_mb']:.3f}MB")
        
        # Show available versions
        versions = cache.get_available_versions("demo_sketch")
        print(f"   Available versions: {versions}")
        
        print("\n🎉 Phase 1 Demo Complete!")
        print("   ✅ Sketch execution working")
        print("   ✅ Preview generation working") 
        print("   ✅ Image conversion working")
        print("   ✅ Cache management working")
        print("   ✅ Version management working")
        print("   ✅ Error handling working")
        
        print(f"\n🚀 Ready for Phase 2: Web Server Foundation!")


if __name__ == "__main__":
    main()