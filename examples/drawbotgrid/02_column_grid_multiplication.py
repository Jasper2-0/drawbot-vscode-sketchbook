# ColumnGrid with Multiplication Example
# Demonstrates using column width multipliers for spanning multiple columns

import drawBot as db
from drawBotGrid import ColumnGrid
import os

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create a column grid with 8 subdivisions and 10pt gutter
columns = ColumnGrid((50, 50, 742, 495), subdivisions=8, gutter=10)

print("✅ Created ColumnGrid for multiplication example")
print(f"📏 Single column width: {columns * 1}")
print(f"📏 Triple column width: {columns * 3}")

# Draw rectangles spanning different numbers of columns
db.fill(1, 0, 0, 0.5)  # Red with transparency

# Single column width rectangles
db.rect(columns[0], 400, columns * 1, 80)  # 1 column wide
db.rect(columns[2], 400, columns * 1, 80)  # 1 column wide
db.rect(columns[4], 400, columns * 1, 80)  # 1 column wide
db.rect(columns[6], 400, columns * 1, 80)  # 1 column wide

# Multi-column width rectangles
db.fill(0, 0, 1, 0.5)  # Blue with transparency
db.rect(columns[0], 300, columns * 3, 80)  # 3 columns wide
db.rect(columns[4], 300, columns * 4, 80)  # 4 columns wide

# Different combinations
db.fill(0, 1, 0, 0.5)  # Green with transparency
db.rect(columns[0], 200, columns * 2, 60)  # 2 columns wide
db.rect(columns[3], 200, columns * 2, 60)  # 2 columns wide
db.rect(columns[6], 200, columns * 2, 60)  # 2 columns wide

# Full width rectangle
db.fill(1, 0.5, 0, 0.5)  # Orange with transparency
db.rect(columns[0], 100, columns * 8, 60)  # Full width (8 columns)

# Add labels for clarity
db.fill(0)  # Black text
db.fontSize(14)
db.text("ColumnGrid Multiplication", (50, 550))
db.fontSize(10)
db.text("Red: 1 column | Blue: 3-4 columns | Green: 2 columns | Orange: 8 columns (full width)", (50, 530))

# Draw grid guidelines to visualize the structure
db.stroke(0, 0, 0, 0.2)  # Light gray
db.strokeWidth(1)
db.fill(None)  # No fill for guidelines

for i in range(8):
    x = columns[i]
    db.line((x, 50), (x, 500))
    
    # Add column numbers
    db.fill(0, 0, 0, 0.7)
    db.fontSize(8)
    db.text(f"{i}", (x + 2, 60))
    db.fill(None)

# Add width annotations
db.fill(0, 0, 0, 0.8)
db.fontSize(8)
db.text("1×", (columns[0] + 10, 420))
db.text("3×", (columns[0] + 10, 320))
db.text("4×", (columns[4] + 10, 320))
db.text("2×", (columns[0] + 10, 220))
db.text("8×", (columns[0] + 10, 120))

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "02_column_grid_multiplication.png"))

print("✅ Saved to output/02_column_grid_multiplication.png")