from __future__ import annotations
import numpy as np
import pygame
import pygame.gfxdraw
import moderngl
import OpenGL.GL as GL


PYGAME_DIGITS = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                 pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]

class PygameGLWindow:
    def __init__(self, size: tuple[int, int], caption: str, frame_rate: float, background_color,
                 resizable=False, tracked_keys=None, track_digits=False):
        self._start_screen_size = size
        self._caption = caption
        self.frame_rate = frame_rate
        self.background_color = background_color
        self._resizable = resizable
        self._int_size: tuple[int, int] = size
        self._do_quit = False
        self.mgl: moderngl.Context | None = None
        self.clock = None
        self._screen2cam: np.ndarray = np.zeros((4, 3), dtype=float)
        self._update_size(size)
        self._cur_pos = None
        self._cur_click = None
        self._delta_cur = None
        self.events = None
        self._key_tracking = dict()
        self._key_down_tracking = dict()
        self.track_digits = track_digits
        self.digit_presses = []
        self._default_font = None
        self._on_mouse_down = [False for _ in range(20)]
        self._on_mouse_up = [False for _ in range(20)]
        self._scroll_wheel_y = 0
        self._on_screen_resized = False
        if tracked_keys is not None:
            for key in tracked_keys:
                self._key_tracking[key] = False

    def open(self):
        # initialize pygame
        pygame.init()
        if self._resizable:
            pygame.display.set_mode(self._start_screen_size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            pygame.display.set_mode(self._start_screen_size, pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption(self._caption)

        # initialise moderngl
        self.mgl = moderngl.create_context()
        self.mgl.gc_mode = 'auto'
        self.mgl.clear(*(x / 255.0 for x in self.background_color), 1.0)

        # handle timing and input things
        self.clock = pygame.time.Clock()
        self._cur_pos = self._screen_to_np(pygame.mouse.get_pos())
        self._cur_click = pygame.mouse.get_pressed(num_buttons=5)
        self._delta_cur = np.zeros(2, dtype=float)
        self.events = pygame.event.get()
        for key in self._key_tracking.keys():
            self._key_tracking[key] = False
            self._key_down_tracking[key] = False

    def next_frame(self):
        # reset for next frame
        pygame.display.flip()
        self.clock.tick(self.frame_rate)
        self.mgl.clear(*(x / 255.0 for x in self.background_color), 1.0)

        # handle mouse values
        last_cur_pos = self._cur_pos
        self._cur_pos = self._screen_to_np(pygame.mouse.get_pos())
        self._delta_cur = self._cur_pos-last_cur_pos
        self._cur_click = pygame.mouse.get_pressed()

        # handle events
        self.events = pygame.event.get()
        for key in self._key_tracking.keys():
            self._key_down_tracking[key] = False
        self.digit_presses.clear()
        for i in range(len(self._on_mouse_down)):
            self._on_mouse_down[i] = False
            self._on_mouse_up[i] = False
        self._scroll_wheel_y = 0
        self._on_screen_resized = False
        for event in self.events:
            if event.type == pygame.QUIT:
                self.quit()
            elif self._resizable and event.type == pygame.VIDEORESIZE:
                self._update_size(event.size)
                self._on_screen_resized = True
            elif event.type == pygame.KEYDOWN:
                if event.key in self._key_tracking:
                    self._key_tracking[event.key] = True
                    self._key_down_tracking[event.key] = True
            elif event.type == pygame.KEYUP:
                if event.key in self._key_tracking:
                    self._key_tracking[event.key] = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._on_mouse_down[event.button] = True
            elif event.type == pygame.MOUSEBUTTONUP:
                self._on_mouse_up[event.button] = True
            elif event.type == pygame.MOUSEWHEEL:
                self._scroll_wheel_y = event.y
            if self.track_digits and event.type == pygame.KEYDOWN and event.key in PYGAME_DIGITS:
                self.digit_presses.append(PYGAME_DIGITS.index(event.key))

    def close(self):
        self.mgl.release()
        pygame.quit()
        self._do_quit = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def loop(self):
        i = 0
        while self.do_continue():
            yield i
            self.next_frame()
            i += 1

    def do_continue(self):
        return not self._do_quit

    def quit(self):
        self._do_quit = True

    @property
    def delta_time(self):
        return self.clock.get_time()/1000

    def enable_blend(self):
        self.mgl.enable(moderngl.BLEND)

    def enable_program_point_size(self):
        self.mgl.enable(moderngl.PROGRAM_POINT_SIZE)

    @staticmethod
    def enable_framebuffer_srgb():
        GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)

    @staticmethod
    def disable_framebuffer_srgb():
        GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)

    def _update_size(self, size: tuple[int, int]):
        self._int_size = size
        self._screen2cam = np.array([
            [2/self.width, 0, 0],
            [0, -2/self.height, 0],
            [0, 0, 0],
            [0, 0, 1]
        ], dtype=float)
        if self.mgl is not None:
            self.mgl.screen.viewport = 0, 0, *size

    @property
    def int_size(self) -> tuple[int, int]:
        return self._int_size

    @property
    def size(self) -> np.ndarray:
        return np.array(self._int_size, dtype=float)

    @property
    def width(self) -> float:
        return float(self._int_size[0])

    @property
    def height(self) -> float:
        return float(self._int_size[1])

    @property
    def cur_pos(self):
        return self._cur_pos.copy()

    @property
    def delta_cur(self):
        return self._delta_cur.copy()

    @property
    def caption(self):
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value
        if pygame.get_init():
            pygame.display.set_caption(value)

    def is_mouse_button_down(self, key):
        return self._cur_click[key]

    def is_key_down(self, key):
        if key not in self._key_tracking:
            raise Exception(f"Key '{key}' not tracked!")
        return self._key_tracking[key]

    def on_key_down(self, key):
        if key not in self._key_down_tracking:
            raise Exception(f"Key '{key}' not tracked!")
        return self._key_down_tracking[key]

    def get_scroll_wheel_y(self):
        return self._scroll_wheel_y

    def on_mouse_button_down(self, key):
        return self._on_mouse_down[key]

    def on_mouse_button_up(self, key):
        return self._on_mouse_up[key]

    def on_resize(self):
        return self._on_screen_resized

    @staticmethod
    def np_to_screen(x: np.ndarray):
        return tuple(round(y) for y in x)

    @staticmethod
    def _screen_to_np(x: tuple[int, int]):
        return np.array(x, dtype=float)

    @property
    def top_left(self) -> np.ndarray:
        return self._screen_to_np((0, 0))

    @property
    def bottom_left(self) -> np.ndarray:
        return self._screen_to_np((0, self._int_size[1]))

    @property
    def top_right(self) -> np.ndarray:
        return self._screen_to_np((self._int_size[0], 0))

    @property
    def bottom_right(self) -> np.ndarray:
        return self._screen_to_np(self._int_size)

    @property
    def center(self) -> np.ndarray:
        return self.size/2

    @property
    def screen2cam(self) -> np.ndarray:
        return self._screen2cam

    def is_in_screen(self, x):
        p = self.np_to_screen(x)
        return 0 <= p[0] <= self.width and 0 <= p[1] <= self.height

    def texture_from_surface(self, surface) -> moderngl.Texture:
        # see https://www.youtube.com/watch?v=LFbePt8i0DI
        tex = self.mgl.texture(surface.get_size(), 4)
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = 'BGRA'
        tex.write(surface.get_view('1'))
        return tex

    def quick_vertex_array(self, program: ProgramWrapper, buffers: dict[str | tuple[str, ...], moderngl.Buffer],
                     index_buffer: moderngl.Buffer | None = None, mode=moderngl.TRIANGLES) -> moderngl.VertexArray:
        buffer_list = list(buffers.values())
        if index_buffer is not None:
            buffer_list.append(index_buffer)
        buffer_items = (((key if isinstance(key, tuple) else (key, )), value) for key, value in buffers.items())
        return self.mgl.vertex_array(program.program, [
            (buffer, " ".join(program.get_format(inp) for inp in inputs), *inputs)
            for inputs, buffer in buffer_items
        ], mode=mode, index_buffer=(None if index_buffer is None else index_buffer))

    def finish_drawing(self):
        self.mgl.finish()

    def use_screen_frame_buffer(self):
        self.mgl.screen.use()


class ProgramWrapper:
    def __init__(self, program: moderngl.Program):
        self.program = program
        self._texture_uniforms: list[str] = []
        self._textures: list[moderngl.Texture] = []

    def __setitem__(self, key, value):
        try:
            if isinstance(value, moderngl.Texture):
                if key in self._textures:
                    self._textures[self._texture_uniforms.index(key)] = value
                else:
                    self.program[key] = len(self._textures)
                    self._texture_uniforms.append(key)
                    self._textures.append(value)
            elif isinstance(value, np.ndarray):
                self.program[key] = tuple(value.reshape(value.size, order="F"))
            else:
                self.program[key] = value
        except KeyError:
            print(f"Warning: Unused key '{key}' attempted to be assigned to!")

    def get_format(self, key: str) -> str:
        attribute = self.program[key]
        return f"{attribute.dimension}{attribute.shape}"

    def bind_textures(self):
        for i, texture in enumerate(self._textures):
            texture.use(i)


# Coordinates and shaders based on https://www.youtube.com/watch?v=LFbePt8i0DI
_SINGLE_QUAD_DATA = np.array([
    # position (x, y), uv coords (x, y)
    [-1.0, 1.0, 0.0, 0.0],  # topleft
    [1.0, 1.0, 1.0, 0.0],  # topright
    [-1.0, -1.0, 0.0, 1.0],  # bottomleft
    [1.0, -1.0, 1.0, 1.0],  # bottomright
], dtype='f4')

_SINGLE_QUAD_VERT_SHADER = '''
#version 330 core

in vec2 vert;
in vec2 texcoord;
out vec2 uvs;

void main() {
    uvs = texcoord;
    gl_Position = vec4(vert, 0.0, 1.0);
}
'''

_SINGLE_QUAD_FRAG_SHADER = '''
#version 330 core

uniform sampler2D tex;

in vec2 uvs;
out vec4 f_color;

void main() {
    f_color = texture(tex, uvs);
}
'''


class PygameUISurface:
    def __init__(self, window: PygameGLWindow):
        self.window = window
        self._default_font = None
        self.surface = pygame.Surface(window.int_size, flags=pygame.SRCALPHA)
        self.surface.fill((0, 0, 0, 0))
        self.texture = window.texture_from_surface(self.surface)

        quad_buffer = self.window.mgl.buffer(_SINGLE_QUAD_DATA)
        self.program = ProgramWrapper(window.mgl.program(_SINGLE_QUAD_VERT_SHADER, _SINGLE_QUAD_FRAG_SHADER))
        self.program["tex"] = self.texture
        self.vertex_array = self.window.quick_vertex_array(self.program, {
            ("vert", "texcoord"): quad_buffer
        }, mode=moderngl.TRIANGLE_STRIP)

        self.window.enable_blend()

    def reset_surface(self):
        if self.surface.get_size() != self.window.int_size:
            self.surface = pygame.transform.scale(self.surface, self.window.int_size)
            self.texture = self.window.texture_from_surface(self.surface)
            self.program["tex"] = self.texture
        self.surface.fill((0, 0, 0, 0))

    def update_texture(self):
        self.texture.write(self.surface.get_view('1'))

    def render(self):
        self.program.bind_textures()
        self.vertex_array.render()

    def __enter__(self):
        self.reset_surface()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.update_texture()

    def set_default_font(self, size, font_name=None, bold=False, italic=False):
        self._default_font = pygame.font.SysFont(font_name, size, bold=bold, italic=italic)

    def draw_text(self, text, color, position, offset=(0, 0), font=None, anti_alias=True):
        if font is None:
            font = self._default_font
        img = font.render(text, anti_alias, color)
        size = np.array(img.get_size(), dtype=float)
        offset = np.array(offset, dtype=float)
        pos = self.window.np_to_screen(position - offset * size)
        self.surface.blit(img, pos)

    def draw_circle(self, center: np.ndarray, radius, color: tuple):
        r = round(radius)
        c = self.window.np_to_screen(center)
        if np.linalg.norm(center)-r < np.linalg.norm(self.window.size):
            pygame.gfxdraw.filled_circle(self.surface, c[0], c[1], r, color)
            pygame.gfxdraw.aacircle(self.surface, c[0], c[1], r, color)

    def draw_line(self, p1: np.ndarray, p2: np.ndarray, thickness, color):
        thickness = round(thickness)
        if thickness == 1:
            pygame.gfxdraw.line(self.surface, *self.window.np_to_screen(p1), *self.window.np_to_screen(p2), color)
        elif thickness > 1:
            pygame.draw.line(self.surface, color, self.window.np_to_screen(p1),
                             self.window.np_to_screen(p2), thickness)

    def draw_rect(self, start: np.ndarray, size: np.ndarray, color, width=0):
        rect_corner = self.window.np_to_screen(start)
        rect_size = tuple(round(x) for x in size)
        pygame.draw.rect(self.surface, color, rect_corner + rect_size, width)

