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
  add_languages('c', 'fortran', native : false, required : true)

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

  mesasdk_rpaths = []
  if host_machine.system() == 'darwin' and mesasdk_root != ''
    mesasdk_rpaths = [mesasdk_root]
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
  mesa_profile_inputs_source = files('src/pyfortmesa/fortran/common/mesa_profile_inputs.f90')
  mesa_eos_source = files('src/pyfortmesa/fortran/eos/mesa_eos_public.f90')
  mesa_kap_source = files('src/pyfortmesa/fortran/kap/mesa_kap_public.f90')

  mesa_pkg_config_check = run_command(
    py,
    [mesa_pkg_config_helper, 'path'],
    check : false,
  )
  if mesa_pkg_config_check.returncode() != 0
    mesa_pkg_config_error = mesa_pkg_config_check.stderr().strip()
    if mesa_pkg_config_error == ''
      mesa_pkg_config_error = mesa_pkg_config_check.stdout().strip()
    endif
    error(mesa_pkg_config_error)
  endif

  fortranobject_source = incdir_f2py / 'fortranobject.c'
  mesa_base_link_args = darwin_arch_args
  mesa_wrapper_specs = [
    {
      'name' : '_mesa_const',
      'source' : mesa_const_source,
      'extra_sources' : [],
      'pkg_config' : ['mesa-const'],
      'symbols' : ['mesa_const_values'],
      'extra_outputs' : [],
      'fortran_extra_args' : [],
    },
    {
      'name' : '_mesa_chem',
      'source' : mesa_chem_source,
      'extra_sources' : [],
      'pkg_config' : ['mesa-chem'],
      'symbols' : [
        'mesa_chem_composition_info',
        'mesa_chem_composition_info_full',
        'mesa_chem_shutdown',
      ],
      'extra_outputs' : [],
      'fortran_extra_args' : [],
    },
    {
      'name' : '_mesa_eos',
      'source' : mesa_eos_source,
      'extra_sources' : [mesa_profile_inputs_source],
      'pkg_config' : ['mesa-eos'],
      'symbols' : [
        'mesa_eos_sample_composition',
        'mesa_eos_composition',
        'mesa_eos_composition_full',
        'mesa_eos_profile',
        'mesa_eos_profile_from_logs',
        'mesa_eos_solve_rho',
        'mesa_eos_solve_rho_profile',
        'mesa_eos_solve_t',
        'mesa_eos_solve_t_profile',
        'mesa_eos_shutdown',
      ],
      'extra_outputs' : ['_mesa_eos-f2pywrappers2.f90'],
      'fortran_extra_args' : mesasdk_openmp_args,
    },
    {
      'name' : '_mesa_kap',
      'source' : mesa_kap_source,
      'extra_sources' : [mesa_profile_inputs_source],
      'pkg_config' : ['mesa-kap', 'mesa-eos'],
      'symbols' : [
        'mesa_kap_sample_composition',
        'mesa_kap_composition',
        'mesa_kap_composition_full',
        'mesa_kap_composition_with_controls',
        'mesa_kap_composition_full_with_controls',
        'mesa_eos_kap_composition_with_controls',
        'mesa_kap_profile',
        'mesa_kap_profile_from_logs',
        'mesa_eos_kap_profile',
        'mesa_eos_kap_profile_from_logs',
        'mesa_kap_shutdown',
      ],
      'extra_outputs' : ['_mesa_kap-f2pywrappers2.f90'],
      'fortran_extra_args' : mesasdk_openmp_args,
    },
  ]

  foreach wrapper_spec : mesa_wrapper_specs
    module_name = wrapper_spec['name']
    module_source = wrapper_spec['source']
    pkg_config_packages = wrapper_spec['pkg_config']
    mesa_cflags = run_command(
      py,
      [mesa_pkg_config_helper, 'cflags'] + pkg_config_packages,
      check : true,
    ).stdout().strip().split()
    mesa_link_args = run_command(
      py,
      [mesa_pkg_config_helper, 'link-args'] + pkg_config_packages,
      check : true,
    ).stdout().strip().split()
    mesa_rpaths = run_command(
      py,
      [mesa_pkg_config_helper, 'rpaths'] + pkg_config_packages,
      check : true,
    ).stdout().strip().split()
    mesa_rpath = ':'.join(mesasdk_rpaths + mesa_rpaths)

    wrapper = custom_target(
      module_name + 'module.c',
      input : [module_source, f2cmap_file],
      output : [
        module_name + 'module.c',
        module_name + '-f2pywrappers.f',
      ] + wrapper_spec['extra_outputs'],
      command : [
        py,
        '-m',
        'numpy.f2py',
        '@INPUT0@',
        'only:',
      ] + wrapper_spec['symbols'] + [
        ':',
        '-m',
        module_name,
        '--lower',
        '--f2cmap',
        '@INPUT1@',
      ],
    )

    py.extension_module(
      module_name,
      wrapper_spec['extra_sources'] + [
        module_source,
        wrapper,
        fortranobject_source,
      ],
      dependencies : [np_dep, f2py_dep],
      c_args : darwin_arch_args + mesa_cflags,
      fortran_args : darwin_arch_args + mesa_cflags + wrapper_spec['fortran_extra_args'],
      link_args : mesa_base_link_args + mesa_link_args + mesasdk_openmp_libs,
      build_rpath : mesa_rpath,
      install_rpath : mesa_rpath,
      subdir : 'pyfortmesa',
      install : true,
    )
  endforeach
endif

py.install_sources(
  'src/pyfortmesa/__init__.py',
  'src/pyfortmesa/__main__.py',
  'src/pyfortmesa/mesa.py',
  'src/pyfortmesa/mesa_support.py',
  subdir : 'pyfortmesa',
)
