subroutine mesa_const_values( &
      cgrav_value, crad_value, clight_value, &
      lsun_value, rsun_value, msun_value, ierr)
   use const_def, only: dp, standard_cgrav, crad, clight, Lsun, Rsun, Msun

   implicit none

   real(dp), intent(out) :: cgrav_value
   real(dp), intent(out) :: crad_value
   real(dp), intent(out) :: clight_value
   real(dp), intent(out) :: lsun_value
   real(dp), intent(out) :: rsun_value
   real(dp), intent(out) :: msun_value
   integer, intent(out) :: ierr

   ierr = 0
   cgrav_value = standard_cgrav
   crad_value = crad
   clight_value = clight
   lsun_value = Lsun
   rsun_value = Rsun
   msun_value = Msun

end subroutine mesa_const_values
