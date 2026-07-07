module pyfortmesa_profile_inputs
   use const_def, only: dp, iln10

   implicit none

   integer, parameter :: profile_input_value = 0
   integer, parameter :: profile_input_log = 1
   integer, parameter :: profile_input_log10 = 2

contains

   subroutine profile_value_from_input(input_mode, input_value, value, &
         log10_value, ierr)
      integer, intent(in) :: input_mode
      real(dp), intent(in) :: input_value
      real(dp), intent(out) :: value
      real(dp), intent(out) :: log10_value
      integer, intent(out) :: ierr

      ierr = 0
      value = 0.0_dp
      log10_value = 0.0_dp

      select case (input_mode)
      case (profile_input_value)
         value = input_value
         if (value <= 0.0_dp) then
            ierr = -5
            return
         end if
         log10_value = log10(value)
      case (profile_input_log)
         value = exp(input_value)
         if (value <= 0.0_dp) then
            ierr = -5
            return
         end if
         log10_value = input_value*iln10
      case (profile_input_log10)
         log10_value = input_value
         value = 10.0_dp**log10_value
         if (value <= 0.0_dp) then
            ierr = -5
            return
         end if
      case default
         ierr = -6
      end select
   end subroutine profile_value_from_input


   subroutine profile_state_from_input(input_mode, input_T, input_Rho, T, &
         Rho, logT, logRho, ierr)
      integer, intent(in) :: input_mode
      real(dp), intent(in) :: input_T
      real(dp), intent(in) :: input_Rho
      real(dp), intent(out) :: T
      real(dp), intent(out) :: Rho
      real(dp), intent(out) :: logT
      real(dp), intent(out) :: logRho
      integer, intent(out) :: ierr

      call profile_value_from_input(input_mode, input_T, T, logT, ierr)
      if (ierr /= 0) return

      call profile_value_from_input(input_mode, input_Rho, Rho, logRho, ierr)
   end subroutine profile_state_from_input

end module pyfortmesa_profile_inputs
