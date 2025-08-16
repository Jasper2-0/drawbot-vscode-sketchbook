# BaselineGrid Example
# Demonstrates baseline grid functionality for text layout

import drawBot as db
from drawBotGrid import BaselineGrid, ColumnGrid, baselineGridTextBox
import os

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create a baseline grid with 12pt line height
baselines = BaselineGrid.from_margins((0, 0, 0, 0), line_height=12)

print("✅ Created BaselineGrid with 12pt line height")
print(f"📏 Number of baselines: {len(baselines)}")
print(f"📏 Line height: {baselines.line_height}")

# Create columns to work with the baseline grid
columns = ColumnGrid((50, 50, 742, 495), subdivisions=3, gutter=20)

# Sample text content
sample_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium."""

# Set up text styling
db.font("Helvetica")
db.fontSize(10)
db.fill(0.2, 0.2, 0.2)  # Dark gray text

# Use baselineGridTextBox for text that snaps to the baseline grid
# This function automatically adjusts text to align with baseline grid
baselineGridTextBox(
    sample_text,
    (columns[0], columns.bottom, columns * 1, columns.height * 0.8),  # First column
    baselines
)

# Different font size in second column
db.fontSize(12)
baselineGridTextBox(
    "This text uses a different font size but still snaps to the same baseline grid. " + sample_text[:200] + "...",
    (columns[1], columns.bottom, columns * 1, columns.height * 0.8),  # Second column
    baselines
)

# Larger font size in third column
db.fontSize(14)
db.fill(0, 0, 0.6)  # Blue text
baselineGridTextBox(
    "Large heading text that also aligns to baseline grid.\n\n" + sample_text[:150] + "...",
    (columns[2], columns.bottom, columns * 1, columns.height * 0.8),  # Third column
    baselines
)

# Add labels for clarity
db.fill(0)  # Black text
db.fontSize(16)
db.text("BaselineGrid Text Layout", (50, 570))
db.fontSize(10)
db.text("Text in different sizes automatically snapping to 12pt baseline grid", (50, 550))

# Draw baseline grid lines to visualize the structure
db.stroke(1, 0, 0, 0.3)  # Light red lines
db.strokeWidth(0.5)
db.fill(None)

# Draw every 4th baseline to avoid clutter
for i in range(0, len(baselines), 4):
    if i < len(baselines):
        y = baselines[i]
        db.line((50, y), (792, y))

# Draw column guidelines
db.stroke(0, 0, 0, 0.2)  # Light gray
db.strokeWidth(1)

for i in range(3):
    x = columns[i]
    db.line((x, 50), (x, 545))
    
    # Add column labels
    db.fill(0, 0, 0, 0.6)
    db.fontSize(8)
    db.text(f"Column {i+1}", (x + 5, 530))
    db.text(f"Font: {[10, 12, 14][i]}pt", (x + 5, 520))
    db.fill(None)

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "05_baseline_grid.png"))

print("✅ Saved to output/05_baseline_grid.png")