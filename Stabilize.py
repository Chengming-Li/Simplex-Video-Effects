import cv2
import numpy as np
import time

def trackVideo(trackbox, vidFrames=None, outputPath="", fps=60, startingFrame=0, vidName="", boxed=False, widgets=None):
    """
    Stabilizes video
    trackbox: 4 element array that has the points of the bounding box 
    vidFrames: array of all the frames of the video
    outputPath: the directory the stabilized video is to be saved in
    fps: fps of video
    startingFrame: index of frame to start the tracking
    vidName: string representing the name of the new video
    boxed: boolean to show bounding box
    widgets: list of tkinter widgets
        [0]: the toplevel widget
        [1]: the progress bar widget
        [2]: the text widget
        [3]: the copy button
    """
    st = time.time()
    widgets[1]['maximum'] = 2*len(vidFrames)-startingFrame
    offsets = [(0, 0) for _ in range(startingFrame+1)]
    tracker = cv2.TrackerCSRT_create()
    started = False
    trackbox = [min(trackbox[0], trackbox[2]), min(trackbox[1], trackbox[3]), max(trackbox[0], trackbox[2]), max(trackbox[1], trackbox[3])]
    trackbox = [trackbox[0], trackbox[1], trackbox[2]-trackbox[0], trackbox[3]-trackbox[1]]
    print(trackbox)
    size = vidFrames[0].shape
    size = (size[1], size[0])
    outputPath = outputPath + vidName
    out = cv2.VideoWriter(outputPath, cv2.VideoWriter_fourcc(*'mp4v'), fps, size, True)
    x = 1
    print(x)
    for i in range(startingFrame, len(vidFrames)):
        frame = vidFrames[i]
        if started is False:
            tracker.init(frame, tuple(trackbox))
            started = findMiddle(array=trackbox)
        else:
            (success, box) = tracker.update(frame)
            if success:
                (x, y, w, h) = [int(v) for v in box]
                if boxed:
                    vidFrames[i] = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                offsets.append(findOffset(started, findMiddle(x, y, w, h)))
            else:
                assert False, "Fail"
        x = i-startingFrame
        widgets[1]['value'] = x
    maxOffsetX, minOffsetX, maxOffsetY, minOffsetY = max(offsets, key=lambda x: x[0])[0], min(offsets, key=lambda x: x[0])[0], max(offsets, key=lambda x: x[1])[1], min(offsets, key=lambda x: x[1])[1]
    x += 1
    for i in range(len(offsets)):
        p = np.zeros((size[1]+abs(maxOffsetY)+abs(minOffsetY), size[0]+abs(maxOffsetX)+abs(minOffsetX), 3), dtype = "uint8")
        of = offsets[i]
        frame = vidFrames[i]
        try:
            p[abs(minOffsetY)+of[1]:abs(minOffsetY)+of[1]+frame.shape[0], abs(minOffsetX)+of[0]:abs(minOffsetX)+of[0]+frame.shape[1]] = frame
            p = p[abs(minOffsetY):abs(minOffsetY)+frame.shape[0], abs(minOffsetX):abs(minOffsetX)+frame.shape[1]]
            out.write(p)
            x += 1
            widgets[1]['value'] = x
        except Exception as e:
            print(frame.shape, "\n", abs(minOffsetY)+of[1], abs(minOffsetY)+of[1]+frame.shape[0], "\n", abs(minOffsetX)+of[0], abs(minOffsetX)+of[0]+frame.shape[1], "\n", of)
            print(e)
            break
    out.release()
    print(f"Saved at {outputPath} with frame rate of {fps} in {time.time()-st}")
    print(x, 2*len(vidFrames)-startingFrame)
    widgets[2].config(text = f"Saved at: {outputPath}")
    widgets[2].pack()
    widgets[3].pack(pady=5)
def findMiddle(a=0, b=0, c=0, d=0, array=0):
    if array:
        return (array[0]+array[2]//2, array[1]+array[3]//2)
    return (a + c//2, b + d//2)
def findOffset(original, new):
    return (original[0]-new[0], original[1]-new[1])
def loadVideo(vidPath, allframes=True):
    """
    Returns list with all the frames of the video and the fps of the video
    vidPath: path to the video
    allframes: if false, only load the first frame
    """
    video = cv2.VideoCapture(vidPath)
    frames = []
    success, frame = video.read()
    res = frame.shape[:2]
    if not allframes:
        return [frame], video.get(cv2.CAP_PROP_FPS), res
    while True:
        if not success:
            return frames, video.get(cv2.CAP_PROP_FPS), res
        frames += [frame]
        success, frame = video.read()