! AMRVAC User Parameters Include File
! 3D HD (Hydrodynamics) configuration

      INTEGER :: nw
      PARAMETER (nw=5)

!     Conservative variables
      INTEGER :: rho_, m1_, m2_, m3_, e_
      PARAMETER (rho_=1)
      PARAMETER (m1_=2)
      PARAMETER (m2_=3)
      PARAMETER (m3_=4)
      PARAMETER (e_=5)

!     Adiabatic index
      DOUBLE PRECISION :: gamma
      PARAMETER (gamma=1.4d0)
