import os.path
import imgui
import moderngl
import pygame
from PIL import Image
from application import Application, Source, Viewer


def texture_from_file(image_file: str) -> moderngl.Texture:
    pil_image = Image.open(image_file)
    tex = moderngl.get_context().texture(pil_image.size, 3)
    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    tex.swizzle = 'RGB'
    tex.write(pil_image.tobytes())
    return tex

IMAGE_TOP_LEFT_OFFSET = (15, 60)
IMAGE_BOTTOM_RIGHT_OFFSET = (15, 15)
OUTLINE_THICKNESS = 5


class ImageViewer(Viewer):
    def __init__(self):
        self.is_shown = True
        self.image_texture: moderngl.Texture | None = None
        self.current_source: Source | None = None
        self.current_image: int = 0

    @property
    def name(self) -> str:
        return "Image viewer"

    def open(self):
        self.is_shown = True

    def ensure_source_exists(self, parent: Application):
        if self.current_source in parent.selection.sources:
            return
        self.current_image = 0
        if sum(len(source.image_paths) for source in parent.selection.sources) == 0:
            self.current_source = None
            self.image_texture = None
            return
        for source in parent.selection.sources:
            if source.image_paths:
                self.current_source = source
                self.update_texture()
                return

    def handle_inputs(self, parent: Application) -> None:
        if self.current_source is None or parent.ui.want_capture_keyboard:
            return
        try:
            source_index = parent.selection.sources.index(self.current_source)
        except ValueError:
            return
        if parent.window.on_key_down(pygame.K_SPACE):
            if self.current_image in parent.selection.subsets[source_index]:
                parent.selection.subsets[source_index].remove(self.current_image)
            else:
                parent.selection.subsets[source_index].add(self.current_image)
        if parent.window.on_key_down(pygame.K_LEFT):
            self.current_image = self.current_image-1
            if self.current_image == -1:
                self.current_source = parent.selection.sources[(source_index-1)%len(parent.selection.sources)]
                self.current_image = len(self.current_source.image_paths)-1
            self.update_texture()
        elif parent.window.on_key_down(pygame.K_RIGHT):
            self.current_image = self.current_image+1
            if self.current_image == len(self.current_source.image_paths):
                self.current_image = 0
                self.current_source = parent.selection.sources[(source_index+1)%len(parent.selection.sources)]
            self.update_texture()

    def update_texture(self):
        self.image_texture = texture_from_file(os.path.join(self.current_source.relative_to_dir,
                                                            self.current_source.image_paths[self.current_image]))


    def draw_ui(self, parent: Application) -> None:
        if not self.is_shown:
            return
        with imgui.begin("Image viewer", True, imgui.WINDOW_NO_COLLAPSE) as image_window:
            if not image_window.opened:
                self.is_shown = False
            self.ensure_source_exists(parent)
            if self.image_texture is None:
                imgui.text("No image to show")
                return
            width, height = self.image_texture.size
            file_name = os.path.split(self.current_source.image_paths[self.current_image])[1]
            imgui.text(f"{self.current_source.name} - {file_name}"
                       f" ({self.current_image+1}/{len(self.current_source.image_paths)}) - {width}x{height}")
            window_size = imgui.get_window_size()
            window_pos = imgui.get_window_position()
            available_size = tuple(max(100, window_size[i]-IMAGE_TOP_LEFT_OFFSET[i]-IMAGE_BOTTOM_RIGHT_OFFSET[i])
                                   for i in (0, 1))
            scale_factor = min(available_size[i]/self.image_texture.size[i] for i in (0, 1))

            subset = parent.selection.subsets[parent.selection.sources.index(self.current_source)]
            imgui.get_window_draw_list().add_rect(
                window_pos[0]+IMAGE_TOP_LEFT_OFFSET[0],
                window_pos[1]+IMAGE_TOP_LEFT_OFFSET[1],
                round(window_pos[0]+IMAGE_TOP_LEFT_OFFSET[0]+scale_factor*self.image_texture.size[0]),
                round(window_pos[1] + IMAGE_TOP_LEFT_OFFSET[1] + scale_factor * self.image_texture.size[1]),
                imgui.get_color_u32_rgba(0., .7, 0., 1.) if self.current_image in subset else
                imgui.get_color_u32_rgba(.7, 0., 0., 1.),
                thickness=OUTLINE_THICKNESS
            )
            imgui.get_window_draw_list().add_image(self.image_texture.glo, tuple(
                window_pos[i]+IMAGE_TOP_LEFT_OFFSET[i] for i in (0, 1)
            ), tuple(
                round(window_pos[i]+IMAGE_TOP_LEFT_OFFSET[i]+scale_factor*self.image_texture.size[i]) for i in (0, 1)
            ))




