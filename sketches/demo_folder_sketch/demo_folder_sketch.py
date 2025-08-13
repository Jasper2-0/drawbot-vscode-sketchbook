# Folder-based Generative Pattern with Data Files
# Demonstrates reading configuration from data folder

import drawBot as drawbot
import random
import json
from pathlib import Path

# Load configuration from data folder
sketch_dir = Path(__file__).parent
config_file = sketch_dir / 'data' / 'colors.json'

# Default values
palette = {
    "primary": [0.2, 0.4, 0.8],
    "secondary": [0.8, 0.2, 0.4], 
    "accent": [0.9, 0.7, 0.1]
}
opacity = 0.7

# Load config if available
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
        palette = config.get('palette', palette)
        opacity = config.get('settings', {}).get('opacity', opacity)
    print(f"✅ Loaded configuration from {config_file}")
else:
    print("⚠️ Using default configuration")

# Set canvas size
drawbot.size(800, 600)

# Set background
drawbot.fill(0.05)  # Very dark background
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

# Generate pattern using loaded colors
def draw_pattern():
    colors = list(palette.values())
    
    for i in range(80):
        # Choose random color from palette
        color = random.choice(colors)
        drawbot.fill(color[0], color[1], color[2], opacity)
        
        x = random.randint(0, int(drawbot.width()))
        y = random.randint(0, int(drawbot.height()))
        size = random.randint(15, 80)
        
        # Add some rotation for variety
        with drawbot.savedState():
            drawbot.translate(x, y)
            drawbot.rotate(random.randint(0, 360))
            drawbot.oval(-size/2, -size/2, size, size)

print("🎨 Generating pattern...")
draw_pattern()
print(f"📊 Used colors: {list(palette.keys())}")

# Save the result to output folder
output_dir = sketch_dir / 'output'
output_dir.mkdir(exist_ok=True)
output_file = output_dir / 'pattern.png'
drawbot.saveImage(str(output_file))
print(f"✅ Saved to {output_file}")