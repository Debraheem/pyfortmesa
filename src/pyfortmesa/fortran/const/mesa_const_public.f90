subroutine mesa_const_values(values, ierr)
   use const_def, only: dp, pi, pi2, pi4, eulercon, eulernum, ln2, ln3, &
      lnPi, ln10, iln10, a2rad, rad2a, one_third, two_thirds, &
      four_thirds, five_thirds, one_sixth, four_thirds_pi, ln4pi3, &
      two_13, four_13, sqrt2, sqrt_2_div_3, avo, amu, clight, qe, &
      kerg, boltzm, planck_h, hbar, cgas, ev2erg, mev_to_ergs, &
      mev_amu, mev2gr, Qconv, kev, boltz_sigma, crad, au, pc, &
      dayyer, secday, secyer, ly, mn, mp, me, rbohr, fine, hion, &
      sige, weinberg_theta, num_neu_fam, standard_cgrav, mu_sun, &
      mu_earth, mu_jupiter, agesun, Msun, Rsun, Lsun, Teffsun, &
      loggsun, mbolsun, m_earth, r_earth, r_earth_polar, m_jupiter, &
      r_jupiter, r_jupiter_polar, semimajor_axis_jupiter, &
      arg_not_provided, missing_value

   implicit none

   real(dp), intent(out) :: values(75)
   integer, intent(out) :: ierr

   ierr = 0

   ! Order must match MESA_CONSTANT_NAMES in mesa_support.py.
   values = [ &
      pi, pi2, pi4, eulercon, eulernum, ln2, ln3, lnPi, ln10, iln10, &
      a2rad, rad2a, one_third, two_thirds, four_thirds, five_thirds, &
      one_sixth, four_thirds_pi, ln4pi3, two_13, four_13, sqrt2, &
      sqrt_2_div_3, avo, amu, clight, qe, kerg, boltzm, planck_h, &
      hbar, cgas, ev2erg, mev_to_ergs, mev_amu, mev2gr, Qconv, kev, &
      boltz_sigma, crad, au, pc, dayyer, secday, secyer, ly, mn, mp, &
      me, rbohr, fine, hion, sige, weinberg_theta, num_neu_fam, &
      standard_cgrav, mu_sun, mu_earth, mu_jupiter, agesun, Msun, &
      Rsun, Lsun, Teffsun, loggsun, mbolsun, m_earth, r_earth, &
      r_earth_polar, m_jupiter, r_jupiter, r_jupiter_polar, &
      semimajor_axis_jupiter, arg_not_provided, missing_value ]

end subroutine mesa_const_values
