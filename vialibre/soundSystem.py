from direct.showbase.ShowBase import ShowBase
# from direct.showbase.Audio3DManager import Audio3DManager

from random import randint

class SoundEngine():
    def __init__(self, base):
        self.base: ShowBase = base
        self.sfxs = dict()
        
        self.addSFX("gunshot", "assets/SFX/gunshot.wav")
    
    def addSFX(self, name: str, path: str):
        exec(f'self.{name} = self.base.loader.loadSfx("{path}")')
        exec(f'self.sfxs[name] = self.{name}')
    
    def setVol(self, sfx: str):
        ...
        
    def setPan(self, sfx: str):
        ...
        
    def play(self, sfx: str, randomize: tuple[int, int] | None = None):
        if not sfx in self.sfxs: return
        
        if self.sfxs[sfx].status() == self.sfxs[sfx].PLAYING: self.sfxs[sfx].stop()
        if randomize: self.sfxs[sfx].setPlayRate(randint(*randomize)/100)
        self.sfxs[sfx].play()