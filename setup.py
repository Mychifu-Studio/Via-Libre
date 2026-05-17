from setuptools import setup

setup(
    name='SimplePlayerDemo',
    options={
        'build_apps': {
            # Build asteroids.exe as a GUI application
            'gui_apps': {
                'SimplePlayerDemo': 'main.py',
            },

            # Set up output logging, important for GUI apps!
            'log_filename': '$USER_APPDATA/SimplePlayerDemo/output.log',
            'log_append': False,

            # Specify which files are included with the distribution
            'include_patterns': [
                './assets/dog.bam'
            ],

            # Include the OpenGL renderer and OpenAL audio plug-in
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