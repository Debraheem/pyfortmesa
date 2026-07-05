subroutine mesa_eos_sample_composition( &
      T, Rho, xa, lnPgas, lnE, lnS, grad_ad, gamma1, ierr)
   use chem_def, only: ih1, ihe4, ic12, in14, io16, ine20, img24, num_chem_isos
   use chem_lib, only: chem_init
   use const_def, only: dp
   use const_lib, only: const_init
   use eos_def, only: i_gamma1, i_grad_ad, i_lnE, i_lnPgas, i_lnS, &
      num_eos_basic_results, num_eos_d_dxa_results
   use eos_lib, only: alloc_eos_handle, eosDT_get, eos_init, eos_shutdown, &
      free_eos_handle
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
   integer, target :: net_iso_store(num_chem_isos)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   logical :: eos_started
   real(dp) :: res(num_eos_basic_results)
   real(dp) :: d_dlnd(num_eos_basic_results)
   real(dp) :: d_dlnT(num_eos_basic_results)
   real(dp) :: d_dxa(num_eos_d_dxa_results, sample_species)

   ierr = 0
   eos_handle = -1
   eos_started = .false.
   lnPgas = 0.0_dp
   lnE = 0.0_dp
   lnS = 0.0_dp
   grad_ad = 0.0_dp
   gamma1 = 0.0_dp

   chem_id_store = [ih1, ihe4, ic12, in14, io16, ine20, img24]
   net_iso_store(:) = 0
   net_iso_store(ih1) = sample_h1
   net_iso_store(ihe4) = sample_he4
   net_iso_store(ic12) = sample_c12
   net_iso_store(in14) = sample_n14
   net_iso_store(io16) = sample_o16
   net_iso_store(ine20) = sample_ne20
   net_iso_store(img24) = sample_mg24
   chem_id => chem_id_store
   net_iso => net_iso_store

   call math_init()

   call const_init('', ierr)

   if (ierr == 0) call chem_init('isotopes.data', ierr)

   if (ierr == 0) then
      call eos_init('', .true., ierr)
      eos_started = (ierr == 0)
   end if

   if (ierr == 0) eos_handle = alloc_eos_handle(ierr)

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

   if (eos_handle > 0) call free_eos_handle(eos_handle)
   if (eos_started) call eos_shutdown()

end subroutine mesa_eos_sample_composition
