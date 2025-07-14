from PIL import Image, ImageFilter

def convert_to_4k(input_path, output_path):
    # Open the original image
    img = Image.open(input_path)
    
    # Set target resolution for 4K
    target_size = (3840, 2160)
    
    # Resize using high-quality resampling
    img_4k = img.resize(target_size, Image.LANCZOS)
    
    # Optionally improve quality by applying a slight sharpening filter
    img_4k = img_4k.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    # Save the processed image
    img_4k.save(output_path, quality=95)
    print(f"Image has been resized to 3840x2160 and saved as '{output_path}'.")

# Example usage
convert_to_4k("visa.jpg", "visa_4k.jpg")
