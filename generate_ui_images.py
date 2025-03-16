from PIL import Image, ImageDraw
import os

def create_empty_orders_icon(size=(200, 200)):
    # Create a new image with transparent background
    image = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Colors
    primary_color = '#02475b'
    
    # Draw a shopping bag
    margin = 20
    width = size[0] - 2 * margin
    height = size[1] - 2 * margin
    
    # Bag body points
    bag_top = margin + height * 0.2
    bag_points = [
        (margin + width * 0.2, bag_top),  # Top left
        (margin + width * 0.8, bag_top),  # Top right
        (margin + width * 0.9, margin + height * 0.9),  # Bottom right
        (margin + width * 0.1, margin + height * 0.9),  # Bottom left
    ]
    
    # Draw bag
    draw.polygon(bag_points, outline=primary_color, width=4)
    
    # Draw handles
    handle_height = height * 0.15
    left_handle = [
        (margin + width * 0.3, bag_top),
        (margin + width * 0.35, margin + height * 0.1),
        (margin + width * 0.4, bag_top),
    ]
    right_handle = [
        (margin + width * 0.6, bag_top),
        (margin + width * 0.65, margin + height * 0.1),
        (margin + width * 0.7, bag_top),
    ]
    draw.line(left_handle, fill=primary_color, width=4)
    draw.line(right_handle, fill=primary_color, width=4)
    
    return image

def main():
    # Create directory if it doesn't exist
    output_dir = 'static/images/ui'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate empty orders icon
    image = create_empty_orders_icon()
    image.save(f"{output_dir}/empty-orders.png", format='PNG')
    print("Generated empty-orders.png")

if __name__ == "__main__":
    main() 