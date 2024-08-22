import sys
import pygame
from pygame_gl_code import PygameGLWindow
from imgui_rendering import ImguiUI
from application import Application
from list_viewer import ListViewer
from image_viewer import ImageViewer

TRACKED_KEYS = [
    pygame.K_LCTRL, pygame.K_s, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_SPACE
]

def main():
    window = PygameGLWindow(
        size=(1000, 800),
        caption="picsel - new file",
        frame_rate=144,
        background_color=(0, 0, 0),
        resizable=True,
        tracked_keys=TRACKED_KEYS
    )

    with window:
        ui = ImguiUI(window)
        app = Application(window, ui, [ListViewer(), ImageViewer()])
        if len(sys.argv) >= 2:
            app.open_file(sys.argv[1])
        app.main_loop()


if __name__ == '__main__':
    main()