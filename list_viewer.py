from __future__ import annotations
import os
import imgui
from application import Viewer, Application
from image_viewer import ImageViewer


class ListViewer(Viewer):
    def __init__(self):
        self.is_shown = True
        self.image_viewer: ImageViewer | None = None

    def open(self):
        self.is_shown = True

    @property
    def name(self) -> str:
        return "Image list"

    def draw_ui(self, app: Application) -> None:
        # find the current image viewer object
        if self.image_viewer is None:
            for viewer in app.viewers:
                if isinstance(viewer, ImageViewer):
                    self.image_viewer = viewer
                    break
        if not self.is_shown:
            return
        with imgui.begin("Image list", closable=True) as list_window:
            if not list_window.opened:
                self.is_shown = False
            if list_window.expanded:
                if len(app.selection.sources) == 0:
                    imgui.text("No sources to show.")
                for source, subset in zip(app.selection.sources, app.selection.subsets):
                    if imgui.collapsing_header(f"{source.name} - {len(source.image_paths)} files", None,
                                               imgui.TREE_NODE_DEFAULT_OPEN)[0]:
                        for i, image in enumerate(source.image_paths):
                            # draw little arrow button
                            if self.image_viewer is not None:
                                is_pointed = (self.image_viewer.current_source == source
                                              and self.image_viewer.current_image == i)
                                if is_pointed:
                                    imgui.push_style_color(imgui.COLOR_BUTTON, 0.7, 0.7, 0.)
                                imgui.push_id(f"a button - {i} {source.absolute_path}")
                                if imgui.small_button(">"):
                                    self.image_viewer.set_image(source, i)
                                imgui.pop_id()
                                if is_pointed:
                                    imgui.pop_style_color()
                                imgui.same_line()
                            # draw clickable file name
                            is_selected = i in subset
                            _, result = imgui.selectable(os.path.basename(image), selected=is_selected)
                            if result and not is_selected:
                                subset.add(i)
                                app.changed = True
                            if not result and is_selected:
                                subset.remove(i)
                                app.changed = True
