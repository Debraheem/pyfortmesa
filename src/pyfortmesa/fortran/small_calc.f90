subroutine small_calc_f(x, y)
   use pyfortmesa_const_def, only: dp
   implicit none

   real(dp), intent(in) :: x
   real(dp), intent(out) :: y

   y = 3.0_dp*x*x + 2.0_dp
end subroutine small_calc_f

subroutine big_sum_f(n, total)
   use pyfortmesa_const_def, only: dp
   implicit none

   integer, intent(in) :: n
   real(dp), intent(out) :: total

   integer :: i

   total = 0.0_dp
   do i = 1, n
      total = total + 0.5_dp*real(i, dp)
   end do
end subroutine big_sum_f
