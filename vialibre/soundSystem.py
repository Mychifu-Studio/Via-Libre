from direct.showbase.ShowBase import ShowBase
# from direct.showbase.Audio3DManager import Audio3DManager

from random import randint

class SoundEngine():
    def __init__(self, base):
        self.base: ShowBase = base
        self.sfxs = dict()
        self.loops = dict()
        self.songs = dict()
        
        self.addSong("pigstep", "assets/music/pigstep.flac")
        self.setVol("pigstep", .1) # Le master est très LOUD
        self.loop("pigstep")
        
        self.addSFX("gunshot", "assets/SFX/gunshot.wav")
        self.addSFX("turret", "assets/SFX/turret_fire.wav")
        self.addSFX("turret_reload", "assets/SFX/turret_reload.wav")
        self.setVol("turret_reload", .1)
        for i in range(1, 11):
            self.addSFX(f"step{i}", f"assets/SFX/step{i}.wav")
            self.setVol(f"step{i}", .1)
            
        self.walk = [f"step{i}" for i in range(1, 11)]
    
    def addSong(self, name: str, path: str):
        song = self.base.loader.loadMusic(path)
        self.songs[name] = song
        
        setattr(self, name, song)
        
    def addSFX(self, name: str, path: str):
        sound = self.base.loader.loadSfx(path)
        self.sfxs[name] = sound
        
        setattr(self, name, sound)
    
    def setVol(self, name: str, value: float):
        if name in self.sfxs:
            self.sfxs[name].setVolume(value)
        if name in self.songs:
            self.songs[name].setVolume(value)
        
    def setPan(self, name: str):
        ...
        
    def play(self, sfx: str, randomize: tuple[int, int] | None = None):
        if not sfx in self.sfxs: return
        
        if self.sfxs[sfx].status() == self.sfxs[sfx].PLAYING: self.sfxs[sfx].stop()
        if randomize: self.sfxs[sfx].setPlayRate(randint(*randomize)/100)
        self.sfxs[sfx].play()
        
    def loopSFX(self, sfx_list: list[str], delay_range: tuple[float, float] = (0.0, 0.0), randomize: tuple[int, int] | None = None):
        valid = [s for s in sfx_list if s in self.sfxs]
        if not valid:
            return

        key = "|".join(sorted(valid))
        if self.loops.get(key, False):
            return

        self.loops[key] = True
        self._loop_step(key, valid, delay_range, randomize)

    def _loop_step(self, key, valid, delay_range, randomize):
        if not self.loops.get(key, False):
            return

        sfx = valid[randint(0, len(valid) - 1)]
        self.play(sfx, randomize=randomize)

        delay = randint(int(delay_range[0] * 1000), int(delay_range[1] * 1000)) / 1000
        self.base.taskMgr.doMethodLater(
            delay,
            self._loop_step_task,
            f"loop_{key}",
            extraArgs=[key, valid, delay_range, randomize],
            appendTask=True
        )

    def _loop_step_task(self, key, valid, delay_range, randomize, task):
        self._loop_step(key, valid, delay_range, randomize)
        return task.done

    def loop(self, name: str):
        if name in self.songs:
            self.songs[name].setLoop(True)
            self.songs[name].play()
            
    def stop(self, name: str):
        if name in self.songs:
            self.songs[name].stop()

    def stopSFX(self, sfx_list: list[str]):
        valid = [s for s in sfx_list if s in self.sfxs]
        if not valid:
            return

        key = "|".join(sorted(valid))
        self.loops[key] = False

        self.base.taskMgr.remove(f"loop_{key}")

        for sfx in valid:
            self.sfxs[sfx].stop()