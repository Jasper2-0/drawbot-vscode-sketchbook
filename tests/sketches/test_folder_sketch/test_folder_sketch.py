# DrawBot Sketch
# Created: 2025-08-13 11:39:39

import drawBot as drawbot

# Set canvas size
drawbot.size(400, 400)

# Set background color
drawbot.fill(1)  # White background
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

# Your drawing code here
drawbot.fill(0)  # Black
drawbot.fontSize(24)
drawbot.text("Hello DrawBot!", (50, 200))

# Save the result
drawbot.saveImage("sketch_output.png")
