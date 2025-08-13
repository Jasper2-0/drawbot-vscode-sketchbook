# Basic Shapes Template
# A simple template demonstrating basic DrawBot shapes

import drawbot

# Set canvas size
drawbot.size(800, 600)

# Set background color (white)
drawbot.fill(1)
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

# Draw a red rectangle
drawbot.fill(1, 0, 0)  # Red
drawbot.rect(50, 50, 200, 150)

# Draw a blue oval
drawbot.fill(0, 0, 1)  # Blue
drawbot.oval(300, 100, 180, 120)

# Draw a green triangle (polygon)
drawbot.fill(0, 0.7, 0)  # Green
triangle_points = [(500, 50), (650, 50), (575, 180)]
drawbot.polygon(*triangle_points)

# Add some text
drawbot.fill(0)  # Black
drawbot.fontSize(24)
drawbot.text("Basic Shapes", (50, 250))

# Save the result
drawbot.saveImage("basic_shapes_output.png")