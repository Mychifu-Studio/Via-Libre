from setuptools import setup

setup(
    name='MultiplayerDemo',
    options={
        'build_apps': {
            'console_apps': {
                'MultiplayerDemo': 'main.py'
            },

            'include_patterns': [
                './assets/dog.bam',
                './assets/crosshair.png',
                './assets/cursor_resized.png',
                './assets/Turrets/*'
            ],

            # Force l'inclusion des modules locaux du projet
            'include_modules': {
                '*': [
                    'vialibre.player',
                    'vialibre.multiplayer',
                    'vialibre.camera',
                    'vialibre.mouseHandler',
                    'vialibre.construction',
                    'vialibre.interaction',
                    'websocket',
                ]
            },

            # Exclut les modules optionnels introuvables de websocket-client
            'exclude_modules': {
                '*': [
                    'python_socks._errors',
                    'python_socks._types',
                    'python_socks.sync',
                    'wsaccel.utf8validator',
                    'wsaccel.xormask',
                    '_bootlocale',
                    '_posixsubprocess',
                    'grp',
                    '_scproxy',  # Module macOS, inutile sur Windows
                ]
            },

            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],

            'platforms': [
                'win_amd64',
            ],
        },

        'bdist_apps': {
            'installers': {
                'win_amd64': 'zip'
            },
        },
    }
)