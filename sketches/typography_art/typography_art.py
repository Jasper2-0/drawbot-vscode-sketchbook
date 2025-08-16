# Typography Art Template
# Demonstrates text manipulation and creative typography

import math

import drawBot as db

# Set canvas size
db.size(600, 800)

# Set background gradient effect
for i in range(100):
    gray = 0.9 + i * 0.001
    db.fill(gray, gray * 0.95, gray * 0.9)
    db.rect(0, i * 8, db.width(), 8)

# Main title
db.fill(0.1, 0.1, 0.3)
db.fontSize(48)
db.font("Helvetica-Bold")
title_text = "CREATIVE"
text_width, text_height = db.textSize(title_text)
db.text(title_text, ((db.width() - text_width) / 2, 650))

# Subtitle with different styling
db.fontSize(24)
db.font("Helvetica-Light")
subtitle = "Typography"
sub_width, sub_height = db.textSize(subtitle)
db.text(subtitle, ((db.width() - sub_width) / 2, 610))

# Circular text arrangement
center_x = db.width() / 2
center_y = 400
radius = 120

text_to_curve = "DESIGN • ART • CODE • "
char_count = len(text_to_curve)

db.fontSize(16)
db.font("Helvetica")

for i, char in enumerate(text_to_curve):
    # Calculate angle for each character
    angle = (i / char_count) * 360

    # Convert to radians
    rad = math.radians(angle - 90)  # -90 to start at top

    # Calculate position
    x = center_x + radius * math.cos(rad)
    y = center_y + radius * math.sin(rad)

    # Save state and transform
    db.save()
    db.translate(x, y)
    db.rotate(angle)

    # Draw character
    db.fill(0.2, 0.4, 0.7)
    char_width, char_height = db.textSize(char)
    db.text(char, (-char_width / 2, -char_height / 2))

    db.restore()

# Text effects with transparency
words = ["BOLD", "ITALIC", "CREATIVE", "DYNAMIC"]
y_positions = [300, 250, 200, 150]

for i, word in enumerate(words):
    db.fontSize(32 + i * 4)

    # Create shadow effect
    db.fill(0, 0, 0, 0.3)
    db.text(word, (55, y_positions[i] - 3))

    # Main text with color
    hue = i / len(words)
    if hue < 0.5:
        db.fill(1 - hue, 0.3, 0.7)
    else:
        db.fill(0.3, hue, 1 - hue)

    db.text(word, (50, y_positions[i]))

# Footer text
db.fontSize(12)
db.fill(0.5)
db.font("Helvetica")
footer = "Generated with DrawBot"
footer_width, _ = db.textSize(footer)
db.text(footer, ((db.width() - footer_width) / 2, 30))

# Save the result
db.saveImage("typography_art_output.png")
