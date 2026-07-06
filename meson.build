project(
  'pyfortmesa',
  version : '0.4.0',
  license : 'LGPL-3.0-only',
  meson_version : '>=1.1.0',
  default_options : ['warning_level=2'],
)

with_mesa = get_option('with_mesa')
py = import('python').find_installation(pure: not with_mesa)

if with_mesa
  add_languages('c', 'fortran', required : true)

  np_dep = dependency('numpy')

  incdir_f2py = run_command(
    py,
    ['-c', 'import numpy.f2py; print(numpy.f2py.get_include())'],
    check : true,
  ).stdout().strip()

  f2py_dep = declare_dependency(
    include_directories : incdir_f2py,
  )

  python_arch = run_command(
    py,
    ['-c', 'import platform; print(platform.machine())'],
    check : true,
  ).stdout().strip()

  darwin_arch_args = []
  if host_machine.system() == 'darwin' and python_arch in ['arm64', 'x86_64']
    darwin_arch_args = ['-arch', python_arch]
  endif

  mesasdk_root = run_command(
    py,
    [
      '-c',
      'import os; print(os.environ.get("MESASDK_ROOT", "/Applications/mesasdk"))',
    ],
    check : true,
  ).stdout().strip()

  mesasdk_rpath_args = []
  if host_machine.system() == 'darwin' and mesasdk_root != ''
    mesasdk_rpath_args = ['-Wl,-rpath,' + mesasdk_root]
  endif

  mesasdk_openmp_libs = []
  mesasdk_openmp_args = []
  if host_machine.system() == 'darwin' and mesasdk_root != ''
    mesasdk_lib_dir = mesasdk_root / 'lib'
    mesasdk_openmp_libs = ['-L' + mesasdk_lib_dir, '-lgomp']
    mesasdk_openmp_args = ['-fopenmp']
  endif

  f2cmap_file = files('tools/f2py_f2cmap')
  tools_dir = meson.current_source_dir() / 'tools'
  mesa_pkg_config_helper = tools_dir / 'mesa_pkg_config.py'
  mesa_const_source = files('src/pyfortmesa/fortran/const/mesa_const_public.f90')
  mesa_chem_source = files('src/pyfortmesa/fortran/chem/mesa_chem_public.f90')
  mesa_eos_source = files('src/pyfortmesa/fortran/eos/mesa_eos_public.f90')
  mesa_kap_source = files('src/pyfortmesa/fortran/kap/mesa_kap_public.f90')

  mesa_const_cflags = run_command(
    py,
    [mesa_pkg_config_helper, 'cflags', 'mesa-const'],
    check : true,
  ).stdout().strip().split()

  mesa_const_libs = run_command(
    py,
    [mesa_pkg_config_helper, 'libs', 'mesa-const'],
    check : true,
  ).stdout().strip().split()

  mesa_chem_cflags = run_command(
    py,
    [mesa_pkg_config_helper, 'cflags', 'mesa-chem'],
    check : true,
  ).stdout().strip().split()

  mesa_chem_libs = run_command(
    py,
    [mesa_pkg_config_helper, 'libs', 'mesa-chem'],
    check : true,
  ).stdout().strip().split()

  mesa_eos_cflags = run_command(
    py,
    [mesa_pkg_config_helper, 'cflags', 'mesa-eos'],
    check : true,
  ).stdout().strip().split()

  mesa_eos_libs = run_command(
    py,
    [mesa_pkg_config_helper, 'libs', 'mesa-eos'],
    check : true,
  ).stdout().strip().split()

  mesa_kap_cflags = run_command(
    py,
    [mesa_pkg_config_helper, 'cflags', 'mesa-kap', 'mesa-eos'],
    check : true,
  ).stdout().strip().split()

  mesa_kap_libs = run_command(
    py,
    [mesa_pkg_config_helper, 'libs', 'mesa-kap', 'mesa-eos'],
    check : true,
  ).stdout().strip().split()

  mesa_const_link_args = darwin_arch_args + mesasdk_rpath_args
  mesa_const_link_args += mesa_const_libs
  mesa_const_link_args += mesasdk_openmp_libs

  mesa_chem_link_args = darwin_arch_args + mesasdk_rpath_args
  mesa_chem_link_args += mesa_chem_libs
  mesa_chem_link_args += mesasdk_openmp_libs

  mesa_eos_link_args = darwin_arch_args + mesasdk_rpath_args
  mesa_eos_link_args += mesa_eos_libs
  mesa_eos_link_args += mesasdk_openmp_libs

  mesa_kap_link_args = darwin_arch_args + mesasdk_rpath_args
  mesa_kap_link_args += mesa_kap_libs
  mesa_kap_link_args += mesasdk_openmp_libs

  mesa_const_wrapper = custom_target(
    '_mesa_constmodule.c',
    input : [mesa_const_source, f2cmap_file],
    output : [
      '_mesa_constmodule.c',
      '_mesa_const-f2pywrappers.f',
    ],
    command : [
      py,
      '-m',
      'numpy.f2py',
      '@INPUT0@',
      'only:',
      'mesa_const_values',
      ':',
      '-m',
      '_mesa_const',
      '--lower',
      '--f2cmap',
      '@INPUT1@',
    ],
  )

  py.extension_module(
    '_mesa_const',
    [
      mesa_const_source,
      mesa_const_wrapper,
      incdir_f2py / 'fortranobject.c',
    ],
    dependencies : [np_dep, f2py_dep],
    c_args : darwin_arch_args + mesa_const_cflags,
    fortran_args : darwin_arch_args + mesa_const_cflags,
    link_args : mesa_const_link_args,
    subdir : 'pyfortmesa',
    install : true,
  )

  mesa_chem_wrapper = custom_target(
    '_mesa_chemmodule.c',
    input : [mesa_chem_source, f2cmap_file],
    output : [
      '_mesa_chemmodule.c',
      '_mesa_chem-f2pywrappers.f',
    ],
    command : [
      py,
      '-m',
      'numpy.f2py',
      '@INPUT0@',
      'only:',
      'mesa_chem_composition_info',
      'mesa_chem_shutdown',
      ':',
      '-m',
      '_mesa_chem',
      '--lower',
      '--f2cmap',
      '@INPUT1@',
    ],
  )

  py.extension_module(
    '_mesa_chem',
    [
      mesa_chem_source,
      mesa_chem_wrapper,
      incdir_f2py / 'fortranobject.c',
    ],
    dependencies : [np_dep, f2py_dep],
    c_args : darwin_arch_args + mesa_chem_cflags,
    fortran_args : darwin_arch_args + mesa_chem_cflags,
    link_args : mesa_chem_link_args,
    subdir : 'pyfortmesa',
    install : true,
  )

  mesa_eos_wrapper = custom_target(
    '_mesa_eosmodule.c',
    input : [mesa_eos_source, f2cmap_file],
    output : [
      '_mesa_eosmodule.c',
      '_mesa_eos-f2pywrappers.f',
      '_mesa_eos-f2pywrappers2.f90',
    ],
    command : [
      py,
      '-m',
      'numpy.f2py',
      '@INPUT0@',
      'only:',
      'mesa_eos_sample_composition',
      'mesa_eos_composition',
      'mesa_eos_composition_full',
      'mesa_eos_profile_from_logs',
      'mesa_eos_solve_rho',
      'mesa_eos_solve_t',
      'mesa_eos_shutdown',
      ':',
      '-m',
      '_mesa_eos',
      '--lower',
      '--f2cmap',
      '@INPUT1@',
    ],
  )

  py.extension_module(
    '_mesa_eos',
    [
      mesa_eos_source,
      mesa_eos_wrapper,
      incdir_f2py / 'fortranobject.c',
    ],
    dependencies : [np_dep, f2py_dep],
    c_args : darwin_arch_args + mesa_eos_cflags,
    fortran_args : darwin_arch_args + mesa_eos_cflags + mesasdk_openmp_args,
    link_args : mesa_eos_link_args,
    subdir : 'pyfortmesa',
    install : true,
  )

  mesa_kap_wrapper = custom_target(
    '_mesa_kapmodule.c',
    input : [mesa_kap_source, f2cmap_file],
    output : [
      '_mesa_kapmodule.c',
      '_mesa_kap-f2pywrappers.f',
      '_mesa_kap-f2pywrappers2.f90',
    ],
    command : [
      py,
      '-m',
      'numpy.f2py',
      '@INPUT0@',
      'only:',
      'mesa_kap_sample_composition',
      'mesa_kap_composition',
      'mesa_kap_composition_full',
      'mesa_kap_composition_with_controls',
      'mesa_kap_composition_full_with_controls',
      'mesa_kap_profile_from_logs',
      'mesa_eos_kap_profile_from_logs',
      'mesa_kap_shutdown',
      ':',
      '-m',
      '_mesa_kap',
      '--lower',
      '--f2cmap',
      '@INPUT1@',
    ],
  )

  py.extension_module(
    '_mesa_kap',
    [
      mesa_kap_source,
      mesa_kap_wrapper,
      incdir_f2py / 'fortranobject.c',
    ],
    dependencies : [np_dep, f2py_dep],
    c_args : darwin_arch_args + mesa_kap_cflags,
    fortran_args : darwin_arch_args + mesa_kap_cflags + mesasdk_openmp_args,
    link_args : mesa_kap_link_args,
    subdir : 'pyfortmesa',
    install : true,
  )
endif

py.install_sources(
  'src/pyfortmesa/__init__.py',
  'src/pyfortmesa/__main__.py',
  'src/pyfortmesa/mesa.py',
  'src/pyfortmesa/mesa_support.py',
  subdir : 'pyfortmesa',
)
