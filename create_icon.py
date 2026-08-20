"""
Create an ICO file from the KanoonVault logo for Windows installer.
This script converts frontend/logo.png to frontend/logo.ico

Requires: Pillow (already in requirements.txt)

Run: python create_icon.py
"""

from pathlib import Path
from PIL import Image
import sys


def create_icon(png_path: Path, ico_path: Path, sizes=None):
    """
    Convert a PNG image to Windows ICO format.
    
    Args:
        png_path: Path to input PNG file
        ico_path: Path to output ICO file  
        sizes: List of icon sizes (in pixels) to include
               Default: (16, 24, 32, 48, 64, 128, 256) - common Windows sizes
    """
    if sizes is None:
        sizes = (16, 24, 32, 48, 64, 128, 256)
    
    if not png_path.exists():
        print(f"[ERROR] PNG file not found: {png_path}")
        return False
    
    try:
        # Open the PNG image
        img = Image.open(str(png_path))
        print(f"[*] Loaded image: {png_path}")
        print(f"[*] Original size: {img.size}")
        
        # Convert to RGBA (required for ICO with transparency)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
            print(f"[*] Converted to RGBA mode")
        
        # Create icon images - Pillow's save method can create multi-resolution icons
        # We'll save with the most common icon sizes
        icon_images = []
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_images.append(resized)
            print(f"[*] Created {size}x{size} version")
        
        # Save as ICO (Pillow automatically handles multi-resolution)
        if icon_images:
            icon_images[0].save(
                str(ico_path),
                format="ICO",
                sizes=[(s, s) for s in sizes]
            )
            print(f"[OK] Icon saved: {ico_path}")
            return True
        else:
            print("[ERROR] Failed to create resized images")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to create icon: {e}")
        return False


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    
    # Try PNG first, then fallback to JPG
    png_path = script_dir / "frontend" / "logo.png"
    jpg_path = script_dir / "frontend" / "logo.jpg"
    ico_path = script_dir / "frontend" / "logo.ico"
    
    print("")
    print("=" * 60)
    print("  KanoonVault Icon Creator")
    print("=" * 60)
    print()
    
    # Determine which source file to use
    source_path = None
    if png_path.exists() and png_path.stat().st_size > 0:
        source_path = png_path
    elif jpg_path.exists():
        source_path = jpg_path
    else:
        print(f"[ERROR] Logo not found!")
        print()
        print("Make sure one of these exists:")
        print(f"  - {png_path}")
        print(f"  - {jpg_path}")
        return 1
    
    # Check if ICO already exists
    if ico_path.exists():
        print(f"[*] ICO file already exists: {ico_path}")
        user_response = input("Overwrite? (y/n): ").strip().lower()
        if user_response != "y":
            print("[*] Skipping icon creation")
            return 0
    
    # Create the icon
    print(f"[*] Creating icon from: {source_path}")
    print(f"[*] Output: {ico_path}")
    print()
    
    success = create_icon(source_path, ico_path)
    
    if success:
        print()
        print("=" * 60)
        print("  Success! Icon created.")
        print("=" * 60)
        print()
        print("The installer configuration (kanoonvault-installer.iss)")
        print("now has an icon for the installation wizard and shortcuts.")
        return 0
    else:
        print()
        print("[ERROR] Failed to create icon")
        return 1


if __name__ == "__main__":
    sys.exit(main())
