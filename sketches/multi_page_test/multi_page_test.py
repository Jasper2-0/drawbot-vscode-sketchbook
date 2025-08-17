"""
Multi-page DrawBot sketch to test preview server handling of multi-page documents.
Creates a 4-page PDF with different content on each page.
"""

import drawBot as drawbot

# Set up the document
drawbot.size(400, 600)

# Page 1 - Title page
drawbot.fill(0.2, 0.4, 0.8)
drawbot.rect(0, 0, 400, 600)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica-Bold", 48)
drawbot.text("Multi-Page", (50, 400))
drawbot.text("Document", (50, 340))

drawbot.font("Helvetica", 24)
drawbot.text("Testing DrawBot's", (50, 280))
drawbot.text("multi-page functionality", (50, 250))

drawbot.font("Helvetica-Light", 16)
drawbot.text("Page 1 of 4", (50, 50))

# Page 2 - Geometric shapes
drawbot.newPage()
drawbot.fill(0.9, 0.9, 0.9)
drawbot.rect(0, 0, 400, 600)

drawbot.fill(0.8, 0.2, 0.2)
drawbot.oval(50, 450, 100, 100)

drawbot.fill(0.2, 0.8, 0.2)
drawbot.rect(250, 450, 100, 100)

drawbot.fill(0.8, 0.8, 0.2)
drawbot.polygon((200, 350), (150, 250), (250, 250))

drawbot.fill(0.2, 0.2, 0.8)
drawbot.oval(100, 150, 200, 100)

drawbot.fill(0, 0, 0)
drawbot.font("Helvetica-Bold", 32)
drawbot.text("Shapes & Colors", (50, 350))
drawbot.font("Helvetica", 16)
drawbot.text("Page 2 of 4", (50, 50))

# Page 3 - Typography showcase
drawbot.newPage()
drawbot.fill(0.1, 0.1, 0.1)
drawbot.rect(0, 0, 400, 600)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica-Bold", 36)
drawbot.text("Typography", (50, 500))

sizes = [32, 28, 24, 20, 16, 14, 12, 10]
y_pos = 450

for i, size in enumerate(sizes):
    drawbot.font("Helvetica", size)
    drawbot.text(f"Text size {size}pt", (50, y_pos - i * 40))

drawbot.fill(0.7, 0.7, 0.7)
drawbot.font("Helvetica-Light", 16)
drawbot.text("Page 3 of 4", (50, 50))

# Page 4 - Final page with gradients
drawbot.newPage()

# Create a simple gradient effect using overlapping rectangles
for i in range(60):
    alpha = 1 - (i / 60)
    drawbot.fill(0.8, 0.3, 0.6, alpha * 0.1)
    drawbot.rect(0, i * 10, 400, 10)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica-Bold", 42)
drawbot.text("The End", (120, 300))

drawbot.font("Helvetica", 18)
drawbot.text("Multi-page document complete!", (80, 250))

drawbot.fill(0.2, 0.2, 0.2)
drawbot.font("Helvetica", 16)
drawbot.text("Page 4 of 4", (50, 50))

# Save the multi-page document as PDF
drawbot.saveImage("output.pdf")

print("Multi-page PDF created successfully!")