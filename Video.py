import torch
from NewHighInterface import HiInterface
import time
from PIL import Image
import cv2
import numpy as np
import os

def changeFPS(path, newFps, dimensions, totalframes=float("inf")):
    """
    Takes video of path and returns the video with the new framerate 
    path: string representing the file path of the input video
    newFps: new fps of video
    dimensions: 2 element iterator representing the dimensions of the foreground video
    totalFrames: the total amount of frames of the foreground video
    """
    assert newFps > 0, "FPS cannot be less than or equal to 0"
    def resizeImages(imgShape, newSize):
        """
        Returns a function that takes in a cv2 image and returns a new cv2 image that fits within newSize
        imgShape: shape of the original image
        newSize: dimensions the new image needs to fit into
        """
        if imgShape == newSize:
            return lambda x: x
        elif newSize[0]/newSize[1] == imgShape[0]/imgShape[1]:
            return lambda x: cv2.resize(x, newSize)
        else:
            newImgShape = [newSize[0], round(imgShape[1]/imgShape[0]*newSize[0])]
            newImgShape = [round(imgShape[0]/imgShape[1]*newSize[1]), newSize[1]] if newImgShape[1] > newSize[0] else newImgShape
            x_offset, y_offset = round((newSize[0]-newImgShape[0])/2), round((newSize[1]-newImgShape[1])/2)
            def resizer(img):
                img = cv2.resize(img, newImgShape)
                p = np.zeros((newSize[1], newSize[0]), dtype = "uint8")
                p[y_offset:y_offset+img.shape[0], x_offset:x_offset+img.shape[1]] = img
                return p
            return resizer
    fps, _, frames = GetFrames(path, cv2Image=True)
    fps, newFps = round(fps), round(newFps)
    if _ == 0 and frames == 0:
        return None
    converter = resizeImages(_, dimensions)
    if fps == 0:
        return [cv2ToPIL(converter(frames[0])) for _ in range(totalframes)]
    print(f"The video originally had {len(frames)} frames in total with a frame rate of {fps}")
    fpsRatio = newFps/fps
    if fpsRatio == 1:
        return list(map(cv2ToPIL, map(converter, frames)))
    else:
        newFrames = []
        rat = fpsRatio  # stores ratio of frames
        i = 0
        while i < len(frames) and len(newFrames) < totalframes:  # for each image:
            ratWhole, ratDec = int(rat), rat%1
            img = frames[i]
            for _ in range(ratWhole):
                newFrames.append(img)  # creates a copy of image for each whole number
            if ratDec > 0:
                imgs, weights, i = [img], [ratDec], i+1
                rec = 1-ratDec
                for _ in range(int(rec/ratDec)):
                    imgs.append(frames[i])
                    weights.append(ratDec)
                    i += 1
                rmd = rec%ratDec
                if rmd != 0:
                    imgs.append(frames[i])
                    weights.append(rmd)
                    i += 1
                    frames[i] = frames[i] * (1-rmd)
                    rat = fpsRatio - rmd + 1
                repeat = lambda y: (y, y, y, 1)
                output = cv2.multiply(imgs.pop(0), repeat(weights.pop(0)))
                for _ in imgs:
                    output = cv2.add(output, cv2.multiply(imgs.pop(0), repeat(weights.pop(0))))
                newFrames.append(output)
            else:
                rat = fpsRatio
                i += 1
        print(f"Now it has a fps of {newFps}")
        return list(map(cv2ToPIL, map(converter, newFrames)))

def GetFrames(video, cv2Image=False):
    """
    Clears the list images and breaks the video into frames, all of which are stored in images as PIL image objects
    video: string representing the path of the video
    cv2Image: boolean on whether to return the images as cv2 images or not(default is PIL)
    """
    if video.split(".")[-1] == "mp4":
        size = False
        images = []
        cap = cv2.VideoCapture(video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        while True:
            success, img = cap.read()
            if not success:
                break
            if not size:
                size = img.shape
                size = (size[1], size[0])
            if not cv2Image:
                img = cv2ToPIL(img)
            images.append(img)
        print("Extracted all frames")
        return fps, size, images
    else:
        img = cv2.imread(video)
        if img is None:
            return 0, 0, 0
        size = img.shape
        size = (size[1], size[0])
        return 0, size, [img]
def cv2ToPIL(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    return img

interface = HiInterface(object_type="hairs-like",  # Can be "object" or "hairs-like".
                            batch_size_seg=5,
                            batch_size_matting=1,
                            device='cuda' if torch.cuda.is_available() else 'cpu',
                            seg_mask_size=320,
                            matting_mask_size=1024,
                            trimap_prob_threshold=231,
                            trimap_dilation=30,
                            trimap_erosion_iters=5,
                            fp16=False,
                            LoaderFunc1=None,
                            LoaderFunc2=None,
                            postProcessing=False)

def RemoveBg(images, bg = None, alpha = False, loadingFunc1=None, loadingFunc2=None, postProcessing=True, fast=False, brightness=255, contrast=255, saturation=255):
    """
    Removes the background on all images in list images
    images: list of PIL image objects
    bg: list of PIL images objects representing the background
    alpha: bool representing whether to save video of as alpha map or not
    loadingFunc1: function called each background removal call
    loadingFunc2: function called each postProcessing call
    postProcessing: boolean whether or not to use post processing(better results, slower runtime)
    fast: interpolates every other frame
    brightness, saturation, contrast: int numbers between 0-509, representing how the images should be adjusted before segmentation. 
    """
    st = time.time()
    interface.func1 = loadingFunc1
    interface.func2 = loadingFunc2
    interface.postProcessing = postProcessing
    output = interface(images, bg, alpha, fast, brightness, contrast, saturation)  # list of images
    print(f"The program processed {len(images)} images in {time.time()-st} seconds({(time.time()-st)/len(images)} seconds per image)")
    return output

def RenderOne(image, bg = None, alpha = False, postProcessing=True, brightness=255, contrast=255, saturation=255):
    interface.postProcessing = postProcessing
    return interface.SegmentOne(image, bg, alpha, brightness, saturation, contrast)

def MoveLoader(loaderBar=None, maxVal=0):
    """
    Returns two functions
    loaderBar: the loading bar widget
    maxVal: maximum value of loading bar
    """
    startingVal = 0
    def ChangeStarterVal(x):
        """
        Updates the startingVal in MoveLoader and loaderBar's value to x
        """
        nonlocal startingVal
        if startingVal == 0:
            loaderBar['mode'] = "determinate"
            loaderBar['maximum'] = maxVal
            loaderBar.stop()
        startingVal = x
        print(x)
        loaderBar['value'] = x
    def ChangeLoadBar(x):
        """
        Updates the loaderBar's value to x + startingVal
        For segmentation function
        """
        print(startingVal + x*7)
        loaderBar['value'] = startingVal + x*7
    return ChangeStarterVal, ChangeLoadBar

def combineIntoVideo(outputPath, videoList, fps, size):
    """
    Combines all frames of videoList into a video file that is saved at outputPath
    outputPath: string representing the path the new video is to be saved to
    videoList: list of frames
    """
    out = cv2.VideoWriter(outputPath, cv2.VideoWriter_fourcc(*'mp4v'), fps, size, True)
    i = 0
    while i < len(videoList):
        videoList[i] = np.array(videoList[i].convert('RGB'))[:, :, ::-1]
        out.write(videoList[i])
        i += 1
    print(f"Saved at {outputPath}")
    out.release()

def RunSegmentation(videoPath, backgroundPath, alpha, outputPath, postProcessing, widgets, fast=False, brightness=255, contrast=255, saturation=255):
    """
    Runs the code
    videoPath: path to the video
    backgroundPath: path to the background file
    alpha: boolean to return the video as an alpha map or not
    fast: boolean to skip every other frame when making segmentation
    outputPath: path to the output directory
    postProcessing: bool determining if they should apply post processing 
    widgets: list of tkinter widgets
        [0]: the toplevel widget
        [1]: the progress bar widget
        [2]: the text widget
        [3]: the copy button
    brightness, saturation, contrast: int numbers between 0-509, representing how the images should be adjusted before segmentation. 
    """
    fps, size, frames = GetFrames(videoPath)
    if backgroundPath:
        background = changeFPS(backgroundPath, fps, size, len(frames))
    else:
        background = None
    if fast:
        maxval = round(len(frames)/2)
    elif not postProcessing:
        maxval = len(frames)
    else:
        maxval = len(frames)*8
    func1, func2 = MoveLoader(widgets[1], maxval)
    videoFrames = RemoveBg(images=frames, bg=background, alpha=alpha, loadingFunc1 = func1, loadingFunc2=func2, postProcessing=postProcessing, fast=fast, brightness=brightness, contrast=contrast, saturation=saturation)
    combineIntoVideo(outputPath = outputPath, videoList = videoFrames, fps=fps, size=size)
    widgets[2].config(text = f"Saved at: {outputPath}")
    widgets[2].pack()
    widgets[3].pack(pady=5)