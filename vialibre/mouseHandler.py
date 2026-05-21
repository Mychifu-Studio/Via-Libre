from panda3d.core import WindowProperties
from direct.showbase.ShowBase import ShowBase


class Mouse():
    def __init__(self, base: ShowBase):
        self.base = base

        self.show = self.releaseMouse
        self.hide = self.captureMouse


    def captureMouse(self):
        properties = WindowProperties()
        properties.set_cursor_hidden(True)
        self.base.win.requestProperties(properties)


    def releaseMouse(self):
        properties = WindowProperties()
        properties.set_cursor_hidden(True)
        self.base.win.requestProperties(properties)


    def centerMouse(self):
        centerX = self.base.win.getXSize() // 2
        centerY = self.base.win.getYSize() // 2
        self.base.win.movePointer(0, centerX, centerY)


    def getMouseDelta(self) -> tuple[int, int]:
        md = self.base.win.getPointer(0)
        x = md.getX()
        y = md.getY()
       
        centerX = self.base.win.getXSize() // 2
        centerY = self.base.win.getYSize() // 2
       
        # Calcul des deltas en pixels
        dx = x - centerX
        dy = y - centerY


        return (dx, dy)


    def hasMouse(self) -> bool:
        return self.base.mouseWatcherNode.hasMouse()