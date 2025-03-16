from PIL import Image, ImageDraw, ImageFont
import os

def create_doctor_image(number, size=(400, 400)):
    # Create a new image with a white background
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw a colored circle for the avatar background
    circle_radius = min(size) // 3
    circle_center = (size[0] // 2, size[1] // 2)
    circle_bbox = (
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    )
    draw.ellipse(circle_bbox, fill='#007bff')
    
    # Add text
    text = f"Doctor {number}"
    # Use Arial font if available, otherwise use default
    try:
        font = ImageFont.truetype("arial.ttf", size=40)
    except:
        font = ImageFont.load_default()
    
    # Get text size and center it
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_position = (
        (size[0] - text_width) // 2,
        circle_bbox[3] + 20
    )
    
    # Draw text
    draw.text(text_position, text, fill='black', font=font)
    
    return image

def main():
    # Create output directory if it doesn't exist
    output_dir = os.path.join('static', 'images', 'doctors')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate 6 doctor images
    for i in range(1, 7):
        image = create_doctor_image(i)
        image.save(os.path.join(output_dir, f'doctor{i}.png'))

if __name__ == '__main__':
    main() 