# ColumnGrid Basic Usage Example
# Demonstrates basic column grid functionality from drawbotgrid

import os

import drawBot as db
from drawBotGrid import ColumnGrid

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create a column grid with 8 subdivisions and 10pt gutter
# Parameters: (x, y, width, height), subdivisions, gutter
columns = ColumnGrid((50, 50, 742, 495), subdivisions=8, gutter=10)

print("✅ Created ColumnGrid with 8 subdivisions and 10pt gutter")
print(f"📏 Grid width: {columns.width}, height: {columns.height}")

# Draw individual rectangles at specific column positions
db.fill(0, 1, 0, 0.5)  # Green with transparency

# Draw rectangles at individual column positions
db.rect(columns[0], 450, 50, 50)  # Column 0
db.rect(columns[1], 450, 50, 50)  # Column 1
db.rect(columns[2], 450, 50, 50)  # Column 2
db.rect(columns[3], 450, 50, 50)  # Column 3
db.rect(columns[4], 450, 50, 50)  # Column 4
db.rect(columns[5], 450, 50, 50)  # Column 5
db.rect(columns[6], 450, 50, 50)  # Column 6
db.rect(columns[7], 450, 50, 50)  # Column 7

# Add labels for clarity
db.fill(0)  # Black text
db.fontSize(14)
db.text("ColumnGrid Basic Usage", (50, 550))
db.fontSize(10)
db.text("8 columns with 10pt gutters - individual column positioning", (50, 530))

# Draw grid guidelines to visualize the structure
db.stroke(0, 0, 0, 0.2)  # Light gray
db.strokeWidth(1)
db.fill(None)  # No fill for guidelines

for i in range(8):
    x = columns[i]
    db.line((x, 0), (x, db.height()))

    # Add column numbers
    db.fill(0, 0, 0, 0.7)
    db.fontSize(8)
    db.text(f"Col {i}", (x + 2, 10))
    db.fill(None)

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "01_column_grid_basic.png"))

print("✅ Saved to output/01_column_grid_basic.png")
