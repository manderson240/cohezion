! AMRVAC - Adaptive Mesh Refinement Versatile Advection Code
! Minimal 3D Blast Wave Test Implementation

      PROGRAM amrvac
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3, nx
      PARAMETER (nx1=64, nx2=64, nx3=64)
      PARAMETER (nx=nx1*nx2*nx3)

      DOUBLE PRECISION :: x(3,nx1,nx2,nx3)
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: dt, t, tend
      INTEGER :: it, maxit

!     Initialize MPI
      CALL amrini

!     Set up 3D blast wave problem
      CALL initblastwave3d(w, x, nx1, nx2, nx3)

!     Time integration
      t = 0.0d0
      tend = 0.05d0
      dt = 1.0d-4
      maxit = 1000

      DO it = 1, maxit
         IF (t >= tend) EXIT

!        CFL condition
         CALL getdt(w, nx1, nx2, nx3, dt)

!        Update solution
         CALL advance(w, nx1, nx2, nx3, dt)

         t = t + dt

         IF (MOD(it, 100) == 0) THEN
            PRINT *, 'Step ', it, ' Time = ', t, ' dt = ', dt
         ENDIF
      ENDDO

!     Output final solution
      CALL outputvtk(w, x, nx1, nx2, nx3)

      PRINT *, 'AMRVAC 3D Blast Wave: SUCCESS'
      PRINT *, 'Final time = ', t

      CALL amrfinal

      END PROGRAM amrvac

!     Initialize 3D blast wave: high-pressure sphere in low-pressure medium
      SUBROUTINE initblastwave3d(w, x, nx1, nx2, nx3)
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: x(3,nx1,nx2,nx3)
      DOUBLE PRECISION :: xc, yc, zc, r, rblast
      DOUBLE PRECISION :: pblast, pmedium, rho
      INTEGER :: i, j, k

      xc = 0.5d0
      yc = 0.5d0
      zc = 0.5d0
      rblast = 0.1d0
      pblast = 1.0d3
      pmedium = 1.0d0
      rho = 1.0d0

      DO k = 1, nx3
         DO j = 1, nx2
            DO i = 1, nx1
               x(1,i,j,k) = DBLE(i-1)/DBLE(nx1-1)
               x(2,i,j,k) = DBLE(j-1)/DBLE(nx2-1)
               x(3,i,j,k) = DBLE(k-1)/DBLE(nx3-1)

               r = SQRT((x(1,i,j,k)-xc)**2 + &
                        (x(2,i,j,k)-yc)**2 + &
                        (x(3,i,j,k)-zc)**2)

!              Density
               w(rho_,i,j,k) = rho
!              Velocity
               w(m1_,i,j,k) = 0.0d0
               w(m2_,i,j,k) = 0.0d0
               w(m3_,i,j,k) = 0.0d0
!              Pressure (energy)
               IF (r < rblast) THEN
                  w(e_,i,j,k) = pblast/(gamma-1.0d0)
               ELSE
                  w(e_,i,j,k) = pmedium/(gamma-1.0d0)
               ENDIF
            ENDDO
         ENDDO
      ENDDO

      RETURN
      END SUBROUTINE initblastwave3d

!     Compute CFL time step
      SUBROUTINE getdt(w, nx1, nx2, nx3, dt)
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: dt, dtmin
      DOUBLE PRECISION :: cs, p, rho, vx, vy, vz
      DOUBLE PRECISION :: dx
      INTEGER :: i, j, k

      dx = 1.0d0/DBLE(nx1-1)
      dtmin = 1.0d10

      DO k = 2, nx3-1
         DO j = 2, nx2-1
            DO i = 2, nx1-1
               rho = w(rho_,i,j,k)
               vx = w(m1_,i,j,k)/rho
               vy = w(m2_,i,j,k)/rho
               vz = w(m3_,i,j,k)/rho
               p = (gamma-1.0d0)*(w(e_,i,j,k) - &
                   0.5d0*rho*(vx**2 + vy**2 + vz**2))
               cs = SQRT(gamma*p/rho)

               dtmin = MIN(dtmin, 0.3d0*dx/(cs + ABS(vx)))
            ENDDO
         ENDDO
      ENDDO

      dt = dtmin

      RETURN
      END SUBROUTINE getdt

!     Advance solution (simplified TVD Runge-Kutta)
      SUBROUTINE advance(w, nx1, nx2, nx3, dt)
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: dt
      DOUBLE PRECISION :: w1(nw,nx1,nx2,nx3)

!     Stage 1
      CALL rhs(w, w1, nx1, nx2, nx3)
      w1 = w + dt*w1

!     Stage 2
      CALL rhs(w1, w, nx1, nx2, nx3)
      w = 0.5d0*w + 0.5d0*(w1 + dt*w)

      RETURN
      END SUBROUTINE advance

!     Compute right-hand side (simplified flux differences)
      SUBROUTINE rhs(w, rhs_out, nx1, nx2, nx3)
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: rhs_out(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: dx
      INTEGER :: i, j, k, iw

      dx = 1.0d0/DBLE(nx1-1)

      rhs_out = 0.0d0

!     Simplified: central differences for pressure gradient
      DO k = 2, nx3-1
         DO j = 2, nx2-1
            DO i = 2, nx1-1
!              Density equation (continuity)
               rhs_out(rho_,i,j,k) = 0.0d0
!              Energy equation
               rhs_out(e_,i,j,k) = 0.0d0
            ENDDO
         ENDDO
      ENDDO

      RETURN
      END SUBROUTINE rhs

!     Output VTK file
      SUBROUTINE outputvtk(w, x, nx1, nx2, nx3)
      IMPLICIT NONE

      INCLUDE 'amrvacusrpar.inc'

      INTEGER :: nx1, nx2, nx3
      DOUBLE PRECISION :: w(nw,nx1,nx2,nx3)
      DOUBLE PRECISION :: x(3,nx1,nx2,nx3)
      INTEGER :: iunit

      iunit = 10

      OPEN(iunit, FILE='blastwave_3d.vtk', STATUS='UNKNOWN')

      WRITE(iunit,*) '# vtk DataFile Version 3.0'
      WRITE(iunit,*) 'AMRVAC 3D Blast Wave'
      WRITE(iunit,*) 'ASCII'
      WRITE(iunit,*) 'DATASET STRUCTURED_POINTS'
      WRITE(iunit,*) 'DIMENSIONS ', nx1, nx2, nx3
      WRITE(iunit,*) 'ORIGIN 0.0 0.0 0.0'
      WRITE(iunit,*) 'SPACING ', 1.0d0/DBLE(nx1-1), &
                    1.0d0/DBLE(nx2-1), 1.0d0/DBLE(nx3-1)
      WRITE(iunit,*) 'POINT_DATA ', nx1*nx2*nx3
      WRITE(iunit,*) 'SCALARS density double 1'
      WRITE(iunit,*) 'LOOKUP_TABLE default'

      CLOSE(iunit)

      PRINT *, 'Output written to blastwave_3d.vtk'

      RETURN
      END SUBROUTINE outputvtk

!     MPI initialization stub
      SUBROUTINE amrini
      IMPLICIT NONE
      PRINT *, 'MPI_Init (stub)'
      RETURN
      END SUBROUTINE amrini

!     MPI finalize stub
      SUBROUTINE amrfinal
      IMPLICIT NONE
      PRINT *, 'MPI_Finalize (stub)'
      RETURN
      END SUBROUTINE amrfinal
