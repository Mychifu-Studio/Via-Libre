from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, Sequence, TypeAlias


class MouseProtocol(Protocol):
    def captureMouse(self) -> None: ...
    def releaseMouse(self) -> None: ...
    def centerMouse(self) -> None: ...
    def getMouseDelta(self) -> tuple[int, int]: ...
    def hasMouse(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class RadialOption:
    text: str
    image: Optional[str] = None


RadialOptionInput: TypeAlias = RadialOption | tuple[str, Optional[str]]
OnSelectCallback: TypeAlias = Callable[[int, RadialOption], None]
OnChangeCallback: TypeAlias = Callable[[Optional[int], Optional[RadialOption]], None]
OnCancelCallback: TypeAlias = Callable[[], None]


from direct.showbase.DirectObject import DirectObject
from direct.gui.DirectGui import DirectFrame, DirectLabel
from panda3d.core import TextNode


class RadialMenu(DirectObject):
    """Menu radial modulaire piloté par un wrapper souris.

    API publique :
    - open_menu()
    - close_menu()
    - set_options()
    - set_title()
    - set_deadzones()
    - destroy()
    """

    def __init__(
        self,
        base: Any,
        mouse: MouseProtocol,
        name: str,
        options: Sequence[RadialOptionInput],
        *,
        option_count: Optional[int] = None,
        deadzone_enter_px: int = 80,
        deadzone_leave_px: int = 65,
        visual_radius: float = 0.42,
        start_angle_deg: float = 90.0,
        clockwise: bool = True,
        open_event: str = "tab",
        close_event: str = "tab-up",
        bind_events: bool = True,
        on_select: Optional[OnSelectCallback] = None,
        on_change: Optional[OnChangeCallback] = None,
        on_cancel: Optional[OnCancelCallback] = None,
        backdrop_alpha: float = 0.20,
        selected_scale: float = 1.12,
        unselected_scale: float = 1.0,
    ) -> None:
        super().__init__()

        if deadzone_leave_px > deadzone_enter_px:
            raise ValueError("deadzone_leave_px doit être <= deadzone_enter_px")

        normalized_options = self._normalize_options(options)
        if len(normalized_options) < 2:
            raise ValueError("Un menu radial doit contenir au moins 2 options")

        if option_count is not None and option_count != len(normalized_options):
            raise ValueError(
                f"option_count={option_count} mais {len(normalized_options)} options fournies"
            )

        self.base = base
        self.mouse = mouse
        self.name = name
        self.options: list[RadialOption] = normalized_options

        self.deadzone_enter_px = deadzone_enter_px
        self.deadzone_leave_px = deadzone_leave_px
        self.visual_radius = visual_radius
        self.start_angle_deg = start_angle_deg
        self.clockwise = clockwise

        self.open_event = open_event
        self.close_event = close_event
        self.bind_events = bind_events

        self.on_select = on_select
        self.on_change = on_change
        self.on_cancel = on_cancel

        self.backdrop_alpha = backdrop_alpha
        self.selected_scale = selected_scale
        self.unselected_scale = unselected_scale

        self.is_open = False
        self.current_index: Optional[int] = None
        self._task_name = f"radial-menu-update-{id(self)}"
        self._option_nodes: list[dict[str, Any]] = []

        self.root = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=(0, 0, 0, 0),
            sortOrder=1000,
        )
        self.root.hide()

        self.backdrop = DirectFrame(
            parent=self.root,
            frameColor=(0, 0, 0, self.backdrop_alpha),
            frameSize=(-1.8, 1.8, -1.1, 1.1),
        )

        self.center = DirectFrame(
            parent=self.root,
            frameColor=(0, 0, 0, 0.55),
            frameSize=(-0.10, 0.10, -0.10, 0.10),
            pos=(0, 0, 0),
        )

        self.title = DirectLabel(
            parent=self.root,
            text=self.name,
            relief=None,
            pos=(0, 0, 0.62),
            scale=0.07,
            text_align=TextNode.ACenter,
            text_fg=(1, 1, 1, 1),
        )

        self._rebuild_options()

        if self.bind_events:
            self.accept(self.open_event, self.open_menu)
            self.accept(self.close_event, self.close_menu)

    # =========
    # Public API
    # =========

    def open_menu(self) -> None:
        if self.is_open or not self.mouse.hasMouse():
            return

        self.is_open = True
        self.current_index = None
        self._highlight(None)

        self.mouse.captureMouse()
        self.mouse.centerMouse()

        self.root.show()
        self.base.taskMgr.add(self._update_menu, self._task_name)

    def close_menu(self) -> None:
        if not self.is_open:
            return

        self.is_open = False
        self.base.taskMgr.remove(self._task_name)
        self.root.hide()

        selected_index = self.current_index
        selected_option = self.options[selected_index] if selected_index is not None else None

        self.current_index = None
        self._highlight(None)
        self.mouse.releaseMouse()

        if self.on_change is not None:
            self.on_change(None, None)

        if selected_index is None:
            if self.on_cancel is not None:
                self.on_cancel()
            return

        if self.on_select is not None and selected_option is not None:
            self.on_select(selected_index, selected_option)

    def set_options(
        self,
        *,
        name: Optional[str] = None,
        options: Optional[Sequence[RadialOptionInput]] = None,
        option_count: Optional[int] = None,
        start_angle_deg: Optional[float] = None,
        clockwise: Optional[bool] = None,
    ) -> None:
        if name is not None:
            self.set_title(name)

        rebuild_layout = False

        if start_angle_deg is not None:
            self.start_angle_deg = start_angle_deg
            rebuild_layout = True

        if clockwise is not None:
            self.clockwise = clockwise
            rebuild_layout = True

        if options is not None:
            normalized = self._normalize_options(options)

            if len(normalized) < 2:
                raise ValueError("Un menu radial doit contenir au moins 2 options")

            if option_count is not None and option_count != len(normalized):
                raise ValueError(
                    f"option_count={option_count} mais {len(normalized)} options fournies"
                )

            self.options = normalized
            self.current_index = None
            rebuild_layout = True

        if rebuild_layout:
            self._rebuild_options()

    def set_title(self, name: str) -> None:
        self.name = name
        self.title["text"] = name

    def set_deadzones(self, enter_px: int, leave_px: int) -> None:
        if leave_px > enter_px:
            raise ValueError("leave_px doit être <= enter_px")

        self.deadzone_enter_px = enter_px
        self.deadzone_leave_px = leave_px

    def destroy(self) -> None:
        self.base.taskMgr.remove(self._task_name)
        self.ignoreAll()

        for node in self._option_nodes:
            node["frame"].destroy()
        self._option_nodes.clear()

        if getattr(self, "root", None) is not None:
            self.root.destroy()
            self.root = None

    # =================
    # Internal methods
    # =================

    @staticmethod
    def _normalize_options(options: Sequence[RadialOptionInput]) -> list[RadialOption]:
        normalized: list[RadialOption] = []

        for item in options:
            if isinstance(item, RadialOption):
                normalized.append(item)
            else:
                text, image = item
                normalized.append(RadialOption(text=text, image=image))

        return normalized

    def _rebuild_options(self) -> None:
        for node in self._option_nodes:
            node["frame"].destroy()
        self._option_nodes.clear()

        count = len(self.options)
        step = 360.0 / count
        direction = -1.0 if self.clockwise else 1.0

        for index, option in enumerate(self.options):
            angle_deg = self.start_angle_deg + index * step * direction
            angle_rad = math.radians(angle_deg)

            x = math.cos(angle_rad) * self.visual_radius
            z = math.sin(angle_rad) * self.visual_radius

            frame = DirectFrame(
                parent=self.root,
                frameColor=(0.08, 0.08, 0.08, 0.78),
                frameSize=(-0.16, 0.16, -0.14, 0.14),
                pos=(x, 0, z),
            )

            icon = None
            if option.image:
                icon = DirectFrame(
                    parent=frame,
                    frameColor=(1, 1, 1, 0),
                    relief=None,
                    image=option.image,
                    pos=(0, 0, 0.05),
                    scale=0.12,
                )

            label = DirectLabel(
                parent=frame,
                text=option.text,
                relief=None,
                pos=(0, 0, -0.065 if icon is not None else 0.0),
                scale=0.05,
                text_align=TextNode.ACenter,
                text_fg=(1, 1, 1, 1),
                text_wordwrap=9,
            )

            self._option_nodes.append(
                {
                    "index": index,
                    "option": option,
                    "frame": frame,
                    "icon": icon,
                    "label": label,
                }
            )

        self._highlight(None)

    def _update_menu(self, task):
        if not self.mouse.hasMouse():
            self._set_current_index(None)
            return task.cont

        dx, dy = self.mouse.getMouseDelta()
        dist = math.hypot(dx, dy)

        threshold = (
            self.deadzone_enter_px
            if self.current_index is None
            else self.deadzone_leave_px
        )

        new_index = None if dist < threshold else self._index_from_delta(dx, dy)
        self._set_current_index(new_index)

        return task.cont

    def _index_from_delta(self, dx: int, dy: int) -> int:
        vx = dx
        vy = -dy

        angle = math.degrees(math.atan2(vy, vx))
        sector_size = 360.0 / len(self.options)

        if self.clockwise:
            normalized = (90.0 - angle) % 360.0
        else:
            normalized = (angle - 90.0) % 360.0

        start_offset = (90.0 - self.start_angle_deg) % 360.0
        normalized = (normalized - start_offset) % 360.0

        return int((normalized + sector_size / 2.0) // sector_size) % len(self.options)

    def _set_current_index(self, new_index: Optional[int]) -> None:
        if new_index == self.current_index:
            return

        self.current_index = new_index
        self._highlight(new_index)

        if self.on_change is None:
            return

        if new_index is None:
            self.on_change(None, None)
        else:
            self.on_change(new_index, self.options[new_index])

    def _highlight(self, index: Optional[int]) -> None:
        for node in self._option_nodes:
            is_selected = node["index"] == index

            node["frame"]["frameColor"] = (
                (0.95, 0.75, 0.15, 0.95) if is_selected else (0.08, 0.08, 0.08, 0.78)
            )
            node["frame"].setScale(
                self.selected_scale if is_selected else self.unselected_scale
            )
            node["label"]["text_fg"] = (
                (0.08, 0.08, 0.08, 1.0) if is_selected else (1.0, 1.0, 1.0, 1.0)
            )

            if node["icon"] is not None:
                node["icon"].setColorScale(
                    (1.0, 1.0, 1.0, 1.0) if is_selected else (0.9, 0.9, 0.9, 1.0)
                )

if __name__ == '__main__':
    from direct.showbase.ShowBase import ShowBase
    from mouseHandler import Mouse
    # from radialMenu import RadialMenu


    class App(ShowBase):
        def __init__(self):
            super().__init__()

            self.mouse_handler = Mouse(self)

            self.menu = RadialMenu(
                base=self,
                mouse=self.mouse_handler,
                name="Emotes",
                options=[
                    ("Wave", None),
                    ("Thumbs up", None),
                    ("Dance", None),
                    ("Sit", None),
                ],
                deadzone_enter_px=80,
                deadzone_leave_px=60,
                start_angle_deg=90.0,
                clockwise=True,
                open_event="tab",
                close_event="tab-up",
                on_select=self.on_select,
                on_change=self.on_change,
                on_cancel=self.on_cancel,
            )

        def on_select(self, index, option):
            print("SELECT", index, option.text)

        def on_change(self, index, option):
            print("CHANGE", index, option.text if option else None)

        def on_cancel(self):
            print("CANCEL")


    app = App()
    app.run()