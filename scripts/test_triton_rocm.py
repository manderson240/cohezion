import torch
import triton
import triton.language as tl


@triton.jit
def add_kernel(
    x_ptr,  # *Pointer* to first input vector.
    y_ptr,  # *Pointer* to second input vector.
    output_ptr,  # *Pointer* to output vector.
    n_elements,  # Size of the vector.
    BLOCK_SIZE: tl.constexpr,  # Number of elements each program should process.
    # NOTE: `constexpr` so it can be used as a shape value.
):
    # There are multiple 'programs' processing different data. We identify which program
    # we are here:
    pid = tl.program_id(0)  # We use a 1D launch grid so axis is 0.
    # This program will process inputs that are offset from the initial data.
    # For instance, if you had a vector of length 256 and block_size of 64, the programs
    # would each access the elements [0:64, 64:128, 128:192, 192:256].
    # Note that offsets are a list of pointers:
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    # Create a mask to guard memory operations exceeding the input size.
    mask = offsets < n_elements
    # Load x and y from DRAM, masking out any extra elements we read.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    # Write x + y back to DRAM.
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor):
    # We need to preallocate the output.
    output = torch.empty_like(x)
    assert x.is_cuda and y.is_cuda and output.is_cuda
    n_elements = output.numel()
    # The LUNCHPAD logic is used to determine how many programs to run.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    # Finally, we launch the kernel with the (grid, block_size, ...) arguments.
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=1024)
    return output

def test_triton_simple():
    if not torch.cuda.is_available():
        print("CUDA/ROCm not available, skipping Triton test.")
        return

    size = 98432
    x = torch.rand(size, device='cuda')
    y = torch.rand(size, device='cuda')
    output_torch = x + y
    output_triton = add(x, y)
    print(torch.max(torch.abs(output_torch - output_triton)))
    assert torch.allclose(output_torch, output_triton)
    print("Triton simple add PASSED!")

if __name__ == "__main__":
    test_triton_simple()
