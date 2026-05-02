# AMRVAC Makefile for 3D Blast Wave Test
# Uses mpif90 for MPI compilation

FC = mpif90
FFLAGS = -O3 -ffree-form -ffree-line-length-none \
         -fdefault-real-8 -fdefault-double-8 \
         -Wall -Wextra -pedantic \
         -fcheck=all -fbacktrace \
         -I.

LDFLAGS = -lm

TARGET = amrvac
SRC = amrvac.f
INC = amrvacusrpar.inc

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(SRC) $(INC)
	$(FC) $(FFLAGS) -o $@ $< $(LDFLAGS)
	@echo "Compilation successful!"

test: $(TARGET)
	@echo "Running 3D Blast Wave test..."
	./$(TARGET)

clean:
	rm -f $(TARGET) *.o *.mod blastwave_3d.vtk

info:
	@echo "Compiler: $(FC)"
	@echo "Flags: $(FFLAGS)"
	@$(FC) --version | head -1
