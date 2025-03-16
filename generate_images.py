from PIL import Image, ImageDraw, ImageFont
import os

def create_medicine_image(name, description, size=(300, 300)):
    # Create a new image with white background
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    
    # Add a light blue gradient background
    for y in range(size[1]):
        color = (240, 248, 255, 255)  # Light blue tint
        draw.line([(0, y), (size[0], y)], fill=color)
    
    # Draw a professional border
    border_width = 3
    draw.rectangle([10, 10, size[0]-11, size[1]-11], outline='#02475b', width=border_width)
    
    try:
        # Try to load Arial font, fallback to default if not available
        title_font = ImageFont.truetype("arial.ttf", 22)
        desc_font = ImageFont.truetype("arial.ttf", 16)
    except:
        title_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()
    
    # Draw medicine name with background
    text_bbox = draw.textbbox((0, 0), name, font=title_font)
    text_width = text_bbox[2] - text_bbox[0]
    x = (size[0] - text_width) // 2
    # Draw text background
    padding = 10
    draw.rectangle([x - padding, 40, x + text_width + padding, 80], 
                  fill='#02475b')
    draw.text((x, 50), name, fill='white', font=title_font)
    
    # Draw description
    lines = description.split()
    desc_lines = []
    current_line = []
    for word in lines:
        current_line.append(word)
        test_line = ' '.join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=desc_font)
        if bbox[2] - bbox[0] > size[0] - 40:
            if len(current_line) > 1:
                current_line.pop()
                desc_lines.append(' '.join(current_line))
                current_line = [word]
            else:
                desc_lines.append(test_line)
                current_line = []
    if current_line:
        desc_lines.append(' '.join(current_line))
    
    y = 100
    for line in desc_lines:
        bbox = draw.textbbox((0, 0), line, font=desc_font)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill='#444444', font=desc_font)
        y += 25
    
    # Draw medical cross symbol
    cross_color = '#02475b'
    cross_size = 60
    center_x = size[0] // 2
    center_y = 200
    
    # Vertical line of the cross
    draw.rectangle([center_x - 10, center_y - cross_size//2,
                   center_x + 10, center_y + cross_size//2],
                   fill=cross_color)
    
    # Horizontal line of the cross
    draw.rectangle([center_x - cross_size//2, center_y - 10,
                   center_x + cross_size//2, center_y + 10],
                   fill=cross_color)
    
    return image

def main():
    # Medicine data from database
    medicines = [
        ('Paracetamol 500mg', 'Pain reliever and fever reducer'),
        ('Vitamin D3 1000IU', 'Vitamin D3 supplement'),
        ('Metformin 500mg', 'Type 2 diabetes medication'),
        ('Omeprazole 20mg', 'Acid reflux medication'),
        ('Amoxicillin 500mg', 'Antibiotic'),
        ('Cetirizine 10mg', 'Antihistamine for allergies'),
        ('Aspirin 81mg', 'Blood thinner'),
        ('Ibuprofen 400mg', 'Pain and inflammation reliever')
    ]
    
    # Create directory if it doesn't exist
    output_dir = 'static/images/medicines'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate medicine images
    for i, (name, desc) in enumerate(medicines, 1):
        image = create_medicine_image(name, desc)
        image.save(f"{output_dir}/medicine{i}.jpg", quality=95)
        print(f"Generated medicine{i}.jpg")

if __name__ == "__main__":
    main() 