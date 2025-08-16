# Typography Art Template
# Demonstrates text manipulation and creative typography

import drawBot as drawbot
import math

# Set canvas size
drawbot.size(600, 800)

# Set background gradient effect
for i in range(100):
    gray = 0.9 + i * 0.001
    drawbot.fill(gray, gray * 0.95, gray * 0.9)
    drawbot.rect(0, i * 8, drawbot.width(), 8)

# Main title
drawbot.fill(0.1, 0.1, 0.3)
drawbot.fontSize(48)
drawbot.font("Helvetica-Bold")
title_text = "CREATIVE"
text_width, text_height = drawbot.textSize(title_text)
drawbot.text(title_text, ((drawbot.width() - text_width) / 2, 650))

# Subtitle with different styling
drawbot.fontSize(24)
drawbot.font("Helvetica-Light")
subtitle = "Typography"
sub_width, sub_height = drawbot.textSize(subtitle)
drawbot.text(subtitle, ((drawbot.width() - sub_width) / 2, 610))

# Circular text arrangement
center_x = drawbot.width() / 2
center_y = 400
radius = 120

text_to_curve = "DESIGN • ART • CODE • "
char_count = len(text_to_curve)

drawbot.fontSize(16)
drawbot.font("Helvetica")

for i, char in enumerate(text_to_curve):
    # Calculate angle for each character
    angle = (i / char_count) * 360
    
    # Convert to radians
    rad = math.radians(angle - 90)  # -90 to start at top
    
    # Calculate position
    x = center_x + radius * math.cos(rad)
    y = center_y + radius * math.sin(rad)
    
    # Save state and transform
    drawbot.save()
    drawbot.translate(x, y)
    drawbot.rotate(angle)
    
    # Draw character
    drawbot.fill(0.2, 0.4, 0.7)
    char_width, char_height = drawbot.textSize(char)
    drawbot.text(char, (-char_width/2, -char_height/2))
    
    drawbot.restore()

# Text effects with transparency
words = ["BOLD", "ITALIC", "CREATIVE", "DYNAMIC"]
y_positions = [300, 250, 200, 150]

for i, word in enumerate(words):
    drawbot.fontSize(32 + i * 4)
    
    # Create shadow effect
    drawbot.fill(0, 0, 0, 0.3)
    drawbot.text(word, (55, y_positions[i] - 3))
    
    # Main text with color
    hue = i / len(words)
    if hue < 0.5:
        drawbot.fill(1 - hue, 0.3, 0.7)
    else:
        drawbot.fill(0.3, hue, 1 - hue)
    
    drawbot.text(word, (50, y_positions[i]))

# Footer text
drawbot.fontSize(12)
drawbot.fill(0.5)
drawbot.font("Helvetica")
footer = "Generated with DrawBot"
footer_width, _ = drawbot.textSize(footer)
drawbot.text(footer, ((drawbot.width() - footer_width) / 2, 30))

# Save the result
drawbot.saveImage("typography_art_output.png")