from panda3d.core import WindowProperties
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject

from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib
from direct.interval.IntervalGlobal import LerpScaleInterval
from panda3d.core import NodePath


class Mouse(DirectObject):
    def __init__(self, base: ShowBase):
        self.base = base

        self.createCursor()

    def createCursor(self):
        self.cursorRoot = NodePath("cursorRoot")
        self.cursorRoot.reparentTo(self.base.aspect2d)
        self.cursorRoot.setBin("gui-popup", 100)
        self.cursorRoot.setDepthTest(False)
        self.cursorRoot.setDepthWrite(False)

        self.cursor = OnscreenImage(image='./assets/cursor_resized.png', parent=self.cursorRoot)
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)
        self.cursor.setPos(1, 0, -1)

        scale = (0.04, 1, 0.04)
        scale_anim = (0.03, 1, 0.03)
        self.cursorRoot.setScale(*scale)

        self.cursorScaleDown = LerpScaleInterval(self.cursorRoot, duration=0.05, scale=scale_anim, startScale=scale)
        self.cursorScaleUp  = LerpScaleInterval(self.cursorRoot, duration=0.1,  scale=scale,      startScale=scale_anim)

        self.accept('mouse1',    self.cursorScaleDown.start)
        self.accept('mouse1-up', self.cursorScaleUp.start)

    def hideCursor(self):
        self.cursor.hide()

    def showCursor(self):
        self.cursor.show()

    def captureMouse(self):
        if not hasattr(self.base.win, "requestProperties"):
            return

        properties = WindowProperties()
        properties.set_cursor_hidden(True)
        self.base.win.requestProperties(properties)


    def releaseMouse(self):
        if not hasattr(self.base.win, "requestProperties"):
            return

        properties = WindowProperties()
        properties.set_cursor_hidden(True)
        self.base.win.requestProperties(properties)


    def centerMouse(self):
        if not hasattr(self.base.win, "movePointer"):
            return

        centerX = self.base.win.getXSize() // 2
        centerY = self.base.win.getYSize() // 2
        self.base.win.movePointer(0, centerX, centerY)

    def getMousePos(self):
        if not hasattr(self.base.win, "getPointer"):
            return 0, 0

        md = self.base.win.getPointer(0)
        x = md.getX()
        y = md.getY()
        return x, y

    def setMousePos(self, coords):
        if not hasattr(self.base.win, "movePointer"):
            return

        self.base.win.movePointer(0, int(coords[0]), int(coords[1]))

    def getMouseDelta(self) -> tuple[int, int]:
        x, y = self.getMousePos()

        centerX = self.base.win.getXSize() // 2
        centerY = self.base.win.getYSize() // 2

        # Calcul des deltas en pixels
        dx = x - centerX
        dy = y - centerY

        return (dx, dy)

    def hasMouse(self) -> bool:
        mouse_watcher = getattr(self.base, "mouseWatcherNode", None)
        return mouse_watcher is not None and mouse_watcher.hasMouse()

    def updateCursor(self):
        if getattr(self.base, 'win', None) is None:
            return
        mouse_watcher = getattr(self.base, "mouseWatcherNode", None)
        if mouse_watcher is None:
            return

        if mouse_watcher.hasMouse():
            x = mouse_watcher.getMouseX()
            y = mouse_watcher.getMouseY()
            ratio = self.base.getAspectRatio()
            self.cursorRoot.setPos(x * ratio, 0, y)
