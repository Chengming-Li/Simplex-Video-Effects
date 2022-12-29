"""
Changes: created a new class that inherits from the Interface class, except now it runs the images through the composite function instead of the apply_mask function.
    It also now returns the masks as well
"""

from typing import List
from PIL import Image, ImageEnhance

from carvekit.api.interface import Interface
from carvekit.utils.mask_utils import composite

def skipEveryOther(videoList):
    """
    Halves the length of videoList by skipping every other image
    """
    return [videoList[i] for i in range(len(videoList)) if i%2==0]

def interpolate(videoList):
    """
    Doubles the length of videoList by interpolating the images
    """
    newList = []
    for i in range(len(videoList)):
        if i > 0:
            newList.append(Image.blend(videoList[i-1], videoList[i], 0.5))
        newList.append(videoList[i])
    return newList

class NewInterface(Interface):
    def convert(self, value):
        value = float(value)
        return value
    def __call__(self, images, bg=None, alpha = False, fast=False, brightness=0, saturation=0, contrast=0):
        """
        Removes the background from the specified images.

        Args:
            images: list of input images
            bg: list of background images
            fast: interpolates images
            brightness, saturation, contrast: int numbers between 0-2, representing how the images should be adjusted before segmentation. 
                Formula: 
                    any number over 1: (num-1)*254+1
        Returns:
            List of images without background as PIL.Image.Image instances
        """
        if bg is None:
            bg = [Image.new("RGBA", images[0].size, color=(0, 0, 0, 255)) for _ in images]
        if fast:
            imageList = skipEveryOther(images)
        else:
            imageList = images
        if float(saturation) != 1:
            y = lambda x: ImageEnhance.Color(x).enhance(self.convert(saturation))
            imageList = [y(i) for i in imageList]
        masks: List[Image.Image] = self.segmentation_pipeline(images=imageList, func=self.func1)

        if self.postProcessing and self.postprocessing_pipeline is not None:
            images: List[Image.Image] = self.postprocessing_pipeline(images=images, masks=masks, bg=bg, func=self.func2, alphaBool=alpha, fast=fast)
        else:
            if fast:
                masks = interpolate(masks)
            if alpha:
                return masks
            images = list(map(
                    lambda x: composite(foreground=images[x], background = bg[x], alpha=masks[x], device=self.device).convert("RGBA"),
                    range(len(masks)),))
        return images
    def SegmentOne(self, image, bg=None, alpha = False, brightness=0, saturation=0, contrast=0):
        if bg is None:
            bg = Image.new("RGBA", image.size, color=(0, 0, 0, 255))
        image1 = image
        if brightness != 1:
            image1 = ImageEnhance.Brightness(image).enhance(self.convert(brightness))
        if saturation != 1:
            image1 = ImageEnhance.Color(image).enhance(self.convert(saturation))
        if contrast != 1:
            image1 = ImageEnhance.Contrast(image).enhance(self.convert(contrast))
        mask = self.segmentation_pipeline(images=[image1], func=None)
        if self.postProcessing and self.postprocessing_pipeline is not None:
            return self.postprocessing_pipeline(images=[image], masks=mask, bg=[bg], func=None, alphaBool=alpha, fast=False)[0]
        elif alpha:
            return mask[0]
        else:
            return composite(foreground=image, background = bg, alpha = mask[0], device=self.device).convert("RGBA")