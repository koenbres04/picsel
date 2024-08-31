import imgui
import numpy as np
import datetime
from PIL import Image
from application import Source, Application
from image_plotter import PositionGenerator, CircleData
from hilbertcurve.hilbertcurve import HilbertCurve


# from https://stackoverflow.com/questions/765396/exif-manipulation-library-for-python/765403#765403
def time_from_image(image: Image.Image) -> datetime.datetime | None:
    std_fmt = '%Y:%m:%d %H:%M:%S.%f'
    # for subsecond prec, see doi.org/10.3189/2013JoG12J126 , sect. 2.2, 2.3
    tags = [(36867, 37521),  # (DateTimeOriginal, SubsecTimeOriginal)
            (36868, 37522),  # (DateTimeDigitized, SubsecTimeDigitized)
            (306, 37520), ]  # (DateTime, SubsecTime)
    exif = image._getexif()

    dat = None
    sub = None
    for t in tags:
        dat = exif.get(t[0])
        sub = exif.get(t[1], 0)

        # PIL.PILLOW_VERSION >= 3.0 returns a tuple
        dat = dat[0] if type(dat) == tuple else dat
        sub = sub[0] if type(sub) == tuple else sub
        if dat is not None:
            break

    if dat is None:
        return None
    full = '{}.{}'.format(dat, sub)
    return datetime.datetime.strptime(full, std_fmt)


class HilbertPlotter(PositionGenerator):
    def __init__(self):
        self.times: dict[Source, list[datetime.datetime]] = {}
        self.colors: dict[Source, list[tuple]] = {}
        self.min_time = datetime.datetime.max
        self.max_time = datetime.datetime.min
        self.curve_iterations = 20
        self.log_point_radius = -9
        self.load_colors = False

    @property
    def name(self) -> str:
        return "Hilbert curve plot"

    def reset(self, app: Application):
        self.times = {source: [] for source in app.selection.sources}
        self.colors = {source: [] for source in app.selection.sources} if self.load_colors else None
        self.min_time = datetime.datetime.max
        self.max_time = datetime.datetime.min

    def draw_ui(self) -> None:
        _, x = imgui.input_int("curve iterations", self.curve_iterations)
        self.curve_iterations = min(30, max(1, x))
        _, self.log_point_radius = imgui.slider_float("Point radius", self.log_point_radius, -20, -4)
        _, self.load_colors = imgui.checkbox("read colors", self.load_colors)

    def process(self, app: Application, source: Source, index: int, pil_image: Image.Image):
        time = time_from_image(pil_image)
        if time is not None:
            self.min_time = min(self.min_time, time)
            self.max_time = max(self.max_time, time)
        self.times[source].append(time)
        if self.colors is not None:
            pixels = pil_image.getpixel((round(pil_image.width/2), round(pil_image.height/2)))
            self.colors[source].append(pixels)

    def get_circle_data(self, source: Source, index: int) -> CircleData:
        time = self.times[source][index]
        if time is None:
            return CircleData(np.array([0., 0.]), 1, np.array([1., 0., 0., 0.]))
        t = (time - self.min_time) / (self.max_time - self.min_time)
        curve = HilbertCurve(self.curve_iterations, 2)
        int_t = round(t*(1 << self.curve_iterations*2))
        p = np.array(curve.point_from_distance(int_t), dtype=float) / (1 << self.curve_iterations)
        if self.colors is None:
            color = (.7, 0., 0.)
        else:
            color = np.array(self.colors[source][index], dtype=float)/255
        return CircleData(np.array([-1., -1.]) + 2 * p, 2**self.log_point_radius, color)
