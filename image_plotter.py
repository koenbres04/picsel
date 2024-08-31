from __future__ import annotations
import imgui
import numpy as np
from application import Application, Source, Viewer
from pygame_gl_code import PygameGLWindow
from image_viewer import ImageViewer
import abc
from PIL import Image
from dataclasses import dataclass


@dataclass
class CircleData:
    center: np.ndarray
    radius: float
    color: np.ndarray

    @classmethod
    def lerp(cls, a: CircleData, b: CircleData, t: float):
        return CircleData(a.center*(1-t)+b.center*t,
                          a.radius*(1-t)+b.radius*t,
                          a.color*(1-t)+b.color*t)


class PositionGenerator(abc.ABC):
    def reset(self, app: Application):
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def process(self, app: Application, source: Source, index: int, pil_image: Image.Image):
        pass

    @abc.abstractmethod
    def get_circle_data(self, source: Source, index: int) -> CircleData:
        pass

    def draw_ui(self) -> None:
        pass


class RandomGenerator(PositionGenerator):
    def __init__(self):
        self.positions: dict[Source, list[np.ndarray]] | None = None

    def reset(self, app: Application):
        self.positions = {source: [] for source in app.selection.sources}

    @property
    def name(self) -> str:
        return "Random positions"

    def process(self, app: Application, source: Source, index: int, pil_image: Image.Image):
        self.positions[source].append(np.random.random(2))

    def get_circle_data(self, source: Source, index: int) -> CircleData:
        return CircleData(self.positions[source][index], 5, np.array([1., 0., 0.]))


class Animation(abc.ABC):
    @abc.abstractmethod
    def get_last_generator(self) -> PositionGenerator:
        pass

    def step(self, app: Application):
        pass

    @abc.abstractmethod
    def get_circle_data(self, source: Source, index: int) -> CircleData:
        pass

    @property
    @abc.abstractmethod
    def needs_replacement(self) -> bool:
        pass

    def get_replacement(self) -> Animation:
        pass


def get_smooth_t(t: float):
    return max(0., min(1., 3*t**2-2*t**3))


class ContstantAnimation(Animation):
    def __init__(self, generator: PositionGenerator):
        self.generator = generator

    def get_last_generator(self) -> PositionGenerator:
        return self.generator

    def get_circle_data(self, source: Source, index: int) -> CircleData:
        return self.generator.get_circle_data(source, index)

    @property
    def needs_replacement(self) -> bool:
        return False


class LerpAnimation(Animation):
    def __init__(self, start: PositionGenerator, end: PositionGenerator, length: float):
        self.start = start
        self.end = end
        self.t = 0
        self.length = length

    def get_last_generator(self) -> PositionGenerator:
        return self.end

    def get_circle_data(self, source: Source, index: int) -> CircleData:
        return CircleData.lerp(self.start.get_circle_data(source, index),
                               self.end.get_circle_data(source, index),
                               get_smooth_t(self.t))

    def step(self, app: Application):
        self.t = min(self.t + app.window.delta_time, self.length)

    @property
    def needs_replacement(self) -> bool:
        return self.t == 1.

    def get_replacement(self) -> Animation:
        return ContstantAnimation(self.end)


ZOOM_FACTOR = 1.1
SELECTION_COLOR = (234/255, 237/255, 24/255)
SELECTION_THICKNESS = 2
ARROW_COLOR = (0/255, 158/255, 176/255)
ARROW_HEIGHT = 10
ARROW_WIDTH = 10


class Camera:
    def __init__(self, position: np.ndarray, scale: float):
        self.position = position
        self.scale = scale

    def handle_inputs(self, app: Application):
        if app.ui.want_capture_mouse or app.ui.want_capture_keyboard:
            return
        if app.window.is_mouse_button_down(0):
            self.position += -app.window.delta_cur*self.scale
        self.position += (app.window.cur_pos-app.window.center)*self.scale
        self.scale /= pow(ZOOM_FACTOR, app.window.get_scroll_wheel_y())
        self.position -= (app.window.cur_pos-app.window.center)*self.scale


    def world_circle_to_screen(self, window: PygameGLWindow, circle: CircleData) -> CircleData:
        return CircleData((circle.center-self.position)/self.scale+window.center, circle.radius/self.scale, circle.color)



class ImagePlotter(Viewer):
    def __init__(self, generators: list[PositionGenerator]):
        self.is_shown = False
        self.is_initialised = False
        self.generators = generators
        self.animation: Animation = ContstantAnimation(generators[0])
        self.animation_time = 1
        self.last_sources: set[Source] | None = None
        self.camera = Camera(np.zeros(2, float), 1.)
        self.image_viewer: None | ImageViewer = None
        self.show_selection = True

    @property
    def name(self) -> str:
        return "Image plotter"

    def open(self):
        self.is_shown = True

    def handle_inputs(self, app: Application) -> None:
        self.camera.handle_inputs(app)
        if (self.image_viewer is not None and not app.ui.want_capture_mouse and not app.ui.want_capture_keyboard
                and app.window.on_double_left_click()):
            closest_source = None
            closest_image = None
            closest_distance = None
            for source, subset in zip(app.selection.sources, app.selection.subsets):
                if source in self.last_sources:
                    for i in range(len(source.image_paths)):
                        world_circle = self.animation.get_circle_data(source, i)
                        circle = self.camera.world_circle_to_screen(app.window, world_circle)
                        d = np.linalg.norm(circle.center - app.window.cur_pos)
                        if d <= circle.radius and (closest_distance is None or d < closest_distance):
                            closest_source = source
                            closest_image = i
                            closest_distance = d
            if closest_source is not None:
                self.image_viewer.current_source = closest_source
                self.image_viewer.current_image = closest_image
                self.image_viewer.update_texture()


    def reload(self, app: Application):
        print("Reloading...")
        for generator in self.generators:
            generator.reset(app)
        for source in app.selection.sources:
            print(f"Loading source {source.name}...", end="")
            for i, image_path in enumerate(source.absolute_image_paths):
                print(f"\rLoading source {source.name}, image {i}/{len(source.image_paths)}...", end="")
                pil_image = Image.open(image_path)
                for generator in self.generators:
                    generator.process(app, source, i, pil_image)
            print()
        self.last_sources = set(app.selection.sources)
        if not self.is_initialised:
            for viewer in app.viewers:
                if isinstance(viewer, ImageViewer):
                    self.image_viewer = viewer
            self.camera.scale = 2./min(app.window.width, app.window.height)
        self.is_initialised = True

    @staticmethod
    def draw_circle(app: Application, circle: CircleData, selected: bool = False):
        if (
            circle.center[0] <= -circle.radius-SELECTION_THICKNESS or
            circle.center[0] >= app.window.width+circle.radius+SELECTION_THICKNESS or
            circle.center[1] <= -circle.radius - SELECTION_THICKNESS or
            circle.center[1] >= app.window.height + circle.radius + SELECTION_THICKNESS
        ):
            return
        if selected:
            app.ui.draw_filled_circle(circle.center, circle.radius+SELECTION_THICKNESS, SELECTION_COLOR)
        app.ui.draw_filled_circle(circle.center, circle.radius, circle.color)

    def draw_ui(self, app: Application) -> None:
        if not self.is_shown:
            return
        with imgui.begin("Image Plotter", True, imgui.WINDOW_NO_COLLAPSE) as info_window:
            if not info_window.opened:
                self.is_shown = False
            if imgui.button("Reload"):
                self.reload(app)
            _, x = imgui.input_float("animation time", self.animation_time)
            self.animation_time = min(100., max(0., x))
            _, self.show_selection = imgui.checkbox("show selection", self.show_selection)

            for generator in self.generators:
                if imgui.tree_node(generator.name):
                    if imgui.button("Apply") and self.is_initialised:
                        self.animation = LerpAnimation(self.animation.get_last_generator(), generator,
                                                       self.animation_time)
                    generator.draw_ui()
                    imgui.tree_pop()

        if not self.is_initialised:
            return
        self.animation.step(app)
        if self.animation.needs_replacement:
            self.animation = self.animation.get_replacement()

        # draw circles
        arrow_circle = None
        for source, subset in zip(app.selection.sources, app.selection.subsets):
            if source in self.last_sources:
                for i in range(len(source.image_paths)):
                    world_circle = self.animation.get_circle_data(source, i)
                    circle = self.camera.world_circle_to_screen(app.window, world_circle)
                    if self.image_viewer is not None and source == self.image_viewer.current_source and i == self.image_viewer.current_image:
                        arrow_circle = circle
                    if self.show_selection and i in subset:
                        app.ui.draw_filled_circle(circle.center, circle.radius+2, SELECTION_COLOR)
                    app.ui.draw_filled_circle(circle.center, circle.radius, circle.color)
        # draw arrow to indicate where the image viewer is
        if arrow_circle is not None:
            offset = arrow_circle.center+np.array([0., -arrow_circle.radius-2])
            app.ui.draw_triangle_filled(
                offset,
                offset + np.array([-ARROW_WIDTH/2, -ARROW_HEIGHT]),
                offset + np.array([+ARROW_WIDTH/2, -ARROW_HEIGHT]),
                ARROW_COLOR
            )
