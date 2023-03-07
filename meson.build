project(
    'caffeine-ng',
    version: '4.1.0',
    meson_version: '>=0.63.0',
    default_options: [
      # The default can yield broken results.
      'python.install_env=auto'
    ]
)

dependency('pygobject-3.0')
dependency('dbus-python')
dependency('gtk+-3.0')
dependency('libnotify')
ayatana_appindicator = dependency('ayatana-appindicator3-0.1', required: false)
appindicator = dependency('appindicator3-0.1', required: false)
dependency('libxfconf-0', required: false)

if not (ayatana_appindicator.found() or appindicator.found())
  error('At least on of these is required:', appindicator.name(), ayatana_appindicator.name())
endif

pymod = import('python')
python = pymod.find_installation('python3',
  modules: ['click', 'ewmh', 'setproctitle', 'pulsectl']
)
python.dependency()

git = find_program('git', required: true)

prefix = get_option('prefix')
pkgdatadir = join_paths(prefix, get_option('datadir'))

conf_data = configuration_data({
  'localedir': join_paths(prefix, get_option('localedir')),
  'pkgdatadir': pkgdatadir,
})

paths_py = configure_file(
    input: 'caffeine/paths.py',
    output: 'paths.py',
    configuration: conf_data,
)

# Cannot use vcs_tag; that file cannot be installed.
# See: https://github.com/mesonbuild/meson/issues/4893
version_py = configure_file(
    input: 'caffeine/version.py',
    output: 'version.py',
    configuration: configuration_data({
      'VCS_TAG': run_command(
        git, 'describe', '--long', '--tags', '--dirty', '--always',
        check: true
      ).stdout().strip()
    }),
)

py_sources = [
    'caffeine/__init__.py',
    'caffeine/__main__.py',
    'caffeine/applicationinstance.py',
    'caffeine/cli.py',
    'caffeine/core.py',
    'caffeine/icons.py',
    'caffeine/inhibitors.py',
    'caffeine/main.py',
    paths_py,  # Is patched with locations.
    'caffeine/procmanager.py',
    'caffeine/triggers.py',
    'caffeine/utils.py',
    version_py,  # Is patched with VCS version.
]
python.install_sources(py_sources,
  subdir: 'caffeine',
)

configure_file(
  input: 'bin/caffeine',
  output: 'caffeine',
  configuration: configuration_data({
    'PYTHON': python.full_path()
  }),
  install_mode: 'rwxr-xr-x',
  install_dir: get_option('bindir'),
)

install_data(
  'share/applications/caffeine.desktop',
  install_dir: '/etc/xdg/autostart',
)

install_data(
  'share/applications/caffeine.desktop',
  install_dir: join_paths(pkgdatadir, 'applications'),
)

subdir('translations')

scdoc = dependency('scdoc', required: true, version: '>= 1.9.7')
mandir = get_option('mandir')
custom_target(
	'caffeine.1',
	input: 'caffeine.1.scd',
	output: 'caffeine.1',
	command: scdoc.get_variable('scdoc'),
	feed: true,
	capture: true,
	install: true,
	install_dir: join_paths(mandir, 'man1/caffeine')
)

install_subdir('caffeine/assets/glade',
  install_dir: join_paths(pkgdatadir, 'caffeine/glade'),
  strip_directory: true,
)

install_subdir('caffeine/assets/images',
  install_dir: join_paths(pkgdatadir, 'caffeine/images'),
  strip_directory: true,
)

install_subdir('caffeine/assets/icons',
  install_dir: join_paths(pkgdatadir, 'icons'),
  strip_directory: true,
)

install_data(
  'share/glib-2.0/schemas/net.launchpad.caffeine.gschema.xml',
  install_dir: join_paths(pkgdatadir, 'glib-2.0/schemas/'),
)

install_data(
  './share/pixmaps/caffeine.png',
  install_dir: join_paths(pkgdatadir, 'pixmaps'),
)
