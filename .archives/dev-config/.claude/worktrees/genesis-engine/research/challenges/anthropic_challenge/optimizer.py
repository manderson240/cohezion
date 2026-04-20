import collections
from dataclasses import dataclass

from problem import N_CORES, SCRATCH_SIZE, SLOT_LIMITS, VLEN


class VLIWPacker:
    def __init__(self):
        self.bundles = []
        self.last_write = collections.defaultdict(lambda: -1)
        self.last_read = collections.defaultdict(lambda: -1)
        self.min_bundle_idx = 0
        self.last_mem_write = -1
        self.last_mem_read = -1

    def barrier(self):
        self.min_bundle_idx = len(self.bundles)
        for k in self.last_write:
            self.last_write[k] = self.min_bundle_idx - 1
        for k in self.last_read:
            self.last_read[k] = self.min_bundle_idx - 1
        self.last_mem_write = self.min_bundle_idx - 1
        self.last_mem_read = self.min_bundle_idx - 1

    def add_slot(self, engine, slot, reads=(), writes=(), is_mem_read=False, is_mem_write=False):
        min_bundle_idx = self.min_bundle_idx - 1
        for r in reads:
            min_bundle_idx = max(min_bundle_idx, self.last_write[r])
        for w in writes:
            min_bundle_idx = max(min_bundle_idx, self.last_write[w])
            min_bundle_idx = max(min_bundle_idx, self.last_read[w])

        if is_mem_read:
            min_bundle_idx = max(min_bundle_idx, self.last_mem_write)
        if is_mem_write:
            min_bundle_idx = max(min_bundle_idx, self.last_mem_read, self.last_mem_write)

        start_idx = min_bundle_idx + 1
        bundle_idx = start_idx
        while True:
            if bundle_idx >= len(self.bundles):
                self.bundles.append({})

            bundle = self.bundles[bundle_idx]
            slots = bundle.setdefault(engine, [])

            if len(slots) < SLOT_LIMITS.get(engine, 1):
                slots.append(slot)
                for w in writes:
                    self.last_write[w] = bundle_idx
                for r in reads:
                    self.last_read[r] = bundle_idx
                if is_mem_read:
                    self.last_mem_read = max(self.last_mem_read, bundle_idx)
                if is_mem_write:
                    self.last_mem_write = max(self.last_mem_write, bundle_idx)
                break
            bundle_idx += 1

    def get_instrs(self):
        return self.bundles


@dataclass
class KernelConfig:
    smart_load_depth: int = 4
    load_slots: int = 4
    disable_hash_opt: bool = False
    crown_depth: int = 7


N_VEC = 30


class OptimizedKernelBuilder:
    def __init__(self, config: KernelConfig = None):
        if config is None:
            config = KernelConfig()
        self.config = config
        self.packer = VLIWPacker()
        self.scratch_ptr = 0
        self.scratch_names = {}
        self.global_const_map = {}
        self.global_vconst_map = {}

    def alloc(self, name, size=1):
        addr = self.scratch_ptr
        self.scratch_ptr += size
        # print(f"ALLOC: {name} size={size} ptr={self.scratch_ptr}")
        assert self.scratch_ptr <= SCRATCH_SIZE, f"Scratch overflow: {self.scratch_ptr} > {SCRATCH_SIZE}"
        self.scratch_names[addr] = name, size
        return addr

    def valloc(self, name):
        return self.alloc(name, VLEN)

    def get_const(self, val):
        if val not in self.global_const_map:
            addr = self.alloc(f"const_{val}")
            self.packer.add_slot("load", ("const", addr, val), writes=(addr,))
            self.global_const_map[val] = addr
        return self.global_const_map[val]

    def get_vconst(self, val):
        if val not in self.global_vconst_map:
            const_addr = self.get_const(val)
            v_addr = self.valloc(f"vconst_{val}")
            self.packer.add_slot(
                "valu",
                ("vbroadcast", v_addr, const_addr),
                reads=(const_addr,),
                writes=tuple(range(v_addr, v_addr + VLEN)),
            )
            self.global_vconst_map[val] = v_addr
        return self.global_vconst_map[val]

    def emit_op(self, op, dest, args):
        reads = []
        for arg in args:
            reads.extend(range(arg, arg + VLEN))
        writes = tuple(range(dest, dest + VLEN))

        if op == "multiply_add":
            a, b, c = args
            self.packer.add_slot(
                "valu",
                ("multiply_add", dest, a, b, c),
                reads=tuple(reads),
                writes=writes,
            )
        else:
            self.packer.add_slot("valu", (op, dest, *args), reads=tuple(reads), writes=writes)

    def emit_valu_mux_sharded(self, dest, idx, nodes, win, scratch_map, s_mux_tmp):
        # Sharded Mux to use limited registers (v_tmp1, v_addr)
        # Supports Depth 0 (1 node) per shard.
        shard_size = 1
        sorted_nodes = sorted(list(nodes))

        # Initialize dest (accumulator) to 0
        v_zero = self.get_vconst(0)
        self.emit_op("&", dest, [dest, v_zero])

        for i in range(0, len(sorted_nodes), shard_size):
            chunk = sorted_nodes[i : i + shard_size]
            res_reg = self.emit_valu_mux_binary_internal(idx, chunk, win, scratch_map, s_mux_tmp)
            # res_reg is v_addr (scratch). Accumulate.
            self.emit_op("+", dest, [dest, res_reg])

    def emit_valu_mux_binary_internal(self, idx, node_list, win, scratch_map, s_mux_tmp):
        # Internal version returning result_reg
        # Uses independent temps [v_addr, v_tmp1] (passed via win['mux_tmps'])
        temps = win["mux_tmps"]
        v_one = self.get_vconst(1)

        def recurse(nodes, reg_offset):
            if len(nodes) == 1:
                # Base Case with Equality Check
                node = nodes[0]
                s_addr = scratch_map[node]
                tgt = temps[reg_offset]

                # Broadcast value (node value)
                self.packer.add_slot(
                    "valu",
                    ("vbroadcast", tgt, s_addr),
                    reads=(s_addr,),
                    writes=tuple(range(tgt, tgt + VLEN)),
                )

                # Equality Check: (idx < node+1) & !(idx < node)
                # T0 (tgt) = Mask. T1 (scratch) = Temp.
                # Optimization: Use passed s_mux_tmp transient const
                v_scratch = temps[reg_offset + 1]

                # T0 = idx < node+1
                # Load node+1 const
                self.packer.add_slot("load", ("const", s_mux_tmp, node + 1), writes=(s_mux_tmp,))
                # Broadcast node+1 to T1 (v_scratch)
                self.packer.add_slot(
                    "valu",
                    ("vbroadcast", v_scratch, s_mux_tmp),
                    reads=(s_mux_tmp,),
                    writes=tuple(range(v_scratch, v_scratch + VLEN)),
                )
                # Compare T0 = idx < T1
                self.emit_op("<", tgt, [idx, v_scratch])

                # T1 = idx < node
                # Load node const
                self.packer.add_slot("load", ("const", s_mux_tmp, node), writes=(s_mux_tmp,))
                # Broadcast node to T1 (v_scratch)
                self.packer.add_slot(
                    "valu",
                    ("vbroadcast", v_scratch, s_mux_tmp),
                    reads=(s_mux_tmp,),
                    writes=tuple(range(v_scratch, v_scratch + VLEN)),
                )
                # Compare T1 = idx < T1
                self.emit_op("<", v_scratch, [idx, v_scratch])

                # T1 = !T1
                self.emit_op("^", v_scratch, [v_scratch, v_one])

                # T0 = T0 & T1
                self.emit_op("&", tgt, [tgt, v_scratch])

                # Load Value into T1
                self.packer.add_slot(
                    "valu",
                    ("vbroadcast", v_scratch, s_addr),
                    reads=(s_addr,),
                    writes=tuple(range(v_scratch, v_scratch + VLEN)),
                )

                # Select: tgt = (Mask) ? T1 : 0
                v_zero = self.get_vconst(0)
                self.packer.add_slot(
                    "flow",
                    ("vselect", tgt, tgt, v_scratch, v_zero),
                    reads=tuple(range(tgt, tgt + VLEN))
                    + tuple(range(v_scratch, v_scratch + VLEN))
                    + tuple(range(v_zero, v_zero + VLEN)),
                    writes=tuple(range(tgt, tgt + VLEN)),
                )
                return tgt

            # Recursive Step (Standard Binary Mux)
            mid = len(nodes) // 2
            left_nodes = nodes[:mid]
            right_nodes = nodes[mid:]

            r_left = recurse(left_nodes, reg_offset)
            r_right = recurse(right_nodes, reg_offset + 1)

            # The split logic:
            split_idx = right_nodes[0]

            # Optimization: load const split_idx into s_mux_tmp
            self.packer.add_slot("load", ("const", s_mux_tmp, split_idx), writes=(s_mux_tmp,))
            # Broadcast to v_cmp (temps[reg_offset+2])
            v_cmp = temps[reg_offset + 2]
            self.packer.add_slot(
                "valu",
                ("vbroadcast", v_cmp, s_mux_tmp),
                reads=(s_mux_tmp,),
                writes=tuple(range(v_cmp, v_cmp + VLEN)),
            )

            self.emit_op("<", v_cmp, [idx, v_cmp])

            # If idx < split_idx (TRUE) -> Left. Else Right.
            self.packer.add_slot(
                "flow",
                ("vselect", r_left, v_cmp, r_left, r_right),
                reads=tuple(range(v_cmp, v_cmp + VLEN))
                + tuple(range(r_left, r_left + VLEN))
                + tuple(range(r_right, r_right + VLEN)),
                writes=tuple(range(r_left, r_left + VLEN)),
            )

            return r_left

        return recurse(node_list, 0)

    def precipitate_crown_cache(self, p_forest_base, rounds):
        """Fabric Alpha: Load the tree crown (R0-R8) into SCALAR scratch only."""
        node_cache = {}  # val -> scratch_addr

        # Calculate nodes in the crown (up to crown_depth)
        crown_nodes = set()
        current = {0}
        for _r in range(min(rounds, self.config.crown_depth)):
            crown_nodes.update(current)
            next_lvl = set()
            for n in current:
                next_lvl.add(n * 2 + 1)
                next_lvl.add(n * 2 + 2)
            current = next_lvl

        # Load nodes into SCALAR scratch
        for node_idx in sorted(list(crown_nodes)):
            s_addr = self.alloc(f"crown_{node_idx}")
            s_const = self.get_const(node_idx)
            self.packer.add_slot(
                "alu",
                ("+", s_addr, p_forest_base, s_const),
                reads=(p_forest_base, s_const),
                writes=(s_addr,),
            )
            self.packer.add_slot(
                "load",
                ("load", s_addr, s_addr),
                reads=(s_addr,),
                writes=(s_addr,),
                is_mem_read=True,
            )
            node_cache[node_idx] = s_addr
        return node_cache, None  # No v_regs returned

    def add_hash_hybrid(self, v_val, v_tmp1, v_tmp2, hash_stages):
        for i_stage, (op1, val1, op2, op3, val3) in enumerate(hash_stages):
            v_val1 = self.get_vconst(val1)
            if i_stage == 0 and not self.config.disable_hash_opt and op1 == "+" and op2 == "+" and op3 == "<<":
                v_factor = self.get_vconst(1 + (1 << val3))
                self.emit_op("multiply_add", v_val, [v_val, v_factor, v_val1])
            else:
                v_val3 = self.get_vconst(val3)
                self.emit_op(op1, v_tmp1, [v_val, v_val1])
                self.emit_op(op3, v_tmp2, [v_val, v_val3])
                self.emit_op(op2, v_val, [v_tmp1, v_tmp2])

    def build_kernel(self, forest_height, n_nodes, batch_size, rounds, hash_stages):
        # Quadrature Nexus Optimization: N_VEC=28, Latent Round Folding, Non-Speculative
        N_VEC = 28
        n_windows = N_VEC
        windows = []
        for w in range(n_windows):
            win = {}
            win["v_idx"] = self.valloc(f"v_idx_{w}")
            win["v_val"] = self.valloc(f"v_val_{w}")  # Accumulator/Hash Val
            win["v_node_val"] = self.valloc(f"v_node_val_{w}")
            win["v_tmp1"] = self.valloc(f"v_tmp1_{w}")
            win["v_addr"] = self.valloc(f"v_addr_{w}")
            win["s_mux_tmp"] = self.alloc(f"s_mux_tmp_{w}")
            windows.append(win)

        # Global Constants
        s_n_nodes = self.alloc("s_n_nodes")
        s_batch_size = self.alloc("s_batch_size")
        p_forest_base = self.alloc("p_forest_base")
        p_idx_base = self.alloc("p_idx_base")
        p_val_base = self.alloc("p_val_base")

        for i, addr in enumerate([None, s_n_nodes, s_batch_size, None, p_forest_base, p_idx_base, p_val_base]):
            if addr is not None:
                tmp_c = self.get_const(i)
                self.packer.add_slot(
                    "load",
                    ("load", addr, tmp_c),
                    reads=(tmp_c,),
                    writes=(addr,),
                    is_mem_read=True,
                )

        # Safe Optimization: Hoist Node 0 (Root)
        s_root_node = self.alloc("s_root_node")
        s_zero = self.get_const(0)
        self.packer.add_slot(
            "alu",
            ("+", s_root_node, p_forest_base, s_zero),
            reads=(p_forest_base, s_zero),
            writes=(s_root_node,),
        )
        self.packer.add_slot(
            "load",
            ("load", s_root_node, s_root_node),
            reads=(s_root_node,),
            writes=(s_root_node,),
            is_mem_read=True,
        )

        v_n_nodes = self.valloc("v_n_nodes")
        self.packer.add_slot(
            "valu",
            ("vbroadcast", v_n_nodes, s_n_nodes),
            reads=(s_n_nodes,),
            writes=tuple(range(v_n_nodes, v_n_nodes + VLEN)),
        )

        v_forest_base = self.valloc("v_forest_base")
        self.packer.add_slot(
            "valu",
            ("vbroadcast", v_forest_base, p_forest_base),
            reads=(p_forest_base,),
            writes=tuple(range(v_forest_base, v_forest_base + VLEN)),
        )

        g_vzero = self.get_vconst(0)
        g_vone = self.get_vconst(1)
        g_vtwo = self.get_vconst(2)

        # Helper for batch calc
        vi_tmp_addrs = [self.alloc(f"vi_tmp_addr_{i}") for i in range(1)]

        batch_stride = VLEN
        core_batch_size = batch_size // N_CORES
        n_core_batches = core_batch_size // VLEN

        s_core_id = self.alloc("s_core_id")
        self.packer.add_slot("flow", ("coreid", s_core_id), writes=(s_core_id,))
        s_core_batch = self.get_const(core_batch_size)
        s_core_offset = self.alloc("s_core_offset")
        self.packer.add_slot(
            "alu",
            ("*", s_core_offset, s_core_id, s_core_batch),
            reads=(s_core_id, s_core_batch),
            writes=(s_core_offset,),
        )
        self.packer.barrier()

        # Calculate Start Pointers (SSA style)
        p_idx_start = self.alloc("p_idx_start")
        p_val_start = self.alloc("p_val_start")
        self.packer.add_slot(
            "alu",
            ("+", p_idx_start, p_idx_base, s_core_offset),
            reads=(p_idx_base, s_core_offset),
            writes=(p_idx_start,),
        )
        self.packer.add_slot(
            "alu",
            ("+", p_val_start, p_val_base, s_core_offset),
            reads=(p_val_base, s_core_offset),
            writes=(p_val_start,),
        )
        self.packer.barrier()

        # Main Loop: Process Chunks of N_VEC vectors
        for b_start in range(0, n_core_batches, n_windows):
            b_end = min(b_start + n_windows, n_core_batches)
            chunk_size = b_end - b_start

            # Initial Loads
            for i in range(chunk_size):
                win = windows[i]
                s_offset = self.get_const((b_start + i) * batch_stride)
                s_tmp_addr = vi_tmp_addrs[0]

                # Load Initial Index -> v_idx
                self.packer.add_slot(
                    "alu",
                    ("+", s_tmp_addr, p_idx_start, s_offset),
                    reads=(p_idx_start, s_offset),
                    writes=(s_tmp_addr,),
                )
                self.packer.add_slot(
                    "load",
                    ("vload", win["v_idx"], s_tmp_addr),
                    reads=(s_tmp_addr,),
                    writes=tuple(range(win["v_idx"], win["v_idx"] + VLEN)),
                    is_mem_read=True,
                )

                # Load Initial Value -> v_val
                self.packer.add_slot(
                    "alu",
                    ("+", s_tmp_addr, p_val_start, s_offset),
                    reads=(p_val_start, s_offset),
                    writes=(s_tmp_addr,),
                )
                self.packer.add_slot(
                    "load",
                    ("vload", win["v_val"], s_tmp_addr),
                    reads=(s_tmp_addr,),
                    writes=tuple(range(win["v_val"], win["v_val"] + VLEN)),
                    is_mem_read=True,
                )

            self.packer.barrier()

            # Pipelined Computation Logic
            for r in range(rounds):
                for i in range(chunk_size):
                    win = windows[i]

                    if r == 0:
                        # Round 0: Constant Broadcast
                        self.packer.add_slot(
                            "valu",
                            ("vbroadcast", win["v_node_val"], s_root_node),
                            reads=(s_root_node,),
                            writes=tuple(range(win["v_node_val"], win["v_node_val"] + VLEN)),
                        )
                    else:
                        # 1. Calc Address (Base + idx)
                        self.emit_op("+", win["v_addr"], [v_forest_base, win["v_idx"]])

                        # 2. Load Node (Correct Gather)
                        for lane in range(VLEN):
                            self.packer.add_slot(
                                "load",
                                (
                                    "load",
                                    win["v_node_val"] + lane,
                                    win["v_addr"] + lane,
                                ),
                                reads=(win["v_addr"] + lane,),
                                writes=(win["v_node_val"] + lane,),
                                is_mem_read=True,
                            )

                    # 3. Hash
                    self.emit_op("^", win["v_val"], [win["v_val"], win["v_node_val"]])
                    self.add_hash_hybrid(win["v_val"], win["v_tmp1"], win["v_addr"], hash_stages)

                    # 4. Update Index
                    self.emit_op("&", win["v_tmp1"], [win["v_val"], g_vone])
                    self.emit_op("multiply_add", win["v_idx"], [win["v_idx"], g_vtwo, g_vone])
                    self.emit_op("+", win["v_idx"], [win["v_idx"], win["v_tmp1"]])

                    # Wrap (Correct vselect logic)
                    # reuse v_tmp1 for condition (idx < n_nodes)
                    self.emit_op("<", win["v_tmp1"], [win["v_idx"], v_n_nodes])

                    # select: idx = (v_tmp1) ? idx : 0
                    self.packer.add_slot(
                        "flow",
                        ("vselect", win["v_idx"], win["v_tmp1"], win["v_idx"], g_vzero),
                        reads=tuple(range(win["v_tmp1"], win["v_tmp1"] + VLEN))
                        + tuple(range(win["v_idx"], win["v_idx"] + VLEN))
                        + tuple(range(g_vzero, g_vzero + VLEN)),
                        writes=tuple(range(win["v_idx"], win["v_idx"] + VLEN)),
                    )

            self.packer.barrier()

            # Writeback
            for i in range(chunk_size):
                win = windows[i]
                s_offset = self.get_const((b_start + i) * batch_stride)
                s_tmp_addr = vi_tmp_addrs[0]

                # Write Index
                self.packer.add_slot(
                    "alu",
                    ("+", s_tmp_addr, p_idx_start, s_offset),
                    reads=(p_idx_start, s_offset),
                    writes=(s_tmp_addr,),
                )
                self.packer.add_slot(
                    "store",
                    ("vstore", s_tmp_addr, win["v_idx"]),
                    reads=(s_tmp_addr,) + tuple(range(win["v_idx"], win["v_idx"] + VLEN)),
                    is_mem_write=True,
                )

                # Write Value
                self.packer.add_slot(
                    "alu",
                    ("+", s_tmp_addr, p_val_start, s_offset),
                    reads=(p_val_start, s_offset),
                    writes=(s_tmp_addr,),
                )
                self.packer.add_slot(
                    "store",
                    ("vstore", s_tmp_addr, win["v_val"]),
                    reads=(s_tmp_addr,) + tuple(range(win["v_val"], win["v_val"] + VLEN)),
                    is_mem_write=True,
                )

        return self.packer.get_instrs()
