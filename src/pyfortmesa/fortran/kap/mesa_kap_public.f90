module pyfortmesa_kap_state
   use chem_def, only: ih1, ihe4, ic12, in14, io16, ine20, img24, &
      num_chem_isos
   use chem_lib, only: chem_init
   use const_def, only: dp
   use const_lib, only: const_init
   use eos_def, only: i_eta, i_lnfree_e, num_eos_basic_results, &
      num_eos_d_dxa_results
   use eos_lib, only: alloc_eos_handle, alloc_eos_handle_using_inlist, &
      eosDT_get, eos_init, eos_shutdown, free_eos_handle
   use kap_def, only: Kap_General_Info, num_kap_fracs
   use kap_lib, only: alloc_kap_handle, alloc_kap_handle_using_inlist, &
      kap_get, kap_init, kap_ptr, kap_shutdown, free_kap_handle
   use math_lib, only: math_init

   implicit none

   integer, parameter :: sample_species = 7
   integer, parameter :: sample_h1 = 1
   integer, parameter :: sample_he4 = 2
   integer, parameter :: sample_c12 = 3
   integer, parameter :: sample_n14 = 4
   integer, parameter :: sample_o16 = 5
   integer, parameter :: sample_ne20 = 6
   integer, parameter :: sample_mg24 = 7

   integer, save :: eos_handle_store = -1
   integer, save :: kap_handle_store = -1
   logical, save :: base_started = .false.
   logical, save :: eos_started = .false.
   logical, save :: kap_started = .false.
   logical, save :: kap_defaults_loaded = .false.
   logical, save :: default_use_type2_opacities = .false.
   logical, save :: default_use_zbase_for_type1 = .true.
   real(dp), save :: default_zbase = -1.0_dp
   real(dp), save :: default_type2_full_off_x = 1.0e-3_dp
   real(dp), save :: default_type2_full_on_x = 1.0e-6_dp
   real(dp), save :: default_type2_full_off_dz = 1.0e-3_dp
   real(dp), save :: default_type2_full_on_dz = 1.0e-2_dp

contains

   subroutine ensure_kap_handles(eos_handle, kap_handle, ierr)
      integer, intent(out) :: eos_handle
      integer, intent(out) :: kap_handle
      integer, intent(out) :: ierr

      character(len=1024) :: inlist_path
      logical :: has_inlist

      ierr = 0
      eos_handle = eos_handle_store
      kap_handle = kap_handle_store

      if (.not. base_started) then
         call math_init()
         call const_init(' ', ierr)
         if (ierr /= 0) return
         call chem_init('isotopes.data', ierr)
         if (ierr /= 0) return
         base_started = .true.
      end if

      if (.not. eos_started) then
         call eos_init(' ', .true., ierr)
         if (ierr /= 0) return
         eos_started = .true.
      end if

      if (eos_handle_store <= 0) then
         call get_shared_inlist(inlist_path, has_inlist)
         if (has_inlist) then
            eos_handle_store = alloc_eos_handle_using_inlist( &
               trim(inlist_path), ierr)
         else
            eos_handle_store = alloc_eos_handle(ierr)
         end if
         if (ierr /= 0) return
      end if

      if (.not. kap_started) then
         call kap_init(.false., ' ', ierr)
         if (ierr /= 0) return
         kap_started = .true.
      end if

      if (kap_handle_store <= 0) then
         call get_shared_inlist(inlist_path, has_inlist)
         if (has_inlist) then
            kap_handle_store = alloc_kap_handle_using_inlist( &
               trim(inlist_path), ierr)
         else
            kap_handle_store = alloc_kap_handle(ierr)
         end if
         if (ierr /= 0) return
      end if

      if (.not. kap_defaults_loaded) then
         call store_kap_defaults(kap_handle_store, ierr)
         if (ierr /= 0) return
      end if

      eos_handle = eos_handle_store
      kap_handle = kap_handle_store
   end subroutine ensure_kap_handles


   subroutine get_shared_inlist(inlist_path, has_inlist)
      character(len=*), intent(out) :: inlist_path
      logical, intent(out) :: has_inlist

      integer :: status
      integer :: value_length

      inlist_path = ' '
      call get_environment_variable( &
         'PYFORTMESA_INLIST', inlist_path, length=value_length, status=status)
      has_inlist = (status == 0 .and. value_length > 0)
   end subroutine get_shared_inlist


   subroutine shutdown_kap_state(release_tables, ierr)
      logical, intent(in) :: release_tables
      integer, intent(out) :: ierr

      ierr = 0

      if (kap_handle_store > 0) then
         call free_kap_handle(kap_handle_store)
         kap_handle_store = -1
      end if

      if (eos_handle_store > 0) then
         call free_eos_handle(eos_handle_store)
         eos_handle_store = -1
      end if

      if (release_tables) then
         if (kap_started) call kap_shutdown()
         if (eos_started) call eos_shutdown()
         kap_started = .false.
         eos_started = .false.
         base_started = .false.
      end if

      kap_defaults_loaded = .false.

      default_use_type2_opacities = .false.
      default_use_zbase_for_type1 = .true.
      default_zbase = -1.0_dp
      default_type2_full_off_x = 1.0e-3_dp
      default_type2_full_on_x = 1.0e-6_dp
      default_type2_full_off_dz = 1.0e-3_dp
      default_type2_full_on_dz = 1.0e-2_dp
   end subroutine shutdown_kap_state


   subroutine store_kap_defaults(kap_handle, ierr)
      integer, intent(in) :: kap_handle
      integer, intent(out) :: ierr

      type(Kap_General_Info), pointer :: rq

      ierr = 0
      call kap_ptr(kap_handle, rq, ierr)
      if (ierr /= 0) return

      default_zbase = rq%Zbase
      default_use_type2_opacities = rq%use_Type2_opacities
      default_use_zbase_for_type1 = rq%use_Zbase_for_Type1
      default_type2_full_off_x = rq%kap_Type2_full_off_X
      default_type2_full_on_x = rq%kap_Type2_full_on_X
      default_type2_full_off_dz = rq%kap_Type2_full_off_dZ
      default_type2_full_on_dz = rq%kap_Type2_full_on_dZ
      kap_defaults_loaded = .true.
   end subroutine store_kap_defaults


   subroutine setup_sample_net_iso(chem_id_store, net_iso_store)
      integer, intent(out) :: chem_id_store(sample_species)
      integer, intent(out) :: net_iso_store(num_chem_isos)

      chem_id_store = [ih1, ihe4, ic12, in14, io16, ine20, img24]
      net_iso_store(:) = 0
      net_iso_store(ih1) = sample_h1
      net_iso_store(ihe4) = sample_he4
      net_iso_store(ic12) = sample_c12
      net_iso_store(in14) = sample_n14
      net_iso_store(io16) = sample_o16
      net_iso_store(ine20) = sample_ne20
      net_iso_store(img24) = sample_mg24
   end subroutine setup_sample_net_iso


   subroutine setup_net_iso( &
         species, chem_id_values, chem_id_store, net_iso_store, ierr)
      integer, intent(in) :: species
      integer, intent(in) :: chem_id_values(species)
      integer, intent(out) :: chem_id_store(species)
      integer, intent(out) :: net_iso_store(num_chem_isos)
      integer, intent(out) :: ierr

      integer :: i

      ierr = 0
      chem_id_store(:) = chem_id_values(:)
      net_iso_store(:) = 0

      do i = 1, species
         if (chem_id_store(i) <= 0 .or. chem_id_store(i) > num_chem_isos) then
            ierr = -2
            exit
         end if
         if (net_iso_store(chem_id_store(i)) /= 0) then
            ierr = -3
            exit
         end if
         net_iso_store(chem_id_store(i)) = i
      end do
   end subroutine setup_net_iso


   subroutine apply_kap_controls( &
         kap_handle, use_type2_mode, zbase, use_zbase_for_type1_mode, &
         type2_full_off_x, type2_full_on_x, &
         type2_full_off_dz, type2_full_on_dz, ierr)
      integer, intent(in) :: kap_handle
      integer, intent(in) :: use_type2_mode
      real(dp), intent(in) :: zbase
      integer, intent(in) :: use_zbase_for_type1_mode
      real(dp), intent(in) :: type2_full_off_x
      real(dp), intent(in) :: type2_full_on_x
      real(dp), intent(in) :: type2_full_off_dz
      real(dp), intent(in) :: type2_full_on_dz
      integer, intent(out) :: ierr

      type(Kap_General_Info), pointer :: rq

      ierr = 0
      call kap_ptr(kap_handle, rq, ierr)
      if (ierr /= 0) return

      rq%Zbase = default_zbase
      rq%use_Type2_opacities = default_use_type2_opacities
      rq%use_Zbase_for_Type1 = default_use_zbase_for_type1
      rq%kap_Type2_full_off_X = default_type2_full_off_x
      rq%kap_Type2_full_on_X = default_type2_full_on_x
      rq%kap_Type2_full_off_dZ = default_type2_full_off_dz
      rq%kap_Type2_full_on_dZ = default_type2_full_on_dz

      if (use_type2_mode >= 0) then
         rq%use_Type2_opacities = (use_type2_mode /= 0)
      end if
      if (use_zbase_for_type1_mode >= 0) then
         rq%use_Zbase_for_Type1 = (use_zbase_for_type1_mode /= 0)
      end if

      if (zbase >= 0.0_dp) rq%Zbase = zbase
      if (type2_full_off_x >= 0.0_dp) then
         rq%kap_Type2_full_off_X = type2_full_off_x
      end if
      if (type2_full_on_x >= 0.0_dp) then
         rq%kap_Type2_full_on_X = type2_full_on_x
      end if
      if (type2_full_off_dz >= 0.0_dp) then
         rq%kap_Type2_full_off_dZ = type2_full_off_dz
      end if
      if (type2_full_on_dz >= 0.0_dp) then
         rq%kap_Type2_full_on_dZ = type2_full_on_dz
      end if

      if (rq%use_Type2_opacities .and. rq%Zbase <= 0.0_dp) then
         ierr = -5
         return
      end if

      if (rq%kap_Type2_full_off_X > 0.71_dp .or. &
          rq%kap_Type2_full_on_X > 0.71_dp) then
         ierr = -6
         return
      end if

      if (rq%kap_Type2_full_off_X < rq%kap_Type2_full_on_X) then
         ierr = -7
         return
      end if

      if (rq%kap_Type2_full_off_dZ > rq%kap_Type2_full_on_dZ) then
         ierr = -8
         return
      end if
   end subroutine apply_kap_controls


   subroutine evaluate_kap( &
         T, Rho, species, chem_id_values, xa, &
         use_type2_mode, zbase, use_zbase_for_type1_mode, &
         type2_full_off_x, type2_full_on_x, &
         type2_full_off_dz, type2_full_on_dz, &
         kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
      real(dp), intent(in) :: T
      real(dp), intent(in) :: Rho
      integer, intent(in) :: species
      integer, intent(in) :: chem_id_values(species)
      real(dp), intent(in) :: xa(species)
      integer, intent(in) :: use_type2_mode
      real(dp), intent(in) :: zbase
      integer, intent(in) :: use_zbase_for_type1_mode
      real(dp), intent(in) :: type2_full_off_x
      real(dp), intent(in) :: type2_full_on_x
      real(dp), intent(in) :: type2_full_off_dz
      real(dp), intent(in) :: type2_full_on_dz
      real(dp), intent(out) :: kap_fracs(num_kap_fracs)
      real(dp), intent(out) :: kappa
      real(dp), intent(out) :: dlnkap_dlnRho
      real(dp), intent(out) :: dlnkap_dlnT
      real(dp), intent(out) :: dlnkap_dxa(species)
      integer, intent(out) :: ierr

      integer, target :: chem_id_store(species)
      integer, allocatable, target :: net_iso_store(:)
      integer, pointer :: chem_id(:)
      integer, pointer :: net_iso(:)
      integer :: eos_handle
      integer :: kap_handle
      real(dp) :: res(num_eos_basic_results)
      real(dp) :: d_dlnd(num_eos_basic_results)
      real(dp) :: d_dlnT(num_eos_basic_results)
      real(dp) :: d_dxa(num_eos_d_dxa_results, species)

      ierr = 0
      kap_fracs(:) = 0.0_dp
      kappa = 0.0_dp
      dlnkap_dlnRho = 0.0_dp
      dlnkap_dlnT = 0.0_dp
      dlnkap_dxa(:) = 0.0_dp

      if (T <= 0.0_dp .or. Rho <= 0.0_dp) then
         ierr = -9
         return
      end if

      call ensure_kap_handles(eos_handle, kap_handle, ierr)

      if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

      if (ierr == 0) then
         call setup_net_iso(species, chem_id_values, chem_id_store, &
            net_iso_store, ierr)
         chem_id => chem_id_store
         net_iso => net_iso_store
      end if

      if (ierr == 0) then
         call eosDT_get( &
            eos_handle, species, chem_id, net_iso, xa, &
            Rho, log10(Rho), T, log10(T), &
            res, d_dlnd, d_dlnT, d_dxa, ierr)
      end if

      if (ierr == 0) then
         call apply_kap_controls( &
            kap_handle, use_type2_mode, zbase, use_zbase_for_type1_mode, &
            type2_full_off_x, type2_full_on_x, &
            type2_full_off_dz, type2_full_on_dz, ierr)
      end if

      if (ierr == 0) then
         call kap_get( &
            kap_handle, species, chem_id, net_iso, xa, &
            log10(Rho), log10(T), &
            res(i_lnfree_e), d_dlnd(i_lnfree_e), d_dlnT(i_lnfree_e), &
            res(i_eta), d_dlnd(i_eta), d_dlnT(i_eta), &
            kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
      end if

      if (allocated(net_iso_store)) deallocate(net_iso_store)
   end subroutine evaluate_kap

end module pyfortmesa_kap_state


subroutine mesa_kap_sample_composition( &
      T, Rho, xa, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use kap_def, only: num_kap_fracs
   use pyfortmesa_kap_state, only: evaluate_kap, sample_species, &
      setup_sample_net_iso

   implicit none

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   real(dp), intent(in) :: xa(sample_species)
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   integer, intent(out) :: ierr

   integer :: chem_id_store(sample_species)
   integer :: net_iso_dummy(num_chem_isos)
   real(dp) :: kap_fracs(num_kap_fracs)
   real(dp) :: dlnkap_dxa(sample_species)

   ! Keep this legacy sample wrapper for quick checks.
   call setup_sample_net_iso(chem_id_store, net_iso_dummy)
   call evaluate_kap( &
      T, Rho, sample_species, chem_id_store, xa, &
      0, -1.0_dp, -1, -1.0_dp, -1.0_dp, -1.0_dp, -1.0_dp, &
      kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)

end subroutine mesa_kap_sample_composition


subroutine mesa_kap_composition( &
      T, Rho, species, chem_id_values, xa, &
      kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr)
   use const_def, only: dp
   use kap_def, only: num_kap_fracs
   use pyfortmesa_kap_state, only: evaluate_kap

   implicit none

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   integer, intent(out) :: ierr

   real(dp) :: kap_fracs(num_kap_fracs)
   real(dp) :: dlnkap_dxa(species)

   call evaluate_kap( &
      T, Rho, species, chem_id_values, xa, &
      0, -1.0_dp, -1, -1.0_dp, -1.0_dp, -1.0_dp, -1.0_dp, &
      kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)

end subroutine mesa_kap_composition


subroutine mesa_kap_composition_full( &
      T, Rho, species, chem_id_values, xa, &
      kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
   use const_def, only: dp
   use kap_def, only: num_kap_fracs
   use pyfortmesa_kap_state, only: evaluate_kap

   implicit none

   integer, parameter :: py_num_kap_fracs = 4

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(out) :: kap_fracs(py_num_kap_fracs)
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   real(dp), intent(out) :: dlnkap_dxa(species)
   integer, intent(out) :: ierr

   real(dp) :: mesa_kap_fracs(num_kap_fracs)

   kap_fracs(:) = 0.0_dp
   kappa = 0.0_dp
   dlnkap_dlnRho = 0.0_dp
   dlnkap_dlnT = 0.0_dp
   dlnkap_dxa(:) = 0.0_dp

   if (num_kap_fracs /= py_num_kap_fracs) then
      ierr = -4
      return
   end if

   call evaluate_kap( &
      T, Rho, species, chem_id_values, xa, &
      0, -1.0_dp, -1, -1.0_dp, -1.0_dp, -1.0_dp, -1.0_dp, &
      mesa_kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)

   if (ierr == 0) kap_fracs(:) = mesa_kap_fracs(:)

end subroutine mesa_kap_composition_full


subroutine mesa_kap_composition_with_controls( &
      T, Rho, species, chem_id_values, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr)
   use const_def, only: dp
   use kap_def, only: num_kap_fracs
   use pyfortmesa_kap_state, only: evaluate_kap

   implicit none

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   integer, intent(out) :: ierr

   real(dp) :: kap_fracs(num_kap_fracs)
   real(dp) :: dlnkap_dxa(species)

   call evaluate_kap( &
      T, Rho, species, chem_id_values, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)

end subroutine mesa_kap_composition_with_controls


subroutine mesa_kap_composition_full_with_controls( &
      T, Rho, species, chem_id_values, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
   use const_def, only: dp
   use kap_def, only: num_kap_fracs
   use pyfortmesa_kap_state, only: evaluate_kap

   implicit none

   integer, parameter :: py_num_kap_fracs = 4

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: kap_fracs(py_num_kap_fracs)
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   real(dp), intent(out) :: dlnkap_dxa(species)
   integer, intent(out) :: ierr

   real(dp) :: mesa_kap_fracs(num_kap_fracs)

   kap_fracs(:) = 0.0_dp
   kappa = 0.0_dp
   dlnkap_dlnRho = 0.0_dp
   dlnkap_dlnT = 0.0_dp
   dlnkap_dxa(:) = 0.0_dp

   if (num_kap_fracs /= py_num_kap_fracs) then
      ierr = -4
      return
   end if

   call evaluate_kap( &
      T, Rho, species, chem_id_values, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      mesa_kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)

   if (ierr == 0) kap_fracs(:) = mesa_kap_fracs(:)

end subroutine mesa_kap_composition_full_with_controls


subroutine mesa_kap_profile( &
      nzones, species, chem_id_values, input_mode, input_T, input_Rho, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      T, Rho, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: i_eta, i_lnfree_e, num_eos_basic_results, &
      num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use kap_def, only: num_kap_fracs
   use kap_lib, only: kap_get
   use pyfortmesa_kap_state, only: apply_kap_controls, ensure_kap_handles, &
      setup_net_iso
   use pyfortmesa_profile_inputs, only: profile_state_from_input

   implicit none

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   integer, intent(in) :: input_mode
   real(dp), intent(in) :: input_T(nzones)
   real(dp), intent(in) :: input_Rho(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: kappa(nzones)
   real(dp), intent(out) :: dlnkap_dlnRho(nzones)
   real(dp), intent(out) :: dlnkap_dlnT(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: kap_handle
   integer :: k
   integer :: op_err
   logical :: okay

   ierr = 0
   failed_zone = 0
   T(:) = 0.0_dp
   Rho(:) = 0.0_dp
   kappa(:) = 0.0_dp
   dlnkap_dlnRho(:) = 0.0_dp
   dlnkap_dlnT(:) = 0.0_dp

   if (nzones <= 0 .or. species <= 0) then
      ierr = -9
      return
   end if

   call ensure_kap_handles(eos_handle, kap_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      call apply_kap_controls( &
         kap_handle, use_type2_mode, zbase, use_zbase_for_type1_mode, &
         type2_full_off_x, type2_full_on_x, &
         type2_full_off_dz, type2_full_on_dz, ierr)
   end if

   if (ierr == 0) then
      okay = .true.
!$OMP PARALLEL DO PRIVATE(k,op_err) SCHEDULE(dynamic,2)
      do k = 1, nzones
!$OMP FLUSH(okay)
         if (.not. okay) cycle

         call do_profile_zone(k, op_err)

         if (op_err /= 0) then
!$OMP CRITICAL (pyfortmesa_kap_profile_error)
            if (okay) then
               okay = .false.
               ierr = op_err
               failed_zone = k
            end if
!$OMP END CRITICAL (pyfortmesa_kap_profile_error)
!$OMP FLUSH(okay)
         end if
      end do
!$OMP END PARALLEL DO
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

contains

   subroutine do_profile_zone(k, op_err)
      integer, intent(in) :: k
      integer, intent(out) :: op_err

      real(dp) :: res(num_eos_basic_results)
      real(dp) :: d_dlnd(num_eos_basic_results)
      real(dp) :: d_dlnT(num_eos_basic_results)
      real(dp) :: d_dxa(num_eos_d_dxa_results, species)
      real(dp) :: kap_fracs(num_kap_fracs)
      real(dp) :: dlnkap_dxa(species)
      real(dp) :: logT
      real(dp) :: logRho

      op_err = 0
      call profile_state_from_input(input_mode, input_T(k), input_Rho(k), &
         T(k), Rho(k), logT, logRho, op_err)
      if (op_err /= 0) return

      call eosDT_get( &
         eos_handle, species, chem_id, net_iso, xa(:, k), &
         Rho(k), logRho, T(k), logT, &
         res, d_dlnd, d_dlnT, d_dxa, op_err)
      if (op_err /= 0) return

      call kap_get( &
         kap_handle, species, chem_id, net_iso, xa(:, k), &
         logRho, logT, &
         res(i_lnfree_e), d_dlnd(i_lnfree_e), d_dlnT(i_lnfree_e), &
         res(i_eta), d_dlnd(i_eta), d_dlnT(i_eta), &
         kap_fracs, kappa(k), dlnkap_dlnRho(k), dlnkap_dlnT(k), &
         dlnkap_dxa, op_err)
   end subroutine do_profile_zone

end subroutine mesa_kap_profile


subroutine mesa_kap_profile_from_logs( &
      nzones, species, chem_id_values, lnT, lnd, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      T, Rho, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone)
   use const_def, only: dp
   use pyfortmesa_profile_inputs, only: profile_input_log

   implicit none

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: lnT(nzones)
   real(dp), intent(in) :: lnd(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: kappa(nzones)
   real(dp), intent(out) :: dlnkap_dlnRho(nzones)
   real(dp), intent(out) :: dlnkap_dlnT(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   call mesa_kap_profile(nzones, species, chem_id_values, profile_input_log, &
      lnT, lnd, xa, use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, type2_full_off_dz, &
      type2_full_on_dz, T, Rho, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, &
      failed_zone)

end subroutine mesa_kap_profile_from_logs


subroutine mesa_eos_kap_profile( &
      nzones, species, chem_id_values, input_mode, input_T, input_Rho, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      T, Rho, res, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: i_eta, i_lnfree_e, num_eos_basic_results, &
      num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use kap_def, only: num_kap_fracs
   use kap_lib, only: kap_get
   use pyfortmesa_kap_state, only: apply_kap_controls, ensure_kap_handles, &
      setup_net_iso
   use pyfortmesa_profile_inputs, only: profile_state_from_input

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   integer, intent(in) :: input_mode
   real(dp), intent(in) :: input_T(nzones)
   real(dp), intent(in) :: input_Rho(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: kappa(nzones)
   real(dp), intent(out) :: dlnkap_dlnRho(nzones)
   real(dp), intent(out) :: dlnkap_dlnT(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: kap_handle
   integer :: k
   integer :: op_err
   logical :: okay

   ierr = 0
   failed_zone = 0
   T(:) = 0.0_dp
   Rho(:) = 0.0_dp
   res(:, :) = 0.0_dp
   kappa(:) = 0.0_dp
   dlnkap_dlnRho(:) = 0.0_dp
   dlnkap_dlnT(:) = 0.0_dp

   if (num_eos_basic_results /= py_num_eos_basic_results) then
      ierr = -4
      return
   end if

   if (nzones <= 0 .or. species <= 0) then
      ierr = -9
      return
   end if

   call ensure_kap_handles(eos_handle, kap_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      call apply_kap_controls( &
         kap_handle, use_type2_mode, zbase, use_zbase_for_type1_mode, &
         type2_full_off_x, type2_full_on_x, &
         type2_full_off_dz, type2_full_on_dz, ierr)
   end if

   if (ierr == 0) then
      okay = .true.
!$OMP PARALLEL DO PRIVATE(k,op_err) SCHEDULE(dynamic,2)
      do k = 1, nzones
!$OMP FLUSH(okay)
         if (.not. okay) cycle

         call do_profile_zone(k, op_err)

         if (op_err /= 0) then
!$OMP CRITICAL (pyfortmesa_eos_kap_profile_error)
            if (okay) then
               okay = .false.
               ierr = op_err
               failed_zone = k
            end if
!$OMP END CRITICAL (pyfortmesa_eos_kap_profile_error)
!$OMP FLUSH(okay)
         end if
      end do
!$OMP END PARALLEL DO
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

contains

   subroutine do_profile_zone(k, op_err)
      integer, intent(in) :: k
      integer, intent(out) :: op_err

      real(dp) :: eos_res(num_eos_basic_results)
      real(dp) :: d_dlnd(num_eos_basic_results)
      real(dp) :: d_dlnT(num_eos_basic_results)
      real(dp) :: d_dxa(num_eos_d_dxa_results, species)
      real(dp) :: kap_fracs(num_kap_fracs)
      real(dp) :: dlnkap_dxa(species)
      real(dp) :: logT
      real(dp) :: logRho

      op_err = 0
      call profile_state_from_input(input_mode, input_T(k), input_Rho(k), &
         T(k), Rho(k), logT, logRho, op_err)
      if (op_err /= 0) return

      call eosDT_get( &
         eos_handle, species, chem_id, net_iso, xa(:, k), &
         Rho(k), logRho, T(k), logT, &
         eos_res, d_dlnd, d_dlnT, d_dxa, op_err)
      if (op_err /= 0) return

      call kap_get( &
         kap_handle, species, chem_id, net_iso, xa(:, k), &
         logRho, logT, &
         eos_res(i_lnfree_e), d_dlnd(i_lnfree_e), d_dlnT(i_lnfree_e), &
         eos_res(i_eta), d_dlnd(i_eta), d_dlnT(i_eta), &
         kap_fracs, kappa(k), dlnkap_dlnRho(k), dlnkap_dlnT(k), &
         dlnkap_dxa, op_err)
      if (op_err /= 0) return

      res(:, k) = eos_res(:)
   end subroutine do_profile_zone

end subroutine mesa_eos_kap_profile


subroutine mesa_eos_kap_profile_from_logs( &
      nzones, species, chem_id_values, lnT, lnd, xa, &
      use_type2_mode, zbase, use_zbase_for_type1_mode, &
      type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, &
      T, Rho, res, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone)
   use const_def, only: dp
   use pyfortmesa_profile_inputs, only: profile_input_log

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: lnT(nzones)
   real(dp), intent(in) :: lnd(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   integer, intent(in) :: use_type2_mode
   real(dp), intent(in) :: zbase
   integer, intent(in) :: use_zbase_for_type1_mode
   real(dp), intent(in) :: type2_full_off_x
   real(dp), intent(in) :: type2_full_on_x
   real(dp), intent(in) :: type2_full_off_dz
   real(dp), intent(in) :: type2_full_on_dz
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: kappa(nzones)
   real(dp), intent(out) :: dlnkap_dlnRho(nzones)
   real(dp), intent(out) :: dlnkap_dlnT(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   call mesa_eos_kap_profile(nzones, species, chem_id_values, &
      profile_input_log, lnT, lnd, xa, use_type2_mode, zbase, &
      use_zbase_for_type1_mode, type2_full_off_x, type2_full_on_x, &
      type2_full_off_dz, type2_full_on_dz, T, Rho, res, kappa, &
      dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone)

end subroutine mesa_eos_kap_profile_from_logs


subroutine mesa_kap_shutdown(release_tables, ierr)
   use pyfortmesa_kap_state, only: shutdown_kap_state

   implicit none

   logical, intent(in) :: release_tables
   integer, intent(out) :: ierr

   call shutdown_kap_state(release_tables, ierr)

end subroutine mesa_kap_shutdown
