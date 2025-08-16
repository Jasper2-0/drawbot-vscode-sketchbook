# Basic Shapes Template
# A simple template demonstrating basic DrawBot shapes

import drawBot as db

# Set canvas size
db.size(800, 600)

# Set background color (white)
db.fill(1)
db.rect(0, 0, db.width(), db.height())

# Draw a red rectangle
db.fill(1, 0, 0)  # Red
db.rect(50, 50, 200, 150)

# Draw a blue oval
db.fill(0, 0, 1)  # Blue
db.oval(300, 100, 180, 120)

# Draw a green triangle (polygon)
db.fill(0, 0.7, 0)  # Green
triangle_points = [(500, 50), (650, 50), (575, 180)]
db.polygon(*triangle_points)

# Add some text
db.fill(0)  # Black
db.fontSize(24)
db.text("Basic Shapes", (50, 250))

# Save the result
db.saveImage("basic_shapes_output.png")
