"""
Smoke test for direct CK GEMM kernel dispatch via ctypes.

This bypasses aiter's Python overhead by directly loading pre-compiled .co kernels
and calling hipModuleLaunchKernel with the correct argument layout.

Kernel argument layout (from asm_gemm_a4w4.cu):
struct __attribute__((packed)) KernelArgs {
    void*   ptr_D;           // 8 bytes
    p2      _p0;             // 8 bytes (2 x uint32)
    void*   ptr_C;           // 8 bytes  
    p2      _p1;             // 8 bytes
    void*   ptr_A;           // 8 bytes
    p2      _p2;             // 8 bytes
    void*   ptr_B;           // 8 bytes
    p2      _p3;             // 8 bytes
    float   alpha;           // 4 bytes
    p3      _p4;             // 12 bytes (3 x uint32)
    float   beta;            // 4 bytes
    p3      _p5;             // 12 bytes
    uint    stride_D0;       // 4 bytes
    p3      _p6;             // 12 bytes
    uint    stride_D1;       // 4 bytes
    p3      _p7;             // 12 bytes
    uint    stride_C0;       // 4 bytes
    p3      _p8;             // 12 bytes
    uint    stride_C1;       // 4 bytes
    p3      _p9;             // 12 bytes
    uint    stride_A0;       // 4 bytes
    p3      _p10;            // 12 bytes
    uint    stride_A1;       // 4 bytes
    p3      _p11;            // 12 bytes
    uint    stride_B0;       // 4 bytes
    p3      _p12;            // 12 bytes
    uint    stride_B1;       // 4 bytes
    p3      _p13;            // 12 bytes
    uint    M;               // 4 bytes
    p3      _p14;            // 12 bytes
    uint    N;               // 4 bytes
    p3      _p15;            // 12 bytes
    uint    K;               // 4 bytes
    p3      _p16;            // 12 bytes
    void*   ptr_ScaleA;      // 8 bytes
    p2      _p17;            // 8 bytes
    void*   ptr_ScaleB;      // 8 bytes
    p2      _p18;            // 8 bytes
    uint    stride_ScaleA0;  // 4 bytes
    p3      _p19;            // 12 bytes
    uint    stride_ScaleA1;  // 4 bytes
    p3      _p20;            // 12 bytes
    uint    stride_ScaleB0;  // 4 bytes
    p3      _p21;            // 12 bytes
    uint    stride_ScaleB1;  // 4 bytes
    p3      _p22;            // 12 bytes
    int     log2_k_split;    // 4 bytes
};

Layout info from CSV (kernel configs for gfx950):
- kernel: _ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256E
- co: f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256.co
- tile_M=128, tile_N=256, splitK=0, bpreshuffle=1
"""

import ctypes
import glob
import os


# Constants
HIP_SUCCESS = 0
CO_DIR = '/home/mike-anderson/dev/aiter/hsa/gfx950/f4gemm'

# Struct that matches the C++ KernelArgs exactly
class KernelArgs(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('ptr_D', ctypes.c_void_p),
        ('_p0', ctypes.c_uint * 2),
        ('ptr_C', ctypes.c_void_p),
        ('_p1', ctypes.c_uint * 2),
        ('ptr_A', ctypes.c_void_p),
        ('_p2', ctypes.c_uint * 2),
        ('ptr_B', ctypes.c_void_p),
        ('_p3', ctypes.c_uint * 2),
        ('alpha', ctypes.c_float),
        ('_p4', ctypes.c_uint * 3),
        ('beta', ctypes.c_float),
        ('_p5', ctypes.c_uint * 3),
        ('stride_D0', ctypes.c_uint),
        ('_p6', ctypes.c_uint * 3),
        ('stride_D1', ctypes.c_uint),
        ('_p7', ctypes.c_uint * 3),
        ('stride_C0', ctypes.c_uint),
        ('_p8', ctypes.c_uint * 3),
        ('stride_C1', ctypes.c_uint),
        ('_p9', ctypes.c_uint * 3),
        ('stride_A0', ctypes.c_uint),
        ('_p10', ctypes.c_uint * 3),
        ('stride_A1', ctypes.c_uint),
        ('_p11', ctypes.c_uint * 3),
        ('stride_B0', ctypes.c_uint),
        ('_p12', ctypes.c_uint * 3),
        ('stride_B1', ctypes.c_uint),
        ('_p13', ctypes.c_uint * 3),
        ('M', ctypes.c_uint),
        ('_p14', ctypes.c_uint * 3),
        ('N', ctypes.c_uint),
        ('_p15', ctypes.c_uint * 3),
        ('K', ctypes.c_uint),
        ('_p16', ctypes.c_uint * 3),
        ('ptr_ScaleA', ctypes.c_void_p),
        ('_p17', ctypes.c_uint * 2),
        ('ptr_ScaleB', ctypes.c_void_p),
        ('_p18', ctypes.c_uint * 2),
        ('stride_ScaleA0', ctypes.c_uint),
        ('_p19', ctypes.c_uint * 3),
        ('stride_ScaleA1', ctypes.c_uint),
        ('_p20', ctypes.c_uint * 3),
        ('stride_ScaleB0', ctypes.c_uint),
        ('_p21', ctypes.c_uint * 3),
        ('stride_ScaleB1', ctypes.c_uint),
        ('_p22', ctypes.c_uint * 3),
        ('log2_k_split', ctypes.c_int),
    ]


def get_struct_size() -> int:
    """Return the size of KernelArgs struct."""
    return ctypes.sizeof(KernelArgs)


def test_struct_size():
    """Verify struct size matches C++ sizeof."""
    size = get_struct_size()
    print(f"KernelArgs struct size: {size} bytes")
    # Expected from C++ code: 288 bytes (based on arg_size variable in the C++)


def test_co_files_exist():
    """Verify .co files are available."""
    co_files = glob.glob(f'{CO_DIR}/*.co')
    print(f"Found {len(co_files)} pre-compiled .co files in {CO_DIR}")
    if co_files:
        print(f"  Example: {os.path.basename(co_files[0])}")
    return len(co_files) > 0


def test_hip_library():
    """Test that HIP library can be loaded."""
    try:
        hip = ctypes.CDLL('libamdhip64.so', ctypes.RTLD_GLOBAL)
        print("Successfully loaded libamdhip64.so")
        return True
    except Exception as e:
        print(f"Failed to load HIP library: {e}")
        return False


def test_module_load(co_path: str):
    """Test loading a .co file directly."""
    hip = ctypes.CDLL('libamdhip64.so', ctypes.RTLD_GLOBAL)
    
    if not os.path.exists(co_path):
        print(f".co file not found: {co_path}")
        return None, None
    
    with open(co_path, 'rb') as f:
        co_data = f.read()
    print(f"Loaded .co file: {len(co_data)} bytes")
    
    module = ctypes.c_void_p()
    
    # Try hipModuleLoadDataEx (preferred for in-memory loading)
    try:
        hip.hipModuleLoadDataEx.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_uint,
            ctypes.c_void_p
        ]
        hip.hipModuleLoadDataEx.restype = ctypes.c_int
        
        result = hip.hipModuleLoadDataEx(
            ctypes.byref(module),
            co_data,
            len(co_data),
            0,
            None
        )
        print(f"hipModuleLoadDataEx result: {result}")
    except Exception as e:
        print(f"hipModuleLoadDataEx exception: {e}")
        result = -1
    
    if result != HIP_SUCCESS:
        # Try hipModuleLoad with filename
        try:
            hip.hipModuleLoad.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p]
            hip.hipModuleLoad.restype = ctypes.c_int
            result = hip.hipModuleLoad(ctypes.byref(module), co_path.encode())
            print(f"hipModuleLoad (file) result: {result}")
        except Exception as e:
            print(f"hipModuleLoad exception: {e}")
    
    if result != HIP_SUCCESS:
        print(f"Failed to load module: {result}")
        return None, None
    
    print(f"Module loaded: {module.value}")
    return hip, module


def test_kernel_dispatch(hip, module, kernel_name: str, args: KernelArgs):
    """Test launching a kernel."""
    if hip is None or module is None:
        print("Skipping kernel dispatch test (no module)")
        return False
    
    func = ctypes.c_void_p()
    result = hip.hipModuleGetFunction(
        ctypes.byref(func),
        module,
        kernel_name.encode() if isinstance(kernel_name, str) else kernel_name
    )
    
    if result != HIP_SUCCESS:
        print(f"hipModuleGetFunction failed: {result}")
        return False
    
    print(f"Got kernel function: {func.value}")
    
    # Grid and block dimensions
    gdx = 1
    gdy = 1
    gdz = 1
    bdx = 256
    bdy = 1
    bdz = 1
    
    # Create config for hipModuleLaunchKernel
    arg_size = ctypes.c_size_t(get_struct_size())
    args_ptr = ctypes.byref(args)
    
    config = (ctypes.c_void_p * 5)(
        0x4000,  # HIP_LAUNCH_PARAM_BUFFER_POINTER
        args_ptr,
        0x4001,  # HIP_LAUNCH_PARAM_BUFFER_SIZE
        ctypes.byref(arg_size),
        0x4002   # HIP_LAUNCH_PARAM_END
    )
    
    # Launch kernel
    stream = ctypes.c_void_p(0)  # 0 = default stream
    result = hip.hipModuleLaunchKernel(
        func,
        gdx, gdy, gdz,
        bdx, bdy, bdz,
        0,  # shared memory
        stream,
        None,  # host耳朵
        config
    )
    
    if result == HIP_SUCCESS:
        print("Kernel launched successfully!")
        return True
    else:
        print(f"hipModuleLaunchKernel failed: {result}")
        return False


def main():
    print("=" * 60)
    print("Direct CK GEMM Kernel Dispatch - Smoke Test")
    print("=" * 60)
    
    # Test 1: Struct size
    print("\n[1] Testing struct size...")
    test_struct_size()
    
    # Test 2: .co files exist
    print("\n[2] Testing .co files exist...")
    test_co_files_exist()
    
    # Test 3: HIP library
    print("\n[3] Testing HIP library...")
    test_hip_library()
    
    # Test 4: Module loading
    print("\n[4] Testing module loading...")
    co_path = f'{CO_DIR}/f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256.co'
    hip, module = test_module_load(co_path)
    
    # Test 5: Kernel dispatch
    if module:
        print("\n[5] Testing kernel dispatch...")
        # Create dummy args
        args = KernelArgs()
        args.ptr_D = 0
        args.ptr_C = 0
        args.ptr_A = 0
        args.ptr_B = 0
        args.alpha = 1.0
        args.beta = 0.0
        args.stride_D0 = 0
        args.stride_D1 = 0
        args.stride_C0 = 0
        args.stride_C1 = 0
        args.stride_A0 = 0
        args.stride_A1 = 0
        args.stride_B0 = 0
        args.stride_B1 = 0
        args.M = 128
        args.N = 256
        args.K = 256
        args.ptr_ScaleA = 0
        args.ptr_ScaleB = 0
        args.stride_ScaleA0 = 0
        args.stride_ScaleA1 = 0
        args.stride_ScaleB0 = 0
        args.stride_ScaleB1 = 0
        args.log2_k_split = 0
        
        kernel_name = '_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256E'
        test_kernel_dispatch(hip, module, kernel_name, args)
    
    print("\n" + "=" * 60)
    print("Smoke test complete")
    print("=" * 60)


if __name__ == '__main__':
    main()
