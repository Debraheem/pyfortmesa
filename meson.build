project(
  'pyfortmesa',
  'c',
  'fortran',
  version : '0.3.1',
  license : 'LGPL-3.0-only',
  meson_version : '>=1.1.0',
  default_options : ['warning_level=2'],
)

py = import('python').find_installation(pure: false)
np_dep = dependency('numpy')

incdir_f2py = run_command(
  py,
  ['-c', 'import numpy.f2py; print(numpy.f2py.get_include())'],
  check : true,
).stdout().strip()

f2py_dep = declare_dependency(
  include_directories : incdir_f2py,
)

fortran_const_source = files('src/pyfortmesa/fortran/const_def.f90')
fortran_calc_source = files('src/pyfortmesa/fortran/small_calc.f90')
f2cmap_file = files('f2py_f2cmap')

fortran_wrapper = custom_target(
  '_fortran_calcmodule.c',
  input : [fortran_calc_source, f2cmap_file],
  output : [
    '_fortran_calcmodule.c',
    '_fortran_calc-f2pywrappers.f',
  ],
  command : [
    py,
    '-m',
    'numpy.f2py',
    '@INPUT0@',
    '-m',
    '_fortran_calc',
    '--lower',
    '--f2cmap',
    '@INPUT1@',
  ],
)

py.extension_module(
  '_fortran_calc',
  [
    fortran_const_source,
    fortran_calc_source,
    fortran_wrapper,
    incdir_f2py / 'fortranobject.c',
  ],
  dependencies : [np_dep, f2py_dep],
  subdir : 'pyfortmesa',
  install : true,
)

py.install_sources(
  'src/pyfortmesa/__init__.py',
  'src/pyfortmesa/__main__.py',
  'src/pyfortmesa/calc.py',
  'src/pyfortmesa/fortran_calc.py',
  subdir : 'pyfortmesa',
)
