from __future__ import annotations
import functools
import json
import os
import shutil
import abc
import pygame
from pygame_gl_code import PygameGLWindow
from imgui_rendering import ImguiUI
import imgui
import easygui


class Source:
    def __init__(self, absolute_path: str, is_folder: bool, image_paths: list[str]):
        self.absolute_path = absolute_path
        self.is_folder = is_folder
        self.image_paths = image_paths

    @property
    def relative_to_dir(self) -> str:
        return self.absolute_path if self.is_folder else os.path.dirname(self.absolute_path)

    @classmethod
    def from_folder(cls, path: str) -> Source:
        image_paths = []
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)) and os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS:
                image_paths.append(file)
        return Source(path, True, image_paths)

    @classmethod
    def from_selection_file(cls, path: str) -> Source:
        with open(path) as file:
            data = json.load(file)
        image_paths = []
        for sub_path, source_data in data["sources"].items():
            if source_data["type"] == "selection":
                sub_path = os.path.dirname(sub_path)
            for image_path in source_data["selection"]:
                image_paths.append(os.path.join(sub_path, image_path))
        # noinspection PyTypeChecker
        return Source(path, False, image_paths)

    @property
    def absolute_image_paths(self):
        for image_path in self.image_paths:
            if self.is_folder:
                yield os.path.join(self.absolute_path, image_path)
            else:
                yield os.path.join(os.path.dirname(self.absolute_path), image_path)

    @property
    def name(self) -> str:
        return os.path.basename(self.absolute_path)




class Selection:
    def __init__(self):
        self.sources: list[Source] = []
        self.subsets: list[set[int]] = []

    @classmethod
    def from_file(cls, path: str):
        base_dir = os.path.dirname(path)
        result = Selection()
        with open(path) as file:
            data = json.load(file)
        for source_path, source_data in data["sources"].items():
            if source_data["type"] == "folder":
                source = Source.from_folder(os.path.join(base_dir, source_path))
            else:
                source = Source.from_selection_file(os.path.join(base_dir, source_path))
            result.sources.append(source)
            source_set = set(source_data["selection"])
            result.subsets.append(set(i for i, image_path in enumerate(source.image_paths) if image_path in source_set))
        return result

    def add_source(self, source: Source):
        self.sources.append(source)
        self.subsets.append(set())

    def remove_source(self, index: int):
        self.sources.pop(index)
        self.subsets.pop(index)

    def save(self, path: str):
        base_dir = os.path.dirname(path)
        sources = {}
        for source, subset in zip(self.sources, self.subsets):
            sources[os.path.relpath(source.absolute_path, base_dir)] = {
                "type": "folder" if source.is_folder else "selection",
                "selection": [
                    p for i, p in enumerate(source.image_paths) if i in subset
                ]
            }
        result = {"sources": sources}
        with open(path, "w") as file:
            json.dump(result, file, indent=2)

    def export(self, folder: str):
        print("")
        for source, subset in zip(self.sources, self.subsets):
            n = 0
            for i, file in enumerate(source.image_paths):
                if i in subset:
                    print(f"\rcopying files {n+1}/{len(subset)} from {source.name}...", end="")
                    n += 1
                    # noinspection PyTypeChecker
                    shutil.copy2(os.path.join(source.relative_to_dir, file), folder)



class Viewer(abc.ABC):

    def handle_inputs(self, app: Application) -> None:
        pass

    @abc.abstractmethod
    def draw_ui(self, app: Application) -> None:
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def open(self):
        pass


class Application:
    def __init__(self, window: PygameGLWindow, ui: ImguiUI, viewers: list[Viewer]):
        self.window = window
        self.ui = ui
        self.current_file: str | None = None
        self.changed = False
        self.selection = Selection()
        self.after_popup = None
        self.viewers = viewers
        self.open_changes_popup = False

    def draw_menu_items(self):
        with imgui.begin_menu("File") as file_menu:
            if file_menu.opened:
                if imgui.menu_item("New...")[0]:
                    self.new_file()
                if imgui.menu_item("Open...")[0]:
                    self.open()
                if imgui.menu_item("Save...")[0]:
                    self.save()
                if imgui.menu_item("Save as...")[0]:
                    self.save_as()
                if imgui.menu_item("Export")[0]:
                    self.export()
        with imgui.begin_menu("Tools") as view_menu:
            if view_menu.opened:
                for viewer in self.viewers:
                    if imgui.menu_item(viewer.name)[0]:
                        viewer.open()

    def draw_changes_pop_up(self):
        imgui.text("Do you want to save your current changes?")
        if imgui.button("Yes"):
            self.save()
            self.after_popup()
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("No"):
            self.after_popup()
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Cancel"):
            imgui.close_current_popup()

    def draw_source_window(self):
        if imgui.button("+ folder"):
            self.add_folder_source()
        imgui.same_line()
        if imgui.button("+ selection"):
            self.add_json_source()
        with imgui.begin_child("sources_list", 0., 0., True):
            for i, source in enumerate(self.selection.sources):
                imgui.text(source.name)
                imgui.same_line()
                if imgui.button("-"):
                    self.selection.remove_source(i)

    def export(self):
        directory = easygui.diropenbox()
        if directory is None:
            return
        self.selection.export(directory)

    def new_file(self, allow_popup=True):
        if allow_popup and self.changed:
            self.open_changes_popup = True
            self.after_popup = functools.partial(self.new_file, allow_popup=False)
            return
        self.selection = Selection()
        self.current_file = None
        self.changed = False

    def open_file(self, file: str):
        self.selection = Selection.from_file(file)
        self.current_file = file
        self.changed = False

    def open(self, allow_popup=True):
        if allow_popup and self.changed:
            self.open_changes_popup = True
            self.after_popup = functools.partial(self.open, allow_popup=False)
            return
        file = easygui.fileopenbox(filetypes=["*.json"])
        if file is None:
            return
        self.open_file(file)

    def save(self):
        if self.current_file is None:
            self.save_as()
            return
        self.selection.save(self.current_file)
        self.changed = False

    def save_as(self):
        new_file = easygui.filesavebox(filetypes=["*.json"], default=self.current_file)
        if new_file is None:
            return
        self.selection.save(new_file)
        self.current_file = new_file
        self.changed = False

    def add_json_source(self):
        source_file = easygui.fileopenbox(filetypes=["*.json"], default=self.current_file)
        if source_file is None:
            return
        self.selection.add_source(Source.from_selection_file(source_file))
        self.changed = True

    def add_folder_source(self):
        directory = easygui.diropenbox()
        if directory is None:
            return
        self.selection.add_source(Source.from_folder(directory))
        self.changed = True

    def main_loop(self):
        for _ in self.window.loop():
            self.window.caption = (f"picsel - {'new file' if self.current_file is None else self.current_file}"
                                   f"{'*' if self.changed else ''}")
            self.ui.process_events()

            if self.window.is_key_down(pygame.K_LCTRL) and self.window.on_key_down(pygame.K_s):
                self.save()
            if self.window.on_window_close():
                if self.changed:
                    self.open_changes_popup = True
                    self.after_popup = lambda : self.window.quit()
                else:
                    self.window.quit()
            for viewer in self.viewers:
                viewer.handle_inputs(self)

            self.ui.new_frame()

            # main menu
            with imgui.begin_main_menu_bar() as main_menu_bar:
                main_menu_bar_height = imgui.get_window_height()
                if main_menu_bar.opened:
                    self.draw_menu_items()

            if self.open_changes_popup:
                imgui.open_popup("You have unsaved changes.")
                self.open_changes_popup = False
            with imgui.begin_popup_modal("You have unsaved changes.") as popup:
                if popup.opened:
                    self.draw_changes_pop_up()

            imgui.set_next_window_position(0., main_menu_bar_height)
            imgui.set_next_window_size(SOURCES_WINDOW_WIDTH, self.window.height-main_menu_bar_height)
            with imgui.begin("sources", False, imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_MOVE |
                                               imgui.WINDOW_NO_RESIZE):
                self.draw_source_window()

            for viewer in self.viewers:
                viewer.draw_ui(self)

            self.ui.render()

SOURCES_WINDOW_WIDTH = 200.
IMAGE_EXTENSIONS = {".png", ".jpeg", ".jpg"}
