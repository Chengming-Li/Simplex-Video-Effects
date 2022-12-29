"""
Changes: created a new class NewMattingMethod that inherits from the MattingMethod class. 
    The new class' call method now also takes in a list of backgorund images and runs the images through composite rather than apply_mask
"""
from carvekit.pipelines.postprocessing import MattingMethod
from typing import Union, List
from PIL import Image
from pathlib import Path
from carvekit.utils.mask_utils import composite
from carvekit.utils.pool_utils import thread_pool_processing
from carvekit.utils.image_utils import load_image, convert_image
import numpy as np

__all__ = ["MattingMethod"]

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

class NewMattingMethod(MattingMethod):
    def __call__(self, images, masks, bg, func, alphaBool=False, fast=False):
        """
        Passes data through composite function

        Args:
            images: list of images
            masks: list of masks
            bg: list of background images
            func: function for updating loading bar

        Returns:
            list of images
        """
        if len(images) != len(masks):
            raise ValueError("Images and Masks lists should have same length!")
        images = thread_pool_processing(convert_image, images)
        masks = thread_pool_processing(lambda x: convert_image(x, mode="L"), masks)
        trimaps = thread_pool_processing(lambda x: self.trimap_generator(original_image=images[x], mask=masks[x]), range(len(images)),)
        alpha = self.matting_module(images=images, trimaps=trimaps, func=func)
        if fast:
            alpha = interpolate(alpha)
        if alphaBool:
            print("ALpha")
            return alpha
        return list(
            map(
                lambda x: composite(foreground=images[x], background = bg[x], alpha=alpha[x], device=self.device).convert("RGBA"),
                range(len(images)),
            )
        )
