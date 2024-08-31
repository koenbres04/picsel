from __future__ import annotations
import os
import imgui
from application import Viewer, Application


class ListViewer(Viewer):
    def __init__(self):
        self.is_shown = True

    def open(self):
        self.is_shown = True

    @property
    def name(self) -> str:
        return "Image list"

    def draw_ui(self, app: Application) -> None:
        if not self.is_shown:
            return
        with imgui.begin("Image list", closable=True) as list_window:
            if not list_window.opened:
                self.is_shown = False
            if list_window.expanded:
                if len(app.selection.sources) == 0:
                    imgui.text("No sources to show.")
                for source, subset in zip(app.selection.sources, app.selection.subsets):
                    if imgui.collapsing_header(f"{source.name} - {len(source.image_paths)} files",
                                               imgui.TREE_NODE_DEFAULT_OPEN)[0]:
                        for i, image in enumerate(source.image_paths):
                            is_selected = i in subset
                            _, result = imgui.selectable(os.path.basename(image), selected=is_selected)
                            if result and not is_selected:
                                subset.add(i)
                                app.changed = True
                            if not result and is_selected:
                                subset.remove(i)
                                app.changed = True
