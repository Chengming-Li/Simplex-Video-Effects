import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk
import os
from Stabilize import loadVideo, trackVideo
from Video import RunSegmentation, RenderOne
import time
from multiprocessing import freeze_support
import threading
import cv2
from PIL import Image, ImageTk

class Framework:
    def __init__(self, window):
        # starting window stuff
        window.config(bg="#323232")
        window.iconbitmap(os.getcwd()+os.sep+"icon.ico")
        screenSize = (window.winfo_screenwidth(), int(window.winfo_screenwidth()/16*9))
        if screenSize[1] > window.winfo_screenheight():
            screenSize = (int(window.winfo_screenheight()/9*16), window.winfo_screenheight())
        window.minsize(screenSize[0], screenSize[1])
        window.maxsize(screenSize[0], screenSize[1])
        window.title("Video Effects")
        window.state('zoomed')
        # frames
        menuFrame = tk.Frame(window, bg="#464646", )
        menuFrame.grid(row=0, column=0, rowspan=8, sticky="NS")
        tk.Frame(menuFrame, bg="#323232", width=2, bd=0).grid(row=0, column=1, ipady=window.winfo_screenheight()*.5, rowspan=800)
        contentFrame = tk.Frame(window, bg="#323232")
        contentFrame.grid(row=0, column=1, sticky="E")
        # side menu
        tk.Label(menuFrame, text="Effects", anchor="w", bg="#464646", fg="White", font=("Cambria 15 bold")).grid(row=11, column=0)
        stabilize = tk.Button(menuFrame, fg="White", activeforeground="White", text="Stabilize", padx=9, font=("Cambria 10"), anchor="w", command=(lambda : self.switchWindows(1)), width=int(window.winfo_screenheight()/54), bg="#464646", activebackground="#323232", borderwidth=0, relief=tk.SUNKEN)
        rembg = tk.Button(menuFrame, fg="White", activeforeground="White", text="Remove Background", font=("Cambria 10"), padx=9, anchor="w", command=(lambda : self.switchWindows(0)), width=int(window.winfo_screenheight()/54), bg="#464646", activebackground="#323232", borderwidth=0, relief=tk.SUNKEN)
        stabilize.grid(row=13, column=0,)
        rembg.grid(row=12, column=0)
        self.framelist = [(rembg, RemoveBackground(contentFrame)), (stabilize, Stabilize(contentFrame))]
        self.currentFrame = self.framelist[0]
        self.currentFrame[0].configure(bg = "#323232")
        [_[1].forget() for _ in self.framelist[1:]]

    def switchWindows(self, pos):
        if self.framelist[pos] is not self.currentFrame:
            self.currentFrame[0].configure(bg = "#464646")
            self.currentFrame[1].forget()
            self.framelist[pos][1].tkraise()
            self.currentFrame = self.framelist[pos]
            self.currentFrame[0].configure(bg = "#323232")
            self.framelist[pos][1].Clear()
            self.framelist[pos][1].pack()

class ContentFramework(tk.Frame):
    def __init__(self, contentFrame, scrollbar=True, allFrames=True):
        super().__init__(contentFrame, bg="#323232")
        self.allFrames = allFrames
        self.canvash = int(window.winfo_screenheight()*0.8)
        self.canvasw = int(window.winfo_screenwidth()*0.8)
        self.canvas = tk.Canvas(self, bg="#1A1A1A", height=self.canvash, width=self.canvasw, borderwidth=0, highlightbackground="#323232")
        self.canvas.grid(row=0, column=0, padx=int(window.winfo_screenheight()/9.95),)
        self.loadedFrame = self.canvas.create_image(0, 0, image = "", anchor = "nw")
        self.loadedFrames = {}
        self.contentFrameButtons = tk.Frame(self, bg="#323232",)
        self.contentFrameButtons.grid(row=1, column=0)
        if scrollbar:
            self.Slider = tk.Scale(self.contentFrameButtons, showvalue=0, from_=0, to=0, activebackground="#B4B4B4", sliderrelief=tk.FLAT, orient=tk.HORIZONTAL, length=self.canvasw, command=self.selectFrame, width=20, troughcolor="#424242", highlightthickness=0, borderwidth=0)
            self.Slider.grid(row=0, column=0, columnspan=200, pady=2)
        else:
            tk.Scale(self.contentFrameButtons, showvalue=0, from_=0, to=0, orient=tk.HORIZONTAL, length=self.canvasw, width=7, troughcolor="#323232", state=tk.DISABLED, highlightthickness=0, borderwidth=0, sliderlength=0).grid(row=0, column=0, columnspan=200, pady=2)
        self.OpVideo = tk.Button(self.contentFrameButtons, text="Select Video", font=("Cambria 12"), relief=tk.SUNKEN, activebackground="#949494", command=self.openVideo, bd=0)
        self.OpDirectory = tk.Button(self.contentFrameButtons, text="Select Output Location", font=("Cambria 12"), activebackground="#949494", command=self.openDirectory, relief=tk.SUNKEN, bd=0)
        self.OpVideo.grid(row=1, column=0, pady=window.winfo_screenheight()*.005)
        self.OpDirectory.grid(row=1, column=5, pady=window.winfo_screenheight()*.005)
        self.outputname = ["", False]
        self.currentFrame = 0
        self.vidName = ""
        self.frames = []
        self.vName = ""
        self.pack()

    def Clear(self):
        self.outputname = ["", False]
        self.currentFrame = 0
        self.vidName = ""
        self.vName = ""
        self.canvas.itemconfig(self.loadedFrame, image = "")
        self.loadedFrames = {}

    def openVideo(self, addition):
        """
        Saves all frames of video in frames, and frame resizer function to convertFrames
        fps will be updated to represent the fps of the video
        If outputname has not been selected, it will be set to the same directory the video was taken from
        Slider's "to" value will be adjusted to represent all the frames 
        Canvas will show the resized image, centered. User will be able to select boxes on the canvas
        """
        outputname, canvas = self.outputname, self.canvas
        filename = filedialog.askopenfilename(initialdir = os.sep + "downloads", title = "Select a Video", filetypes = (("Video files", "*.mp4*"),)).replace("/", os.sep)
        if not outputname[1]:
            outputname[0] = filename.replace(os.sep + filename.split(os.sep)[-1], "")
        if filename:
            st = time.time()
            self.vidName = filename.split(os.sep)[-1].split(".")
            self.vName = filename.split(os.sep)[-1]
            self.vidName = os.sep+self.vidName[0]+addition+self.vidName[1]
            self.frames, self.fps, res = loadVideo(filename, self.allFrames)
            self.cvf, self.cvf2, self.offset, self.ratio = self.convertFrames(res, [int(canvas.cget("height")), int(canvas.cget("width"))])
            self.loadedFrames[0] = self.cvf(self.frames[0])
            canvas.itemconfig(self.loadedFrame, image = self.loadedFrames[0])
            canvas.coords(self.loadedFrame, self.offset[0], self.offset[1])
            canvas.itemconfig(self.loadedFrame, state="normal")
            print(f"Prepared {len(self.frames)} frames in {time.time()-st} seconds.")
            return filename
    
    def openDirectory(self):
        """
        Selects a directory and sets it as outputname
        """
        on = filedialog.askdirectory(title = "Select Output Location").replace("/", os.sep)
        if on:
            self.outputname[:] = [on, True]
    
    def selectFrame(self, num):
        """
        Updates the canvas to display the frame at position num
        num: value representing the index of desired frame
        """
        self.currentFrame = int(num)
        if int(num) in self.loadedFrames:
            self.canvas.itemconfig(self.loadedFrame, image=self.loadedFrames[int(num)])
        else:
            self.loadedFrames[int(num)] = self.cvf(self.frames[int(num)])
            self.canvas.itemconfig(self.loadedFrame, image=self.loadedFrames[int(num)])

    def convertFrames(self, frameRes, newRes):
        """
        Converts frame from cv2 image to PIL image. Resizes if necessary
        frame: cv2 image
        newRes: new resolution
        """
        ratio = newRes[0]/frameRes[0]
        if frameRes[1]*ratio > newRes[1]:
            ratio = newRes[1]/frameRes[1]
            x = round(frameRes[0]*ratio)
            offset = [2, (newRes[0]-x)//2+2]
            newSize = [x, newRes[1]]
        else:
            x = round(frameRes[1]*ratio)
            offset = [(newRes[1]-x)//2+2, 2]
            newSize = [newRes[0], x]
        def helper1(frame):
            frame = cv2.resize(frame, (newSize[1], newSize[0]))
            return ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        def helper2(frame):
            frame = cv2.resize(frame, (newSize[1], newSize[0]))
            return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return helper1, helper2, offset, ratio

    def OpenSettings(self):
        top = tk.Toplevel(bg="#B1B1B1")
        top.grab_set()
        top.resizable(False, False)
        top.title("Advanced Settings")
        return top

class RemoveBackground(ContentFramework):
    def __init__(self, contentFrame):
        super().__init__(contentFrame, False, False)
        self.remBGButton = tk.Button(self.contentFrameButtons, text="Remove Background", activebackground="#949494", font=("Cambria 20"), command=self.removeBackground, padx=window.winfo_screenheight()*.008, relief=tk.SUNKEN, bd=0)
        self.remBGButton.grid(row=1, column=60, pady=window.winfo_screenheight()*.005)
        self.backgroundPath, self.alpha, self.postProcessing, self.fast = None, False, False, False
        self.Advanced = tk.Button(self.contentFrameButtons, text="Advanced Options", font=("Cambria 9"), relief=tk.SUNKEN, activebackground="#949494", command=self.OpenSettings, bd=0)
        self.Advanced.grid(row=1, column=199, pady=window.winfo_screenheight()*.005)

        self.mode = "Mixed"
        self.brightness = 1
        self.saturation = 1
        self.contrast = 1

    def openVideo(self):
        self.videoPath = super().openVideo("_output.")
        SegmentOne(self, self.alpha, self.postProcessing, self.brightness, self.saturation, self.contrast)

    def removeBackground(self):
        if not self.frames:
            tk.messagebox.showerror("Error", message='Please select a video')
        else:
            top = tk.Toplevel(bg="#B1B1B1")
            def copyP():
                top.clipboard_clear()
                top.clipboard_append(l2.cget("text").split("at:")[-1][1:])
            top.grab_set()
            top.resizable(False, False)
            top.title("Removing Video Background")
            top.geometry(f"+{int(window.winfo_screenwidth()/3)}+{int(window.winfo_screenheight()/3)}")

            l = tk.Label(top, font=("Cambria 15"), text=f"Removing the Background of {self.vName}", bg="#B1B1B1")
            l.pack(pady=2)
            l2 = tk.Label(top, font=("Cambria 12"), text="", bg="#B1B1B1")
            progress = ttk.Progressbar(top, orient = tk.HORIZONTAL, length = 600, mode = 'indeterminate')
            progress.pack(pady=10, padx=10)
            progress.start(25)
            CopyButton = tk.Button(top, text="Copy Path", font=("Cambria 10"), fg="White", command=copyP, relief=tk.SUNKEN, bd=0, background="#4D4D4D")
            threading.Thread(target=lambda : segment(self.videoPath, self.backgroundPath, self.alpha, self.outputname[0]+self.vidName, self.postProcessing, self.fast, [top, progress, l2, CopyButton], self.brightness, self.saturation, self.contrast)).start()
            top.mainloop()

    def assignVal(self, val, x):
        if val == "brightness":
            self.brightness = x
        elif val == "saturation":
            self.saturation = x
        elif val == "alpha":
            self.alpha = not self.alpha
        elif val == "mode":
            if x == "Mixed":
                self.mode = "Mixed"
                self.fast = False
                self.postProcessing = False
            elif x == "Accurate":
                self.mode = "Accurate"
                self.fast = False
                self.postProcessing = True
            else:
                self.mode = "Fast"
                self.fast = True
                self.postProcessing = False
        else:
            self.contrast = x
    
    def OpenSettings(self):
        top = super().OpenSettings()
        top.geometry(f"+{int(window.winfo_screenwidth()/3)}+{int(window.winfo_screenheight()/3)}")
        topSide = tk.Frame(top, bg="#B1B1B1", )
        topSide.pack()
        # Background, alpha, mode
        BackgroundButton = tk.Button(topSide, text="Select Background", font=("Cambria 17"), fg="White", command=self.selectBackground, relief=tk.SUNKEN, bd=0, background="#4D4D4D")
        BackgroundButton.grid(row=1, column=0, pady=8, padx=10)
        alphaBox = tk.Checkbutton(topSide, background="#4D4D4D", font=("Cambria 17"), text='Alpha', command=(lambda : self.assignVal("alpha", 0)), fg="White", selectcolor='gray')
        alphaBox.grid(row=2, column=0, pady=2, padx=10)
        dropDownFrame = tk.Frame(topSide, bg="#B1B1B1", )
        dropDownFrame.grid(row=3, column=0, pady=8, padx=10)
        tk.Label(dropDownFrame, font=("Cambria 17"), bg="#B1B1B1", text=f"Mode:").pack()
        options = [
            "Fast",
            "Mixed",
            "Accurate"
        ]
        drop = tk.OptionMenu(dropDownFrame, tk.StringVar(value=self.mode), *options, command=(lambda x: self.assignVal("mode", x)))
        drop.config(bg="#4D4D4D", fg="WHITE")
        drop.pack()

        # Brightness, saturation, contrast
        tk.Label(topSide, font=("Cambria 10"), bg="#B1B1B1", text=f"This adjustment will only be used to help with background removal\nIt will not be applied onto the video").grid(row=1, column = 1, pady=2, padx=8)
        Contrast = tk.Scale(topSide, label="Contrast", from_=0, to=2, resolution=0.1, bg="#B1B1B1", activebackground="#E7E7E7", sliderrelief=tk.FLAT, orient=tk.HORIZONTAL, length=int(window.winfo_screenheight()/2), command=(lambda x: self.assignVal("contrast", x)), width=15, troughcolor="#555555", highlightthickness=0, borderwidth=0)
        Contrast.set(self.contrast)
        Contrast.grid(row=2, column=1, pady=2, padx=8)

        RenderFrame = tk.Button(topSide, text="Render Frame", font=("Cambria 17"), fg="White", command=(lambda : SegmentOne(self, self.alpha, self.postProcessing, self.brightness, self.saturation, self.contrast, top)), relief=tk.SUNKEN, bd=0, background="#4D4D4D")
        RenderFrame.grid(row=3, column=1, padx=2, pady=8)

    def selectBackground(self):
        filename = filedialog.askopenfilename(initialdir = os.sep + "downloads", title = "Select a Background File", filetypes = (("Media Files", "*.mp4*"), ("Media Files", "*.png*"), ("Media Files", "*.jpg*"))).replace("/", os.sep)
        if filename:
            self.backgroundPath = filename

class Stabilize(ContentFramework):
    def __init__(self, contentFrame):
        super().__init__(contentFrame)
        self.pos = [0, 0, 0, 0, False]  # starting position x, starting position y, ending position x, ending position y, boolean to allow tracking or not
        self.rectangle = self.canvas.create_rectangle(0, 0, 0, 0, outline="", width=2)

        self.StabilizeButton = tk.Button(self.contentFrameButtons, text="Stabilize", activebackground="#949494", font=("Cambria 20"), command=self.Stabilize, padx=window.winfo_screenheight()*.05, relief=tk.SUNKEN, bd=0)
        self.StabilizeButton.grid(row=1, column=60, pady=window.winfo_screenheight()*.005)

        # lists of all widgets in stabilize class
        self.widgets = [self.contentFrameButtons, self.canvas, self.Slider, self.OpVideo, self.OpDirectory, self.StabilizeButton]

    def Clear(self):
        super().Clear()
        self.frames = []
        self.pos[:] = [0, 0, 0, 0, False]
        Slider = self.Slider
        Slider.config(to=0, sliderlength=15)
        Slider.set(0)

    def openVideo(self):
        super().openVideo("_stabilized.")
        self.canvas.bind('<Button-1>', self.startDrag)
        self.canvas.itemconfig(self.rectangle, outline="")
        self.pos[:] = [0, 0, 0, 0, False]
        Slider = self.Slider
        Slider.config(to=len(self.frames)-1, sliderlength=max(8, Slider.cget("length")//len(self.frames)))
        Slider.set(0)
    def clamp(self, num, min_value, max_value):
        """
        Quality of life function, confines num to be between min_value and max_value
        num: number to be clamped
        min_value: minimum value the num is allowed to be
        max_value: maximum value the num is allowed to be
        """
        return min(max(num, min_value), max_value)
    # stabilize
    def startDrag(self, event):
        """
        Called when user begins to create box on canvas. Sets pos[0] and pos[1] to the mouse position, and binds mouse movement to resize rectangle for visualization
        """
        offset, pos, canvas, rectangle = self.offset, self.pos, self.canvas, self.rectangle
        canvas.bind('<ButtonRelease-1>', lambda x: None)
        if event.x >= offset[0] and event.x <= self.canvasw-offset[0]+3 and event.y >= offset[1] and event.y <= self.canvasw-offset[1]+3:
            pos[4] = False
            pos[0], pos[1] = event.x, event.y
            canvas.coords(rectangle, event.x, event.y, event.x, event.y)
            canvas.bind('<Motion>', self.mouseUpdate)
            canvas.itemconfig(rectangle, outline='yellow')
            canvas.bind('<ButtonRelease-1>', self.endDrag)
    def mouseUpdate(self, event):
        """
        Called while user creates box on canvas. Resizes rectangle according to mouse movement for visualization
        """
        pos, offset = self.pos, self.offset
        self.canvas.coords(self.rectangle, pos[0], pos[1], self.clamp(event.x, offset[0], self.canvasw-offset[0]+3), self.clamp(event.y, offset[1], self.canvash-offset[1]+3))
    def endDrag(self, event):
        """
        Called when user ends box creation on canvas. Sets pos[2] and pos[3] to the mouse position, and unbinds mouse movement. If the area of the rectangle is too small, it will remove the rectangle. Otherwise it will set pos[4] to True, allowing for tracking
        """
        canvas, pos, offset = self.canvas, self.pos, self.offset
        canvas.bind('<Motion>', lambda x: None)
        pos[2], pos[3] = self.clamp(event.x, offset[0], self.canvasw-offset[0]+3), self.clamp(event.y, offset[1], self.canvash-offset[1]+3)
        area = abs(pos[0]-pos[2]) * abs(pos[1] - pos[3])
        if area > (self.canvash*self.canvasw//1300):
            canvas.coords(self.rectangle, pos[0], pos[1], pos[2], pos[3])
            pos[4] = True
        else:
            canvas.itemconfig(self.rectangle, outline="")

    def Stabilize(self):
        if not self.frames:
            tk.messagebox.showerror("Error", message='Please select a video to stabilize')
        elif not self.pos[4]:
            tk.messagebox.showerror("Error", message='Please select an area to stabilize')
        else:
            top = tk.Toplevel(bg="#B1B1B1")
            def copyP():
                top.clipboard_clear()
                top.clipboard_append(l2.cget("text").split("at:")[-1][1:])
            top.grab_set()
            top.resizable(False, False)
            top.title("Stabilizing Video")
            top.geometry(f"+{int(window.winfo_screenwidth()/3)}+{int(window.winfo_screenheight()/3)}")
            l = tk.Label(top, font=("Cambria 15"), text=f"Stabilizing {self.vName}", bg="#B1B1B1")
            l.pack(pady=2)
            l2 = tk.Label(top, font=("Cambria 12"), text="", bg="#B1B1B1")
            progress = ttk.Progressbar(top, orient = tk.HORIZONTAL, length = 600, mode = 'determinate')
            progress.pack(pady=10, padx=10)
            CopyButton = tk.Button(top, text="Copy Path", fg="White", font=("Cambria 10"), command=copyP, relief=tk.SUNKEN, bd=0, background="#4D4D4D")
            threading.Thread(target=lambda : tv([top, progress, l2, CopyButton], self.pos, self.offset, self.ratio, self.frames, self.outputname, self.fps, self.currentFrame, self.vidName)).start()
            top.mainloop()

def tv(lst, pos, offset, ratio, frames, outputname, fps, currentFrame, vidName):
    tb = [int((pos[x]-offset[x%2])*(1/ratio)) for x in range(4)]
    trackVideo(tb, frames, outputname[0], fps, currentFrame, vidName, boxed=False, widgets=lst)

def segment(videoPath, backgroundPath, alpha, outputPath, postProcessing, fast=False, widgets=[], brightness = 1, saturation = 1, contrast = 1):
    RunSegmentation(videoPath, backgroundPath, alpha, outputPath, postProcessing, widgets, fast, brightness, contrast, saturation)

def SegmentOne(self, alpha, postProcessing, brightness = 1, saturation = 1, contrast = 1, toplevel=None):
    if self.vidName:
        image = self.cvf2(self.frames[0])
        output = RenderOne(image, None, alpha, postProcessing, brightness, contrast, saturation)
        self.loadedFrames["Frame"] = ImageTk.PhotoImage(output)
        self.canvas.itemconfig(self.loadedFrame, image = self.loadedFrames["Frame"])
        if toplevel is not None:
            toplevel.destroy()

if __name__ == "__main__":  # here so the computer doesnt create multiple windows
    freeze_support()
    window = tk.Tk()
    a = Framework(window)
    window.mainloop()