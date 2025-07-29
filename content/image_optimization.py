"""
Image optimization utilities for content management system.

Provides automatic image optimization, resizing, and format conversion
to improve performance and SEO.
"""

import os
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from typing import Tuple, Optional
import io


class ImageOptimizer:
    """
    Handle image optimization, resizing, and format conversion.
    """
    
    # Recommended sizes for different use cases
    SIZES = {
        'thumbnail': (300, 200),
        'medium': (600, 400),
        'large': (1200, 800),
        'hero': (1920, 1080),
        'og_image': (1200, 630),  # Open Graph recommended size
        'twitter_card': (1200, 600),  # Twitter Card recommended size
    }
    
    # Quality settings for different formats
    QUALITY_SETTINGS = {
        'JPEG': 85,
        'PNG': 95,
        'WEBP': 80,
    }
    
    def __init__(self):
        """Initialize the image optimizer."""
        self.max_file_size = getattr(settings, 'MAX_IMAGE_SIZE', 5 * 1024 * 1024)  # 5MB
    
    def optimize_image(self, image_file, target_size: str = 'large', 
                      format: str = 'JPEG', maintain_aspect_ratio: bool = True) -> ContentFile:
        """
        Optimize an image file for web use.
        
        Args:
            image_file: Django file object or PIL Image
            target_size: Size key from SIZES dict or tuple (width, height)
            format: Target format (JPEG, PNG, WEBP)
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            ContentFile with optimized image
        """
        # Open image
        if hasattr(image_file, 'read'):
            # Django file object
            image = Image.open(image_file)
        else:
            # PIL Image object
            image = image_file
        
        # Convert to RGB if necessary (for JPEG)
        if format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Get target dimensions
        if isinstance(target_size, str):
            target_width, target_height = self.SIZES.get(target_size, self.SIZES['large'])
        else:
            target_width, target_height = target_size
        
        # Resize image
        image = self._resize_image(image, target_width, target_height, maintain_aspect_ratio)
        
        # Apply additional optimizations
        image = self._apply_optimizations(image)
        
        # Save to bytes
        output = io.BytesIO()
        quality = self.QUALITY_SETTINGS.get(format, 85)
        
        save_kwargs = {'format': format, 'optimize': True}
        if format == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['progressive'] = True
        elif format == 'PNG':
            save_kwargs['optimize'] = True
        elif format == 'WEBP':
            save_kwargs['quality'] = quality
            save_kwargs['method'] = 6  # Best compression
        
        image.save(output, **save_kwargs)
        output.seek(0)
        
        # Create content file
        filename = f"optimized_image.{format.lower()}"
        return ContentFile(output.getvalue(), name=filename)
    
    def create_multiple_sizes(self, image_file, base_name: str) -> dict:
        """
        Create multiple optimized versions of an image.
        
        Args:
            image_file: Original image file
            base_name: Base name for generated files
            
        Returns:
            Dictionary with size names as keys and file paths as values
        """
        results = {}
        original_image = Image.open(image_file)
        
        for size_name, dimensions in self.SIZES.items():
            try:
                # Create optimized version
                optimized = self.optimize_image(
                    original_image.copy(),
                    target_size=dimensions,
                    format='JPEG'
                )
                
                # Generate filename
                filename = f"{base_name}_{size_name}.jpg"
                
                # Save file
                file_path = default_storage.save(filename, optimized)
                results[size_name] = file_path
                
            except Exception as e:
                # Log error but continue with other sizes
                print(f"Error creating {size_name} version: {e}")
                continue
        
        return results
    
    def _resize_image(self, image: Image.Image, target_width: int, 
                     target_height: int, maintain_aspect_ratio: bool = True) -> Image.Image:
        """
        Resize image to target dimensions.
        
        Args:
            image: PIL Image object
            target_width: Target width in pixels
            target_height: Target height in pixels
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            Resized PIL Image
        """
        current_width, current_height = image.size
        
        if maintain_aspect_ratio:
            # Calculate aspect ratios
            current_ratio = current_width / current_height
            target_ratio = target_width / target_height
            
            if current_ratio > target_ratio:
                # Image is wider than target ratio
                new_width = target_width
                new_height = int(target_width / current_ratio)
            else:
                # Image is taller than target ratio
                new_height = target_height
                new_width = int(target_height * current_ratio)
            
            # Resize maintaining aspect ratio
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # If we need exact dimensions, crop to center
            if new_width != target_width or new_height != target_height:
                image = ImageOps.fit(image, (target_width, target_height), 
                                   Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        else:
            # Resize without maintaining aspect ratio
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _apply_optimizations(self, image: Image.Image) -> Image.Image:
        """
        Apply additional image optimizations.
        
        Args:
            image: PIL Image object
            
        Returns:
            Optimized PIL Image
        """
        # Auto-orient based on EXIF data
        image = ImageOps.exif_transpose(image)
        
        # Apply sharpening filter for better quality after resize
        try:
            from PIL import ImageFilter
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=3))
        except ImportError:
            # Skip if PIL doesn't have filter support
            pass
        
        return image
    
    def generate_srcset(self, base_url: str, image_versions: dict) -> str:
        """
        Generate srcset attribute for responsive images.
        
        Args:
            base_url: Base URL for images
            image_versions: Dictionary of size -> filename
            
        Returns:
            srcset string for HTML img tag
        """
        srcset_parts = []
        
        size_widths = {
            'thumbnail': 300,
            'medium': 600,
            'large': 1200,
            'hero': 1920,
        }
        
        for size_name, filename in image_versions.items():
            if size_name in size_widths:
                width = size_widths[size_name]
                url = f"{base_url}/{filename}"
                srcset_parts.append(f"{url} {width}w")
        
        return ", ".join(srcset_parts)
    
    def is_valid_image(self, file) -> bool:
        """
        Check if uploaded file is a valid image.
        
        Args:
            file: Uploaded file object
            
        Returns:
            True if valid image, False otherwise
        """
        try:
            image = Image.open(file)
            image.verify()  # Verify it's a valid image
            return True
        except Exception:
            return False
    
    def get_image_info(self, image_file) -> dict:
        """
        Get information about an image file.
        
        Args:
            image_file: Image file object
            
        Returns:
            Dictionary with image information
        """
        try:
            image = Image.open(image_file)
            
            return {
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
                'size_bytes': image_file.size if hasattr(image_file, 'size') else 0,
                'aspect_ratio': round(image.width / image.height, 2),
            }
        except Exception as e:
            return {'error': str(e)}


class SEOImageProcessor:
    """
    Handle SEO-specific image processing and optimization.
    """
    
    def __init__(self):
        """Initialize the SEO image processor."""
        self.optimizer = ImageOptimizer()
    
    def process_article_image(self, image_file, article_slug: str) -> dict:
        """
        Process an article's featured image for SEO optimization.
        
        Args:
            image_file: Original image file
            article_slug: Article slug for file naming
            
        Returns:
            Dictionary with processed image information
        """
        base_name = f"articles/{article_slug}/featured"
        
        # Create multiple sizes
        image_versions = self.optimizer.create_multiple_sizes(image_file, base_name)
        
        # Create specific SEO versions
        seo_versions = {}
        
        # Open Graph image (1200x630)
        og_image = self.optimizer.optimize_image(
            Image.open(image_file),
            target_size=(1200, 630),
            format='JPEG'
        )
        og_path = default_storage.save(f"{base_name}_og.jpg", og_image)
        seo_versions['og_image'] = og_path
        
        # Twitter Card image (1200x600)
        twitter_image = self.optimizer.optimize_image(
            Image.open(image_file),
            target_size=(1200, 600),
            format='JPEG'
        )
        twitter_path = default_storage.save(f"{base_name}_twitter.jpg", twitter_image)
        seo_versions['twitter_image'] = twitter_path
        
        # Generate WebP versions for modern browsers
        webp_versions = {}
        for size_name, jpeg_path in image_versions.items():
            try:
                webp_image = self.optimizer.optimize_image(
                    Image.open(default_storage.open(jpeg_path)),
                    target_size=size_name,
                    format='WEBP'
                )
                webp_path = default_storage.save(f"{base_name}_{size_name}.webp", webp_image)
                webp_versions[size_name] = webp_path
            except Exception as e:
                print(f"Error creating WebP version for {size_name}: {e}")
        
        return {
            'jpeg_versions': image_versions,
            'webp_versions': webp_versions,
            'seo_versions': seo_versions,
            'base_name': base_name,
        }
    
    def generate_picture_element(self, image_data: dict, alt_text: str, 
                               css_classes: str = "") -> str:
        """
        Generate HTML picture element with WebP support and responsive sizes.
        
        Args:
            image_data: Image data from process_article_image
            alt_text: Alt text for accessibility
            css_classes: CSS classes to apply
            
        Returns:
            HTML picture element string
        """
        webp_versions = image_data.get('webp_versions', {})
        jpeg_versions = image_data.get('jpeg_versions', {})
        
        # Build WebP srcset
        webp_srcset = self.optimizer.generate_srcset(settings.MEDIA_URL, webp_versions)
        
        # Build JPEG srcset
        jpeg_srcset = self.optimizer.generate_srcset(settings.MEDIA_URL, jpeg_versions)
        
        # Get fallback image (largest available)
        fallback_image = jpeg_versions.get('large', jpeg_versions.get('medium', ''))
        
        html = f"""<picture{' class="' + css_classes + '"' if css_classes else ''}>
    <source srcset="{webp_srcset}" type="image/webp">
    <source srcset="{jpeg_srcset}" type="image/jpeg">
    <img src="{settings.MEDIA_URL}{fallback_image}" 
         alt="{alt_text}"
         loading="lazy"
         sizes="(max-width: 768px) 100vw, (max-width: 1200px) 80vw, 1200px">
</picture>"""
        
        return html