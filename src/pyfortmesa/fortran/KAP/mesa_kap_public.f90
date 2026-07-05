subroutine mesa_kap_sample_composition( &
      T, Rho, xa, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr)
   use chem_def, only: ih1, ihe4, ic12, in14, io16, ine20, img24, num_chem_isos
   use chem_lib, only: chem_init
   use const_def, only: dp
   use const_lib, only: const_init
   use eos_def, only: i_eta, i_lnfree_e, num_eos_basic_results, &
      num_eos_d_dxa_results
   use eos_lib, only: alloc_eos_handle, eosDT_get, eos_init, eos_shutdown, &
      free_eos_handle
   use kap_def, only: num_kap_fracs
   use kap_lib, only: alloc_kap_handle, free_kap_handle, kap_get, kap_init, &
      kap_shutdown
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
   real(dp), intent(out) :: kappa
   real(dp), intent(out) :: dlnkap_dlnRho
   real(dp), intent(out) :: dlnkap_dlnT
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(sample_species)
   integer, target :: net_iso_store(num_chem_isos)
   integer, pointer :: chem_id(:)
   integer, pointer :: net_iso(:)
   integer :: eos_handle
   integer :: kap_handle
   logical :: eos_started
   logical :: kap_started
   real(dp) :: res(num_eos_basic_results)
   real(dp) :: d_dlnd(num_eos_basic_results)
   real(dp) :: d_dlnT(num_eos_basic_results)
   real(dp) :: d_dxa(num_eos_d_dxa_results, sample_species)
   real(dp) :: kap_fracs(num_kap_fracs)
   real(dp) :: dlnkap_dxa(sample_species)

   ierr = 0
   eos_handle = -1
   kap_handle = -1
   eos_started = .false.
   kap_started = .false.
   kappa = 0.0_dp
   dlnkap_dlnRho = 0.0_dp
   dlnkap_dlnT = 0.0_dp

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
      call kap_init(.true., '', ierr)
      kap_started = (ierr == 0)
   end if

   if (ierr == 0) kap_handle = alloc_kap_handle(ierr)

   if (ierr == 0) then
      call kap_get( &
         kap_handle, sample_species, chem_id, net_iso, xa, log10(Rho), log10(T), &
         res(i_lnfree_e), d_dlnd(i_lnfree_e), d_dlnT(i_lnfree_e), &
         res(i_eta), d_dlnd(i_eta), d_dlnT(i_eta), &
         kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
   end if

   if (kap_handle > 0) call free_kap_handle(kap_handle)
   if (kap_started) call kap_shutdown()
   if (eos_handle > 0) call free_eos_handle(eos_handle)
   if (eos_started) call eos_shutdown()

end subroutine mesa_kap_sample_composition
