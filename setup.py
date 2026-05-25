from setuptools import setup, find_packages

setup(
    name='ViaLibre',
    version='1.0.0',
    description='¡Via Libre! est un Action Tower Defense prenant place dans la povince de Valparaiso.',
    author='Mychifu Studio',
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    install_requires=[
        'panda3d',
    ],
    options={
        'build_apps': {
            'gui_apps': {
                'ViaLibre': 'main.py',
            },

            'include_patterns': [
                'assets/**',
                'vialibre/**',
                '*.png',
                '*.jpg',
                '*.ogg',
                '*.wav',
                '*.egg',
                '*.bam',
                '*.txt',
                '*.json',
                'assets/Tony_run.bam',
                'assets/Shop.bam',
                'assets/quest_guy.bam',
                'assets/bartender.bam',
            ],

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
                    '_scproxy',
                ]
            },

            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],

            'platforms': [
                'win_amd64',
            ],
            
            'log_filename': '$USER_APPDATA/ViaLibre/log/output.log',
            'log_append': False,
        },

        'bdist_apps': {
            'installers': {
                'win_amd64': 'zip',
            },
        },
    },

    zip_safe=False,
)