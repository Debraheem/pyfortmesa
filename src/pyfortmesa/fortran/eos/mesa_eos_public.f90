module pyfortmesa_eos_state
   use chem_def, only: ih1, ihe4, ic12, in14, io16, ine20, img24, &
      num_chem_isos
   use chem_lib, only: chem_init
   use const_lib, only: const_init
   use eos_lib, only: alloc_eos_handle, alloc_eos_handle_using_inlist, &
      eos_init, eos_shutdown, free_eos_handle
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
   logical, save :: base_started = .false.
   logical, save :: eos_started = .false.

contains

   subroutine ensure_eos_handle(eos_handle, ierr)
      integer, intent(out) :: eos_handle
      integer, intent(out) :: ierr

      character(len=1024) :: inlist_path
      logical :: has_inlist

      ierr = 0
      eos_handle = eos_handle_store

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

      eos_handle = eos_handle_store
   end subroutine ensure_eos_handle


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


   subroutine shutdown_eos_state(release_tables, ierr)
      logical, intent(in) :: release_tables
      integer, intent(out) :: ierr

      ierr = 0

      if (eos_handle_store > 0) then
         call free_eos_handle(eos_handle_store)
         eos_handle_store = -1
      end if

      if (release_tables) then
         if (eos_started) call eos_shutdown()
         eos_started = .false.
         base_started = .false.
      end if
   end subroutine shutdown_eos_state


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

end module pyfortmesa_eos_state


subroutine mesa_eos_sample_composition( &
      T, Rho, xa, lnPgas, lnE, lnS, grad_ad, gamma1, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: i_gamma1, i_grad_ad, i_lnE, i_lnPgas, i_lnS, &
      num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use pyfortmesa_eos_state, only: ensure_eos_handle, sample_species, &
      setup_sample_net_iso

   implicit none

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   real(dp), intent(in) :: xa(sample_species)
   real(dp), intent(out) :: lnPgas
   real(dp), intent(out) :: lnE
   real(dp), intent(out) :: lnS
   real(dp), intent(out) :: grad_ad
   real(dp), intent(out) :: gamma1
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(sample_species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   real(dp) :: res(num_eos_basic_results)
   real(dp) :: d_dlnd(num_eos_basic_results)
   real(dp) :: d_dlnT(num_eos_basic_results)
   real(dp) :: d_dxa(num_eos_d_dxa_results, sample_species)

   ierr = 0
   lnPgas = 0.0_dp
   lnE = 0.0_dp
   lnS = 0.0_dp
   grad_ad = 0.0_dp
   gamma1 = 0.0_dp

   if (T <= 0.0_dp .or. Rho <= 0.0_dp) then
      ierr = -5
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_sample_net_iso(chem_id_store, net_iso_store)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      call eosDT_get( &
         eos_handle, sample_species, chem_id, net_iso, xa, &
         Rho, log10(Rho), T, log10(T), &
         res, d_dlnd, d_dlnT, d_dxa, ierr)
   end if

   if (ierr == 0) then
      lnPgas = res(i_lnPgas)
      lnE = res(i_lnE)
      lnS = res(i_lnS)
      grad_ad = res(i_grad_ad)
      gamma1 = res(i_gamma1)
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

end subroutine mesa_eos_sample_composition


subroutine mesa_eos_composition( &
      T, Rho, species, chem_id_values, xa, &
      lnPgas, lnE, lnS, grad_ad, gamma1, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: i_gamma1, i_grad_ad, i_lnE, i_lnPgas, i_lnS, &
      num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso

   implicit none

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(out) :: lnPgas
   real(dp), intent(out) :: lnE
   real(dp), intent(out) :: lnS
   real(dp), intent(out) :: grad_ad
   real(dp), intent(out) :: gamma1
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   real(dp) :: res(num_eos_basic_results)
   real(dp) :: d_dlnd(num_eos_basic_results)
   real(dp) :: d_dlnT(num_eos_basic_results)
   real(dp) :: d_dxa(num_eos_d_dxa_results, species)

   ierr = 0
   lnPgas = 0.0_dp
   lnE = 0.0_dp
   lnS = 0.0_dp
   grad_ad = 0.0_dp
   gamma1 = 0.0_dp

   if (T <= 0.0_dp .or. Rho <= 0.0_dp) then
      ierr = -5
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

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
      lnPgas = res(i_lnPgas)
      lnE = res(i_lnE)
      lnS = res(i_lnS)
      grad_ad = res(i_grad_ad)
      gamma1 = res(i_gamma1)
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

end subroutine mesa_eos_composition


subroutine mesa_eos_composition_full( &
      T, Rho, species, chem_id_values, xa, &
      res, d_dlnd, d_dlnT, d_dxa, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26
   integer, parameter :: py_num_eos_d_dxa_results = 2

   real(dp), intent(in) :: T
   real(dp), intent(in) :: Rho
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(out) :: res(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnd(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnT(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dxa(py_num_eos_d_dxa_results, species)
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   real(dp) :: eos_res(num_eos_basic_results)
   real(dp) :: eos_d_dlnd(num_eos_basic_results)
   real(dp) :: eos_d_dlnT(num_eos_basic_results)
   real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)

   ierr = 0
   res(:) = 0.0_dp
   d_dlnd(:) = 0.0_dp
   d_dlnT(:) = 0.0_dp
   d_dxa(:, :) = 0.0_dp

   if (num_eos_basic_results /= py_num_eos_basic_results .or. &
       num_eos_d_dxa_results /= py_num_eos_d_dxa_results) then
      ierr = -4
      return
   end if

   if (T <= 0.0_dp .or. Rho <= 0.0_dp) then
      ierr = -5
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

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
         eos_res, eos_d_dlnd, eos_d_dlnT, eos_d_dxa, ierr)
   end if

   if (ierr == 0) then
      res(:) = eos_res(:)
      d_dlnd(:) = eos_d_dlnd(:)
      d_dlnT(:) = eos_d_dlnT(:)
      d_dxa(:, :) = eos_d_dxa(:, :)
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

end subroutine mesa_eos_composition_full


subroutine mesa_eos_profile( &
      nzones, species, chem_id_values, input_mode, input_T, input_Rho, xa, &
      T, Rho, res, ierr, failed_zone)
   use chem_def, only: num_chem_isos
   use const_def, only: dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso
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
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: k
   integer :: op_err
   logical :: okay

   ierr = 0
   failed_zone = 0
   T(:) = 0.0_dp
   Rho(:) = 0.0_dp
   res(:, :) = 0.0_dp

   if (num_eos_basic_results /= py_num_eos_basic_results) then
      ierr = -4
      return
   end if

   if (nzones <= 0 .or. species <= 0) then
      ierr = -5
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      okay = .true.
!$OMP PARALLEL DO PRIVATE(k,op_err) SCHEDULE(dynamic,2)
      do k = 1, nzones
!$OMP FLUSH(okay)
         if (.not. okay) cycle

         call do_profile_zone(k, op_err)

         if (op_err /= 0) then
!$OMP CRITICAL (pyfortmesa_eos_profile_error)
            if (okay) then
               okay = .false.
               ierr = op_err
               failed_zone = k
         end if
!$OMP END CRITICAL (pyfortmesa_eos_profile_error)
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
      real(dp) :: eos_d_dlnd(num_eos_basic_results)
      real(dp) :: eos_d_dlnT(num_eos_basic_results)
      real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)
      real(dp) :: logT
      real(dp) :: logRho

      op_err = 0
      call profile_state_from_input(input_mode, input_T(k), input_Rho(k), &
         T(k), Rho(k), logT, logRho, op_err)
      if (op_err /= 0) return

      call eosDT_get( &
         eos_handle, species, chem_id, net_iso, xa(:, k), &
         Rho(k), logRho, T(k), logT, &
         eos_res, eos_d_dlnd, eos_d_dlnT, eos_d_dxa, op_err)
      if (op_err /= 0) return

      res(:, k) = eos_res(:)
   end subroutine do_profile_zone

end subroutine mesa_eos_profile


subroutine mesa_eos_profile_from_logs( &
      nzones, species, chem_id_values, lnT, lnd, xa, &
      T, Rho, res, ierr, failed_zone)
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
   real(dp), intent(out) :: T(nzones)
   real(dp), intent(out) :: Rho(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   call mesa_eos_profile(nzones, species, chem_id_values, profile_input_log, &
      lnT, lnd, xa, T, Rho, res, ierr, failed_zone)

end subroutine mesa_eos_profile_from_logs


subroutine mesa_eos_solve_rho( &
      T, which_other, other_value, Rho_guess, &
      species, chem_id_values, xa, logRho_tol, other_tol, max_iter, &
      Rho_result, logRho_result, res, d_dlnd, d_dlnT, d_dxa, eos_calls, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: arg_not_provided, dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get_Rho
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26
   integer, parameter :: py_num_eos_d_dxa_results = 2

   real(dp), intent(in) :: T
   integer, intent(in) :: which_other
   real(dp), intent(in) :: other_value
   real(dp), intent(in) :: Rho_guess
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(in) :: logRho_tol
   real(dp), intent(in) :: other_tol
   integer, intent(in) :: max_iter
   real(dp), intent(out) :: Rho_result
   real(dp), intent(out) :: logRho_result
   real(dp), intent(out) :: res(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnd(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnT(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dxa(py_num_eos_d_dxa_results, species)
   integer, intent(out) :: eos_calls
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   real(dp) :: eos_res(num_eos_basic_results)
   real(dp) :: eos_d_dlnd(num_eos_basic_results)
   real(dp) :: eos_d_dlnT(num_eos_basic_results)
   real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)

   ierr = 0
   Rho_result = 0.0_dp
   logRho_result = 0.0_dp
   res(:) = 0.0_dp
   d_dlnd(:) = 0.0_dp
   d_dlnT(:) = 0.0_dp
   d_dxa(:, :) = 0.0_dp
   eos_calls = 0

   if (num_eos_basic_results /= py_num_eos_basic_results .or. &
       num_eos_d_dxa_results /= py_num_eos_d_dxa_results) then
      ierr = -4
      return
   end if

   if (T <= 0.0_dp .or. Rho_guess <= 0.0_dp .or. max_iter <= 0) then
      ierr = -5
      return
   end if

   if (which_other <= 0 .or. which_other > num_eos_basic_results) then
      ierr = -6
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      call eosDT_get_Rho( &
         eos_handle, species, chem_id, net_iso, xa, &
         log10(T), which_other, other_value, &
         logRho_tol, other_tol, max_iter, log10(Rho_guess), &
         arg_not_provided, arg_not_provided, &
         arg_not_provided, arg_not_provided, &
         logRho_result, eos_res, eos_d_dlnd, eos_d_dlnT, &
         eos_d_dxa, eos_calls, ierr)
   end if

   if (ierr == 0) then
      Rho_result = 10.0_dp**logRho_result
      res(:) = eos_res(:)
      d_dlnd(:) = eos_d_dlnd(:)
      d_dlnT(:) = eos_d_dlnT(:)
      d_dxa(:, :) = eos_d_dxa(:, :)
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

end subroutine mesa_eos_solve_rho


subroutine mesa_eos_solve_t( &
      Rho, which_other, other_value, T_guess, &
      species, chem_id_values, xa, logT_tol, other_tol, max_iter, &
      T_result, logT_result, res, d_dlnd, d_dlnT, d_dxa, eos_calls, ierr)
   use chem_def, only: num_chem_isos
   use const_def, only: arg_not_provided, dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get_T
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26
   integer, parameter :: py_num_eos_d_dxa_results = 2

   real(dp), intent(in) :: Rho
   integer, intent(in) :: which_other
   real(dp), intent(in) :: other_value
   real(dp), intent(in) :: T_guess
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(in) :: logT_tol
   real(dp), intent(in) :: other_tol
   integer, intent(in) :: max_iter
   real(dp), intent(out) :: T_result
   real(dp), intent(out) :: logT_result
   real(dp), intent(out) :: res(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnd(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dlnT(py_num_eos_basic_results)
   real(dp), intent(out) :: d_dxa(py_num_eos_d_dxa_results, species)
   integer, intent(out) :: eos_calls
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   real(dp) :: eos_res(num_eos_basic_results)
   real(dp) :: eos_d_dlnd(num_eos_basic_results)
   real(dp) :: eos_d_dlnT(num_eos_basic_results)
   real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)

   ierr = 0
   T_result = 0.0_dp
   logT_result = 0.0_dp
   res(:) = 0.0_dp
   d_dlnd(:) = 0.0_dp
   d_dlnT(:) = 0.0_dp
   d_dxa(:, :) = 0.0_dp
   eos_calls = 0

   if (num_eos_basic_results /= py_num_eos_basic_results .or. &
       num_eos_d_dxa_results /= py_num_eos_d_dxa_results) then
      ierr = -4
      return
   end if

   if (Rho <= 0.0_dp .or. T_guess <= 0.0_dp .or. max_iter <= 0) then
      ierr = -5
      return
   end if

   if (which_other <= 0 .or. which_other > num_eos_basic_results) then
      ierr = -6
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      call eosDT_get_T( &
         eos_handle, species, chem_id, net_iso, xa, &
         log10(Rho), which_other, other_value, &
         logT_tol, other_tol, max_iter, log10(T_guess), &
         arg_not_provided, arg_not_provided, &
         arg_not_provided, arg_not_provided, &
         logT_result, eos_res, eos_d_dlnd, eos_d_dlnT, &
         eos_d_dxa, eos_calls, ierr)
   end if

   if (ierr == 0) then
      T_result = 10.0_dp**logT_result
      res(:) = eos_res(:)
      d_dlnd(:) = eos_d_dlnd(:)
      d_dlnT(:) = eos_d_dlnT(:)
      d_dxa(:, :) = eos_d_dxa(:, :)
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

end subroutine mesa_eos_solve_t


subroutine mesa_eos_solve_rho_profile( &
      nzones, species, chem_id_values, input_mode, input_T, which_other, &
      other_value, Rho_guess, xa, logRho_tol, other_tol, max_iter, &
      Rho_result, logRho_result, res, d_dlnd, d_dlnT, d_dxa, eos_calls, &
      ierr, failed_zone)
   use chem_def, only: num_chem_isos
   use const_def, only: arg_not_provided, dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get_Rho
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso
   use pyfortmesa_profile_inputs, only: profile_input_value, profile_value_from_input

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26
   integer, parameter :: py_num_eos_d_dxa_results = 2

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   integer, intent(in) :: input_mode
   real(dp), intent(in) :: input_T(nzones)
   integer, intent(in) :: which_other
   real(dp), intent(in) :: other_value(nzones)
   real(dp), intent(in) :: Rho_guess(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   real(dp), intent(in) :: logRho_tol
   real(dp), intent(in) :: other_tol
   integer, intent(in) :: max_iter
   real(dp), intent(out) :: Rho_result(nzones)
   real(dp), intent(out) :: logRho_result(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dlnd(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dlnT(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dxa(py_num_eos_d_dxa_results, species, nzones)
   integer, intent(out) :: eos_calls(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: k
   integer :: op_err
   logical :: okay

   ierr = 0
   failed_zone = 0
   Rho_result(:) = 0.0_dp
   logRho_result(:) = 0.0_dp
   res(:, :) = 0.0_dp
   d_dlnd(:, :) = 0.0_dp
   d_dlnT(:, :) = 0.0_dp
   d_dxa(:, :, :) = 0.0_dp
   eos_calls(:) = 0

   if (num_eos_basic_results /= py_num_eos_basic_results .or. &
       num_eos_d_dxa_results /= py_num_eos_d_dxa_results) then
      ierr = -4
      return
   end if

   if (nzones <= 0 .or. species <= 0 .or. max_iter <= 0) then
      ierr = -5
      return
   end if

   if (which_other <= 0 .or. which_other > num_eos_basic_results) then
      ierr = -6
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      okay = .true.
!$OMP PARALLEL DO PRIVATE(k,op_err) SCHEDULE(dynamic,2)
      do k = 1, nzones
!$OMP FLUSH(okay)
         if (.not. okay) cycle

         call do_solve_rho_zone(k, op_err)

         if (op_err /= 0) then
!$OMP CRITICAL (pyfortmesa_eos_solve_rho_profile_error)
            if (okay) then
               okay = .false.
               ierr = op_err
               failed_zone = k
            end if
!$OMP END CRITICAL (pyfortmesa_eos_solve_rho_profile_error)
!$OMP FLUSH(okay)
         end if
      end do
!$OMP END PARALLEL DO
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

contains

   subroutine do_solve_rho_zone(k, op_err)
      integer, intent(in) :: k
      integer, intent(out) :: op_err

      real(dp) :: T_value
      real(dp) :: logT
      real(dp) :: Rho_guess_value
      real(dp) :: logRho_guess
      real(dp) :: eos_res(num_eos_basic_results)
      real(dp) :: eos_d_dlnd(num_eos_basic_results)
      real(dp) :: eos_d_dlnT(num_eos_basic_results)
      real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)
      integer :: zone_calls

      op_err = 0
      call profile_value_from_input(input_mode, input_T(k), T_value, logT, op_err)
      if (op_err /= 0) return

      call profile_value_from_input(profile_input_value, Rho_guess(k), &
         Rho_guess_value, logRho_guess, op_err)
      if (op_err /= 0) return

      call eosDT_get_Rho( &
         eos_handle, species, chem_id, net_iso, xa(:, k), &
         logT, which_other, other_value(k), &
         logRho_tol, other_tol, max_iter, logRho_guess, &
         arg_not_provided, arg_not_provided, &
         arg_not_provided, arg_not_provided, &
         logRho_result(k), eos_res, eos_d_dlnd, eos_d_dlnT, &
         eos_d_dxa, zone_calls, op_err)
      if (op_err /= 0) return

      Rho_result(k) = 10.0_dp**logRho_result(k)
      res(:, k) = eos_res(:)
      d_dlnd(:, k) = eos_d_dlnd(:)
      d_dlnT(:, k) = eos_d_dlnT(:)
      d_dxa(:, :, k) = eos_d_dxa(:, :)
      eos_calls(k) = zone_calls
   end subroutine do_solve_rho_zone

end subroutine mesa_eos_solve_rho_profile


subroutine mesa_eos_solve_t_profile( &
      nzones, species, chem_id_values, input_mode, input_Rho, which_other, &
      other_value, T_guess, xa, logT_tol, other_tol, max_iter, &
      T_result, logT_result, res, d_dlnd, d_dlnT, d_dxa, eos_calls, ierr, &
      failed_zone)
   use chem_def, only: num_chem_isos
   use const_def, only: arg_not_provided, dp
   use eos_def, only: num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: eosDT_get_T
   use pyfortmesa_eos_state, only: ensure_eos_handle, setup_net_iso
   use pyfortmesa_profile_inputs, only: profile_input_value, profile_value_from_input

   implicit none

   integer, parameter :: py_num_eos_basic_results = 26
   integer, parameter :: py_num_eos_d_dxa_results = 2

   integer, intent(in) :: nzones
   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   integer, intent(in) :: input_mode
   real(dp), intent(in) :: input_Rho(nzones)
   integer, intent(in) :: which_other
   real(dp), intent(in) :: other_value(nzones)
   real(dp), intent(in) :: T_guess(nzones)
   real(dp), intent(in) :: xa(species, nzones)
   real(dp), intent(in) :: logT_tol
   real(dp), intent(in) :: other_tol
   integer, intent(in) :: max_iter
   real(dp), intent(out) :: T_result(nzones)
   real(dp), intent(out) :: logT_result(nzones)
   real(dp), intent(out) :: res(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dlnd(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dlnT(py_num_eos_basic_results, nzones)
   real(dp), intent(out) :: d_dxa(py_num_eos_d_dxa_results, species, nzones)
   integer, intent(out) :: eos_calls(nzones)
   integer, intent(out) :: ierr
   integer, intent(out) :: failed_zone

   integer, target :: chem_id_store(species)
   integer, allocatable, target :: net_iso_store(:)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: k
   integer :: op_err
   logical :: okay

   ierr = 0
   failed_zone = 0
   T_result(:) = 0.0_dp
   logT_result(:) = 0.0_dp
   res(:, :) = 0.0_dp
   d_dlnd(:, :) = 0.0_dp
   d_dlnT(:, :) = 0.0_dp
   d_dxa(:, :, :) = 0.0_dp
   eos_calls(:) = 0

   if (num_eos_basic_results /= py_num_eos_basic_results .or. &
       num_eos_d_dxa_results /= py_num_eos_d_dxa_results) then
      ierr = -4
      return
   end if

   if (nzones <= 0 .or. species <= 0 .or. max_iter <= 0) then
      ierr = -5
      return
   end if

   if (which_other <= 0 .or. which_other > num_eos_basic_results) then
      ierr = -6
      return
   end if

   call ensure_eos_handle(eos_handle, ierr)

   if (ierr == 0) allocate(net_iso_store(num_chem_isos), stat=ierr)

   if (ierr == 0) then
      call setup_net_iso(species, chem_id_values, chem_id_store, &
         net_iso_store, ierr)
      chem_id => chem_id_store
      net_iso => net_iso_store
   end if

   if (ierr == 0) then
      okay = .true.
!$OMP PARALLEL DO PRIVATE(k,op_err) SCHEDULE(dynamic,2)
      do k = 1, nzones
!$OMP FLUSH(okay)
         if (.not. okay) cycle

         call do_solve_t_zone(k, op_err)

         if (op_err /= 0) then
!$OMP CRITICAL (pyfortmesa_eos_solve_t_profile_error)
            if (okay) then
               okay = .false.
               ierr = op_err
               failed_zone = k
            end if
!$OMP END CRITICAL (pyfortmesa_eos_solve_t_profile_error)
!$OMP FLUSH(okay)
         end if
      end do
!$OMP END PARALLEL DO
   end if

   if (allocated(net_iso_store)) deallocate(net_iso_store)

contains

   subroutine do_solve_t_zone(k, op_err)
      integer, intent(in) :: k
      integer, intent(out) :: op_err

      real(dp) :: Rho_value
      real(dp) :: logRho
      real(dp) :: T_guess_value
      real(dp) :: logT_guess
      real(dp) :: eos_res(num_eos_basic_results)
      real(dp) :: eos_d_dlnd(num_eos_basic_results)
      real(dp) :: eos_d_dlnT(num_eos_basic_results)
      real(dp) :: eos_d_dxa(num_eos_d_dxa_results, species)
      integer :: zone_calls

      op_err = 0
      call profile_value_from_input(input_mode, input_Rho(k), Rho_value, logRho, op_err)
      if (op_err /= 0) return

      call profile_value_from_input(profile_input_value, T_guess(k), &
         T_guess_value, logT_guess, op_err)
      if (op_err /= 0) return

      call eosDT_get_T( &
         eos_handle, species, chem_id, net_iso, xa(:, k), &
         logRho, which_other, other_value(k), &
         logT_tol, other_tol, max_iter, logT_guess, &
         arg_not_provided, arg_not_provided, &
         arg_not_provided, arg_not_provided, &
         logT_result(k), eos_res, eos_d_dlnd, eos_d_dlnT, &
         eos_d_dxa, zone_calls, op_err)
      if (op_err /= 0) return

      T_result(k) = 10.0_dp**logT_result(k)
      res(:, k) = eos_res(:)
      d_dlnd(:, k) = eos_d_dlnd(:)
      d_dlnT(:, k) = eos_d_dlnT(:)
      d_dxa(:, :, k) = eos_d_dxa(:, :)
      eos_calls(k) = zone_calls
   end subroutine do_solve_t_zone

end subroutine mesa_eos_solve_t_profile


subroutine mesa_eos_shutdown(release_tables, ierr)
   use pyfortmesa_eos_state, only: shutdown_eos_state

   implicit none

   logical, intent(in) :: release_tables
   integer, intent(out) :: ierr

   call shutdown_eos_state(release_tables, ierr)

end subroutine mesa_eos_shutdown
