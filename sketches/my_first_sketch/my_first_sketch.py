# Minimal Sketch Template
# A clean starting point for your creative ideas

import drawBot as drawbot

# Set canvas size
drawbot.size(400, 400)

# Set background color
drawbot.fill(1)  # White
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

drawbot.fill(1, 0, 0)
drawbot.rect(10, 10, 200, 200)
# Your code goes here...
# For example:
drawbot.fill(0)  # Black
drawbot.fontSize(20)
drawbot.text("Start creating third things", (50, 200))

# Save the result
drawbot.saveImage("output.png")
