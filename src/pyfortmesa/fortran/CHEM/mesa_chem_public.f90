subroutine mesa_chem_composition_info( &
      species, chem_id_values, xa, &
      xh, xhe, xz, abar, zbar, z2bar, z53bar, ye, &
      mass_correction, sumx, ierr)
   use chem_def, only: num_chem_isos
   use chem_lib, only: basic_composition_info, chem_init
   use const_def, only: dp
   use const_lib, only: const_init
   use math_lib, only: math_init

   implicit none

   integer, intent(in) :: species
   integer, intent(in) :: chem_id_values(species)
   real(dp), intent(in) :: xa(species)
   real(dp), intent(out) :: xh
   real(dp), intent(out) :: xhe
   real(dp), intent(out) :: xz
   real(dp), intent(out) :: abar
   real(dp), intent(out) :: zbar
   real(dp), intent(out) :: z2bar
   real(dp), intent(out) :: z53bar
   real(dp), intent(out) :: ye
   real(dp), intent(out) :: mass_correction
   real(dp), intent(out) :: sumx
   integer, intent(out) :: ierr

   integer, target :: chem_id_store(species)
   integer :: i

   ierr = 0
   xh = 0.0_dp
   xhe = 0.0_dp
   xz = 0.0_dp
   abar = 0.0_dp
   zbar = 0.0_dp
   z2bar = 0.0_dp
   z53bar = 0.0_dp
   ye = 0.0_dp
   mass_correction = 0.0_dp
   sumx = 0.0_dp

   call math_init()

   call const_init(' ', ierr)

   if (ierr == 0) call chem_init('isotopes.data', ierr)

   if (ierr == 0) then
      chem_id_store(:) = chem_id_values(:)
      do i = 1, species
         if (chem_id_store(i) <= 0 .or. chem_id_store(i) > num_chem_isos) then
            ierr = -2
            exit
         end if
      end do
   end if

   if (ierr == 0) then
      call basic_composition_info( &
         species, chem_id_store, xa, xh, xhe, xz, &
         abar, zbar, z2bar, z53bar, ye, mass_correction, sumx)
   end if

end subroutine mesa_chem_composition_info


subroutine mesa_chem_shutdown(ierr)
   use chem_lib, only: chem_shutdown

   implicit none

   integer, intent(out) :: ierr

   ierr = 0
   call chem_shutdown()

end subroutine mesa_chem_shutdown
