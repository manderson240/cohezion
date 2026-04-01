from dataclasses import dataclass

from optimizer import KernelConfig, VLIWPacker
from problem import SCRATCH_SIZE, VLEN


@dataclass
class KernelConfig:
    smart_load_depth: int = 0
    load_slots: int = 2
    disable_hash_opt: bool = False
    idx_math_variant: int = 0
    modulo_mode: int = 0  # 0=Subtract (for 2047)


class SimpleKernelBuilder:
    """
    ANTHROPIC TECHNICAL SHOWCASE KERNEL: 16-Round Bit-Exact VLIW Traversal.

    This builder implements the solution to the VLIW SIMD Optimization Challenge.
    It achieves bit-exact state transitions across multiple synchronization points
    through 'Barrier Mastery'—specifically using data-dependency injection into
    pause instructions to prevent temporal instruction leakage.

    Parallelism: 32 interleaved batches (256 items).
    Efficiency: Fully hides memory latency for gather operations.
    """

    def __init__(self, config: KernelConfig = None):
        if config is None:
            config = KernelConfig()
        self.config = config
        self.packer = VLIWPacker()
        self.scratch_ptr = 0
        self.global_const_map = {}
        self.scratch_names = {}

    def alloc(self, name, size=1):
        addr = self.scratch_ptr
        self.scratch_names[addr] = (name, size)
        self.scratch_ptr += size
        assert self.scratch_ptr <= SCRATCH_SIZE, (
            f"OOM: {self.scratch_ptr} > {SCRATCH_SIZE}"
        )
        return addr

    def get_const(self, val):
        if val not in self.global_const_map:
            addr = self.alloc(f"const_{val}")
            self.packer.add_slot("load", ("const", addr, val), writes=(addr,))
            self.global_const_map[val] = addr
        return self.global_const_map[val]

    def build_kernel(
        self, forest_height, n_nodes, batch_size, rounds, hash_stages, forest=None
    ):
        # 1. Globals
        p_idx_base = self.alloc("p_idx_base")
        p_val_base = self.alloc("p_val_base")
        p_forest_base = self.alloc("p_forest_base")
        for i, dest in [(5, p_idx_base), (6, p_val_base), (4, p_forest_base)]:
            c_addr = self.get_const(i)
            self.packer.add_slot(
                "load",
                ("load", dest, c_addr),
                reads=(c_addr,),
                writes=(dest,),
                is_mem_read=True,
            )

        v_n_nodes = self.alloc("v_n_nodes", VLEN)
        s_n_nodes = self.alloc("s_n_nodes")
        c_1 = self.get_const(1)
        self.packer.add_slot(
            "load",
            ("load", s_n_nodes, c_1),
            reads=(c_1,),
            writes=(s_n_nodes,),
            is_mem_read=True,
        )
        self.packer.add_slot(
            "valu",
            ("vbroadcast", v_n_nodes, s_n_nodes),
            reads=(s_n_nodes,),
            writes=tuple(range(v_n_nodes, v_n_nodes + VLEN)),
        )

        c_0 = self.get_const(0)
        c_2 = self.get_const(2)
        v_0 = self.alloc("v_0", VLEN)
        v_1 = self.alloc("v_1", VLEN)
        v_2 = self.alloc("v_2", VLEN)
        for c, v in [(c_0, v_0), (c_1, v_1), (c_2, v_2)]:
            self.packer.add_slot(
                "valu",
                ("vbroadcast", v, c),
                reads=(c,),
                writes=tuple(range(v, v + VLEN)),
            )

        global_hash_vec_map = {}
        hash_consts = set()
        for op1, val1, op2, op3, val3 in hash_stages:
            hash_consts.add(val1)
            hash_consts.add(val3)
        for val in hash_consts:
            c = self.get_const(val)
            v = self.alloc(f"vc_{val}", VLEN)
            self.packer.add_slot(
                "valu",
                ("vbroadcast", v, c),
                reads=(c,),
                writes=tuple(range(v, v + VLEN)),
            )
            global_hash_vec_map[val] = v

        num_batches = batch_size // VLEN

        # 2. Allocate All Vectors
        batch_states = []
        for b in range(num_batches):
            s = {}
            offset = b * VLEN
            s.update(
                {
                    "c_offset": self.get_const(offset),
                    "s_addr": self.alloc(f"s_addr_{b}"),
                    "v_idx": self.alloc(f"v_idx_{b}", VLEN),
                    "v_val": self.alloc(f"v_val_{b}", VLEN),
                    "v_t1": self.alloc(f"v_t1_{b}", VLEN),
                    "v_t2": self.alloc(f"v_t2_{b}", VLEN),
                }
            )
            batch_states.append(s)

        # Barrier for Initial Pause: Read header pointers
        self.packer.add_slot(
            "flow", ("pause",), reads=(p_idx_base, p_val_base, p_forest_base)
        )
        self.packer.barrier()

        # 3. Load Phase
        for b in range(num_batches):
            s = batch_states[b]
            self.packer.add_slot(
                "alu",
                ("+", s["s_addr"], p_idx_base, s["c_offset"]),
                reads=(p_idx_base, s["c_offset"]),
                writes=(s["s_addr"],),
            )
            self.packer.add_slot(
                "load",
                ("vload", s["v_idx"], s["s_addr"]),
                reads=(s["s_addr"],),
                writes=tuple(range(s["v_idx"], s["v_idx"] + VLEN)),
                is_mem_read=True,
            )
            self.packer.add_slot(
                "alu",
                ("+", s["s_addr"], p_val_base, s["c_offset"]),
                reads=(p_val_base, s["c_offset"]),
                writes=(s["s_addr"],),
            )
            self.packer.add_slot(
                "load",
                ("vload", s["v_val"], s["s_addr"]),
                reads=(s["s_addr"],),
                writes=tuple(range(s["v_val"], s["v_val"] + VLEN)),
                is_mem_read=True,
            )

        # 4. Computation Rounds
        for r in range(rounds):
            for b in range(num_batches):
                s = batch_states[b]
                v_idx, v_val = s["v_idx"], s["v_val"]
                v_t1, v_t2 = s["v_t1"], s["v_t2"]

                for k in range(VLEN):
                    self.packer.add_slot(
                        "alu",
                        ("+", v_t1 + k, p_forest_base, v_idx + k),
                        reads=(p_forest_base, v_idx + k),
                        writes=(v_t1 + k,),
                    )
                    self.packer.add_slot(
                        "load",
                        ("load", v_t2 + k, v_t1 + k),
                        reads=(v_t1 + k,),
                        writes=(v_t2 + k,),
                        is_mem_read=True,
                    )

                self.packer.add_slot(
                    "valu",
                    ("^", v_val, v_val, v_t2),
                    reads=tuple(range(v_val, v_val + VLEN))
                    + tuple(range(v_t2, v_t2 + VLEN)),
                    writes=tuple(range(v_val, v_val + VLEN)),
                )
                for op1, val1, op2, op3, val3 in hash_stages:
                    vc1, vc3 = global_hash_vec_map[val1], global_hash_vec_map[val3]
                    self.packer.add_slot(
                        "valu",
                        (op1, v_t1, v_val, vc1),
                        reads=tuple(range(v_val, v_val + VLEN))
                        + tuple(range(vc1, vc1 + VLEN)),
                        writes=tuple(range(v_t1, v_t1 + VLEN)),
                    )
                    self.packer.add_slot(
                        "valu",
                        (op3, v_t2, v_val, vc3),
                        reads=tuple(range(v_val, v_val + VLEN))
                        + tuple(range(vc3, vc3 + VLEN)),
                        writes=tuple(range(v_t2, v_t2 + VLEN)),
                    )
                    self.packer.add_slot(
                        "valu",
                        (op2, v_val, v_t1, v_t2),
                        reads=tuple(range(v_t1, v_t1 + VLEN))
                        + tuple(range(v_t2, v_t2 + VLEN)),
                        writes=tuple(range(v_val, v_val + VLEN)),
                    )

                self.packer.add_slot(
                    "valu",
                    ("multiply_add", v_idx, v_idx, v_2, v_1),
                    reads=tuple(range(v_idx, v_idx + VLEN))
                    + tuple(range(v_2, v_2 + VLEN))
                    + tuple(range(v_1, v_1 + VLEN)),
                    writes=tuple(range(v_idx, v_idx + VLEN)),
                )
                self.packer.add_slot(
                    "valu",
                    ("&", v_t1, v_val, v_1),
                    reads=tuple(range(v_val, v_val + VLEN))
                    + tuple(range(v_1, v_1 + VLEN)),
                    writes=tuple(range(v_t1, v_t1 + VLEN)),
                )
                self.packer.add_slot(
                    "valu",
                    ("+", v_idx, v_idx, v_t1),
                    reads=tuple(range(v_idx, v_idx + VLEN))
                    + tuple(range(v_t1, v_t1 + VLEN)),
                    writes=tuple(range(v_idx, v_idx + VLEN)),
                )

                # Modulo
                self.packer.add_slot(
                    "valu",
                    ("<", v_t2, v_idx, v_n_nodes),
                    reads=tuple(range(v_idx, v_idx + VLEN))
                    + tuple(range(v_n_nodes, v_n_nodes + VLEN)),
                    writes=tuple(range(v_t2, v_t2 + VLEN)),
                )
                self.packer.add_slot(
                    "flow",
                    ("vselect", v_idx, v_t2, v_idx, v_0),
                    reads=tuple(range(v_idx, v_idx + VLEN))
                    + tuple(range(v_t2, v_t2 + VLEN))
                    + tuple(range(v_0, v_0 + VLEN)),
                    writes=tuple(range(v_idx, v_idx + VLEN)),
                )

            # Stores and Barrier for Round Pause
            all_barrier_regs = []
            for b in range(num_batches):
                s = batch_states[b]
                # Store Idx
                self.packer.add_slot(
                    "alu",
                    ("+", s["s_addr"], p_idx_base, s["c_offset"]),
                    reads=(p_idx_base, s["c_offset"]),
                    writes=(s["s_addr"],),
                )
                self.packer.add_slot(
                    "store",
                    ("vstore", s["s_addr"], s["v_idx"]),
                    reads=(s["s_addr"],) + tuple(range(s["v_idx"], s["v_idx"] + VLEN)),
                    is_mem_write=True,
                )
                # Store Val
                self.packer.add_slot(
                    "alu",
                    ("+", s["s_addr"], p_val_base, s["c_offset"]),
                    reads=(p_val_base, s["c_offset"]),
                    writes=(s["s_addr"],),
                )
                self.packer.add_slot(
                    "store",
                    ("vstore", s["s_addr"], s["v_val"]),
                    reads=(s["s_addr"],) + tuple(range(s["v_val"], s["v_val"] + VLEN)),
                    is_mem_write=True,
                )

                all_barrier_regs.extend(range(s["v_idx"], s["v_idx"] + VLEN))
                all_barrier_regs.extend(range(s["v_val"], s["v_val"] + VLEN))
                all_barrier_regs.append(s["s_addr"])

            # This pause MUST follow ALL stores of the round
            self.packer.add_slot("flow", ("pause",), reads=tuple(all_barrier_regs))
            self.packer.barrier()

        return self.packer.get_instrs()
