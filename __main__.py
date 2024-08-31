import sys
import pygame
import os.path
from pygame_gl_code import PygameGLWindow
from imgui_rendering import ImguiUI
from application import Application
from list_viewer import ListViewer
from image_viewer import ImageViewer
from image_plotter import ImagePlotter
from hilbert_plotter import HilbertPlotter

TRACKED_KEYS = [
    pygame.K_LCTRL, pygame.K_s, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_SPACE
]

def main():
    window = PygameGLWindow(
        size=(1900, 900),
        caption="picsel - new file",
        frame_rate=144,
        background_color=(0, 0, 0),
        resizable=True,
        open_maximized=True,
        tracked_keys=TRACKED_KEYS, check_for_close=False
    )

    with window:
        ui = ImguiUI(window, ini_file=os.path.join(os.path.dirname(__file__), "imgui.ini"))
        app = Application(window, ui, [ListViewer(), ImageViewer(), ImagePlotter([HilbertPlotter()])])
        if len(sys.argv) >= 2:
            app.open_file(sys.argv[1])
        app.main_loop()


if __name__ == '__main__':
    main()
