# MLA Stage1 Kernel Argument Specification

Source traced from: `/home/mike-anderson/dev/aiter/csrc/py_itfs_cu/asm_mla.cu`
Config from: `/home/mike-anderson/dev/aiter/hsa/gfx950/mla/mla_asm.csv`
Padding types from: `/home/mike-anderson/dev/aiter/csrc/include/aiter_hip_common.h`

---

## Target Kernel

```
KERNEL FILE:   hsa/gfx950/mla/mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co
MANGLED NAME:  _ZN5aiter36mla_a8w8_qh16_qseqlen1_gqaratio16_psE
CONFIG:        qType=fp8, kvType=fp8, Gqa=16, ps=1, qSeqLen=1, prefill=0, causal=0, lse=0
```

This kernel is selected when:
- `q_dtype = fp8`, `kv_dtype = fp8`
- `gqa_ratio = 16` (16 Q-heads / 1 KV-head)
- `max_seqlen_q = 1` (decode, one token per sequence)
- `persistent = True` (work_meta_data / work_indptr+work_info_set provided)

---

## Launch Parameters

### Non-Persistent Mode (num_kv_splits_indptr != nullptr)
```
BLOCK: (256, 1, 1)   -- bdx=256 (4 wavefronts of 64), bdy=1, bdz=1
GRID:  (gdx, batch, kv_split)
  gdx = (max_seqlen_q * gqa_ratio + sub_Q - 1) / sub_Q
      = (1 * 16 + 128 - 1) / 128 = 1
  gdy = batch size (qo_indptr.size(0) - 1)
  gdz = kv_split  (splitData.size(1))
```

### Persistent Mode (num_kv_splits_indptr == nullptr)
```
BLOCK: (256, 1, 1)   -- same as above
GRID:  (work_indptr.size(0) - 1, 1, 1)
  gdx = number of work tiles = work_indptr.size(0) - 1
  gdy = 1
  gdz = 1
```

---

## KernelArgs Struct Layout

The struct is `__attribute__((packed))`. All elements follow:
- 8-byte pointer + p2 padding (8 bytes) = 16 bytes per pointer slot
- 4-byte scalar + p3 padding (12 bytes) = 16 bytes per scalar slot

```
struct p3 { uint32_t _p0; uint32_t _p1; uint32_t _p2; };  // 12 bytes
struct p2 { uint32_t _p0; uint32_t _p1; };                  // 8 bytes

struct __attribute__((packed)) KernelArgs {
    // TOTAL SIZE: 320 bytes
    void* ptr_R;         // offset 0   -- splitData (partial output) [splits, total_q, nheads, v_dim] f32
    p2 _p0;              // offset 8
    void* ptr_LSE;       // offset 16  -- splitLse (partial LSE) [splits, total_q, nheads, 1] f32
    p2 _p1;              // offset 24
    void* ptr_Q;         // offset 32  -- Q tensor [total_q, nheads, qk_head_dim] fp8
    p2 _p2;              // offset 40
    void* ptr_KV;        // offset 48  -- KV paged buffer [num_pages, page_size, 1, qk_head_dim] fp8
    p2 _p3;              // offset 56
    void* ptr_LTP;       // offset 64  -- kv_indptr [batch+1] int32
    p2 _p4;              // offset 72
    void* ptr_LTD;       // offset 80  -- kv_page_indices [total_kv_pages] int32
    p2 _p5;              // offset 88
    void* ptr_LTL;       // offset 96  -- kv_last_page_lens [batch] int32
    p2 _p6;              // offset 104
    float scalar;        // offset 112 -- softmax_scale (SM_SCALE)
    p3 _p12;             // offset 116
    uint32_t s_MQA;      // offset 128 -- gqa_ratio * max_seqlen_q  (= 16 * 1 = 16 for decode)
    p3 _p13;             // offset 132
    uint32_t s_kv_split; // offset 144 -- kv_split count = splitData.size(1)
    p3 _p14;             // offset 148
    uint32_t s_Q_Bs;     // offset 160 -- Q stride_bytes per batch: stride(0)*element_size*max_seqlen_q
    p3 _p15;             // offset 164
    uint32_t s_Bs;       // offset 176 -- KV page stride_bytes: KV.stride(0)*element_size
    p3 _p16;             // offset 180
    uint32_t s_log2_plen;// offset 192 -- log2(page_size)  (= 0 when page_size=1)
    p3 _p17;             // offset 196
    void* ptr_QTP;       // offset 208 -- qo_indptr [batch+1] int32
    p2 _p18;             // offset 216
    void* ptr_STP;       // offset 224 -- persistent metadata ptr (see below)
    p2 _p19;             // offset 232
    void* ptr_RP;        // offset 240 -- final output tensor [total_q, nheads, v_dim] bf16
    p2 _p20;             // offset 248
    void* ptr_QSCALE;    // offset 256 -- q_scale [1] f32 (required for fp8 Q)
    p2 _p21;             // offset 264
    void* ptr_KVSCALE;   // offset 272 -- kv_scale [1] f32 (required for fp8 KV)
    p2 _p22;             // offset 280
    uint32_t out_16_nosplit; // offset 288 -- kv_split (same value as s_kv_split)
    p3 _p23;             // offset 292
    void* ptr_LSEP;      // offset 304 -- final LSE [total_q, nheads] f32 (nullable)
    p2 _p24;             // offset 312
    //                   // total: 320 bytes
};
```

---

## Field-by-Field Mapping (Python call → KernelArgs)

Python call signature:
```python
mla_decode_stage1_asm_fwd(
    q_fp8,              # -> ptr_Q
    kv_4d,             # -> ptr_KV
    qo_indptr,         # -> ptr_QTP
    kv_indptr,         # -> ptr_LTP
    kv_indices,        # -> ptr_LTD
    kv_last_page_len,  # -> ptr_LTL
    None,              # num_kv_splits_indptr (None = persistent mode)
    work_metadata,     # used to fill ptr_STP (see persistent path)
    work_indptr,       # used to fill ptr_STP via packed uint64 pairs (if work_metadata is None)
    work_info_set,     # used to fill ptr_STP via packed uint64 pairs (if work_metadata is None)
    qseqlen,           # max_seqlen_q -> used to compute s_MQA, s_Q_Bs
    PAGE_SIZE,         # page_size -> used to compute s_log2_plen, s_Bs
    NUM_KV_HEADS,      # nhead_kv -> only used for gqa_ratio computation (must be 1)
    SM_SCALE,          # -> scalar
    logits,            # -> ptr_R  (splitData)
    attn_lse,          # -> ptr_LSE (splitLse)
    output,            # -> ptr_RP  (final output)
    q_scale,           # -> ptr_QSCALE
    kv_scale,          # -> ptr_KVSCALE
)
```

---

## ptr_STP: Persistent Metadata Pointer

The `ptr_STP` field encodes persistent work metadata.

**Case 1: `work_meta_data` tensor provided directly**
```c
args.ptr_STP = work_meta_data->data_ptr();
```

**Case 2: `work_indptr` + `work_info_set` provided (no pre-packed metadata)**
The C++ layer allocates a 10-element uint64_t array on device:
```c
uint64_t persistent_meta_data[10];
persistent_meta_data[0] = (uint64_t)work_indptr->data_ptr();
persistent_meta_data[1] = (uint64_t)work_info_set->data_ptr();
// hipMalloc + hipMemcpy to GPU
args.ptr_STP = dev_PS_META_DATA;  // pointer to [ptr_work_indptr, ptr_work_info_set, ...]
```

**Case 3: Non-persistent mode (num_kv_splits_indptr != nullptr)**
```c
args.ptr_STP = num_kv_splits_indptr->data_ptr();
```

---

## Scalar Computations

```c
int stride_Q    = Q->stride(0) * Q->element_size() * max_seqlen_q;
int stride_Page = KV->stride(0) * KV->element_size();
uint32_t log2_page = (uint32_t)log2f(page_size);

args.s_MQA       = gqa_ratio * max_seqlen_q;  // = 16 * 1 = 16
args.s_kv_split  = kv_split;                   // = splitData.size(1)
args.s_Q_Bs      = stride_Q;
args.s_Bs        = stride_Page;
args.s_log2_plen = log2_page;                  // = 0 for page_size=1
args.out_16_nosplit = kv_split;                // same as s_kv_split
```

For a typical decode with `[total_q=bs, 16 heads, 576 qk_head_dim]` fp8:
- `stride_Q = bs * 16 * 576 * 1 * 1 = bs * 9216` bytes (if contiguous)
  - Actually: `Q.stride(0) * Q.element_size() * max_seqlen_q = (16*576) * 1 * 1 = 9216` bytes

---

## Kernel Launch via hipModuleLaunchKernel

The C++ wrapper uses `HIP_LAUNCH_PARAM_BUFFER_POINTER` style (not `kernelParams[]`):

```c
void* config[] = {
    HIP_LAUNCH_PARAM_BUFFER_POINTER,
    &args,           // pointer to the packed KernelArgs struct
    HIP_LAUNCH_PARAM_BUFFER_SIZE,
    &arg_size,       // sizeof(KernelArgs) = 320
    HIP_LAUNCH_PARAM_END
};

hipModuleLaunchKernel(kernel_func,
    gdx, gdy, gdz,   // grid
    256, 1, 1,       // block
    0,               // shared memory = 0
    stream,
    nullptr,         // kernelParams = nullptr
    (void**)&config  // extra = config array
);
```

**Critical**: `kernelParams` must be `nullptr`; all args go via `extra` with `HIP_LAUNCH_PARAM_BUFFER_POINTER`.

---

## ctypes Python Equivalent

```python
import ctypes

class p2(ctypes.Structure):
    _fields_ = [("_p0", ctypes.c_uint32), ("_p1", ctypes.c_uint32)]

class p3(ctypes.Structure):
    _fields_ = [("_p0", ctypes.c_uint32), ("_p1", ctypes.c_uint32), ("_p2", ctypes.c_uint32)]

class MlaKernelArgs(ctypes.Structure):
    _pack_ = 1  # __attribute__((packed))
    _fields_ = [
        ("ptr_R",           ctypes.c_void_p),  # offset 0
        ("_p0",             p2),               # offset 8
        ("ptr_LSE",         ctypes.c_void_p),  # offset 16
        ("_p1",             p2),               # offset 24
        ("ptr_Q",           ctypes.c_void_p),  # offset 32
        ("_p2",             p2),               # offset 40
        ("ptr_KV",          ctypes.c_void_p),  # offset 48
        ("_p3",             p2),               # offset 56
        ("ptr_LTP",         ctypes.c_void_p),  # offset 64  (kv_indptr)
        ("_p4",             p2),               # offset 72
        ("ptr_LTD",         ctypes.c_void_p),  # offset 80  (kv_page_indices)
        ("_p5",             p2),               # offset 88
        ("ptr_LTL",         ctypes.c_void_p),  # offset 96  (kv_last_page_lens)
        ("_p6",             p2),               # offset 104
        ("scalar",          ctypes.c_float),   # offset 112 (softmax_scale)
        ("_p12",            p3),               # offset 116
        ("s_MQA",           ctypes.c_uint32),  # offset 128 (gqa_ratio * max_seqlen_q)
        ("_p13",            p3),               # offset 132
        ("s_kv_split",      ctypes.c_uint32),  # offset 144
        ("_p14",            p3),               # offset 148
        ("s_Q_Bs",          ctypes.c_uint32),  # offset 160 (Q stride bytes per seq)
        ("_p15",            p3),               # offset 164
        ("s_Bs",            ctypes.c_uint32),  # offset 176 (KV page stride bytes)
        ("_p16",            p3),               # offset 180
        ("s_log2_plen",     ctypes.c_uint32),  # offset 192 (log2(page_size))
        ("_p17",            p3),               # offset 196
        ("ptr_QTP",         ctypes.c_void_p),  # offset 208 (qo_indptr)
        ("_p18",            p2),               # offset 216
        ("ptr_STP",         ctypes.c_void_p),  # offset 224 (persistent metadata)
        ("_p19",            p2),               # offset 232
        ("ptr_RP",          ctypes.c_void_p),  # offset 240 (final output)
        ("_p20",            p2),               # offset 248
        ("ptr_QSCALE",      ctypes.c_void_p),  # offset 256
        ("_p21",            p2),               # offset 264
        ("ptr_KVSCALE",     ctypes.c_void_p),  # offset 272
        ("_p22",            p2),               # offset 280
        ("out_16_nosplit",  ctypes.c_uint32),  # offset 288 (= kv_split)
        ("_p23",            p3),               # offset 292
        ("ptr_LSEP",        ctypes.c_void_p),  # offset 304 (final LSE, nullable)
        ("_p24",            p2),               # offset 312
    ]

assert ctypes.sizeof(MlaKernelArgs) == 320
```

### Launch Call

```python
HIP_LAUNCH_PARAM_BUFFER_POINTER = ctypes.c_void_p(1)
HIP_LAUNCH_PARAM_BUFFER_SIZE    = ctypes.c_void_p(2)
HIP_LAUNCH_PARAM_END            = ctypes.c_void_p(3)

args = MlaKernelArgs()
# ... fill fields ...
arg_size = ctypes.c_size_t(ctypes.sizeof(args))

config = (ctypes.c_void_p * 5)(
    HIP_LAUNCH_PARAM_BUFFER_POINTER,
    ctypes.cast(ctypes.addressof(args), ctypes.c_void_p),
    HIP_LAUNCH_PARAM_BUFFER_SIZE,
    ctypes.cast(ctypes.addressof(arg_size), ctypes.c_void_p),
    HIP_LAUNCH_PARAM_END,
)

hip.hipModuleLaunchKernel(
    func,          # hipFunction_t
    gdx, 1, 1,     # grid (persistent mode)
    256, 1, 1,     # block
    0,             # shared mem
    stream,
    None,          # kernelParams = nullptr
    config,        # extra
)
```

---

## mla_reduce_v1: NOT an ASM kernel

`mla_reduce_v1` is a CK-tile device kernel compiled into the aiter `.so`, NOT a pre-compiled `.co` file. It is launched via `<<<grid, threads, sharedmem, stream>>>` syntax from `csrc/kernels/mla/reduce.cu`.

To invoke it from ctypes you must call it through the compiled `libaiter.so` C ABI, NOT via `hipModuleLoad`.

The Python binding is: `aiter.mla_reduce_v1(partial_output, partial_lse, reduce_indptr, reduce_final_map, reduce_partial_map, max_seqlen_q, final_output, final_lse)`

---

## Work Buffer Layout (Persistent Mode)

The `work_meta_data` tensor is a device buffer of `10 * sizeof(uint64_t) = 80 bytes` containing:
```
[0]: (uint64_t) device pointer to work_indptr  [int32_t*, length = num_tiles + 1]
[1]: (uint64_t) device pointer to work_info_set [MlaWorkInfo*, 8 x int32 per entry]
[2..9]: unused (reserved)
```

`MlaWorkInfo` (8 x int32 = 32 bytes each):
```c
struct MlaWorkInfo {
    int32_t batch_idx;
    int32_t partial_qo_loc;
    int32_t qo_start;
    int32_t qo_end;
    int32_t kv_start;
    int32_t kv_end;
    int32_t kv_offset;
    int32_t padding[1];
};
```

---

## Summary Table

| Field        | Python argument  | Type     | Value for fp8 decode, gqa=16, qseqlen=1, ps=1 |
|--------------|-----------------|----------|------------------------------------------------|
| ptr_R        | logits          | void*    | splitData GPU ptr                              |
| ptr_LSE      | attn_lse        | void*    | splitLse GPU ptr                               |
| ptr_Q        | q_fp8           | void*    | Q GPU ptr                                      |
| ptr_KV       | kv_4d           | void*    | KV GPU ptr                                     |
| ptr_LTP      | kv_indptr       | void*    | kv_indptr GPU ptr                              |
| ptr_LTD      | kv_indices      | void*    | kv_page_indices GPU ptr                        |
| ptr_LTL      | kv_last_page_len| void*    | kv_last_page_lens GPU ptr                      |
| scalar       | SM_SCALE        | float    | 1/sqrt(576) ≈ 0.04167                          |
| s_MQA        | computed        | uint32   | 16 * 1 = 16                                    |
| s_kv_split   | computed        | uint32   | splitData.size(1) = num_kv_splits              |
| s_Q_Bs       | computed        | uint32   | Q.stride(0)*1*1 = 16*576 = 9216 bytes          |
| s_Bs         | computed        | uint32   | KV.stride(0)*1 = page_size*1*576 bytes         |
| s_log2_plen  | computed        | uint32   | log2(1) = 0                                    |
| ptr_QTP      | qo_indptr       | void*    | qo_indptr GPU ptr                              |
| ptr_STP      | work_meta_data  | void*    | persistent metadata GPU ptr (see above)        |
| ptr_RP       | output          | void*    | final output GPU ptr                           |
| ptr_QSCALE   | q_scale         | void*    | [1] f32 GPU ptr                                |
| ptr_KVSCALE  | kv_scale        | void*    | [1] f32 GPU ptr                                |
| out_16_nosplit| computed       | uint32   | = kv_split (same as s_kv_split)               |
| ptr_LSEP     | lse (nullable)  | void*    | nullptr (no final LSE output needed)           |
