import collections
from problem import SLOT_LIMITS, SCRATCH_SIZE, VLEN, N_CORES
from dataclasses import dataclass

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
    crown_depth: int = 5

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
            self.packer.add_slot("valu", ("vbroadcast", v_addr, const_addr), reads=(const_addr,), writes=tuple(range(v_addr, v_addr+VLEN)))
            self.global_vconst_map[val] = v_addr
        return self.global_vconst_map[val]

    def emit_op(self, op, dest, args):
        reads = []
        for arg in args:
            reads.extend(range(arg, arg+VLEN))
        writes = tuple(range(dest, dest+VLEN))

        if op == "multiply_add":
            a, b, c = args
            self.packer.add_slot("valu", ("multiply_add", dest, a, b, c), reads=tuple(reads), writes=writes)
        else:
            self.packer.add_slot("valu", (op, dest, *args), reads=tuple(reads), writes=writes)

    def emit_valu_mux_binary(self, dest, idx, nodes, win, scratch_map):
        # Recursive Binary Muxing (Tree Reduction) with Lazy Broadcast
        sorted_nodes = sorted(list(nodes))
        temps = win['mux_tmps']

        def recurse(node_list, reg_offset):
            # Base Case
            if len(node_list) == 1:
                node_idx = node_list[0]
                s_addr = scratch_map[node_idx]
                target_reg = temps[reg_offset]
                # Broadcast on demand from scalar scratch
                self.packer.add_slot("valu", ("vbroadcast", target_reg, s_addr), reads=(s_addr,), writes=tuple(range(target_reg, target_reg+VLEN)))
                return target_reg

            # Recursive Step
            mid = len(node_list) // 2
            left_nodes = node_list[:mid]
            right_nodes = node_list[mid:]
            split_idx = right_nodes[0]

            # Recurse
            # Reuse stack: Left uses [offset...], Right uses [offset+1...]
            # Note: Depth D needs D regs.
            # If D=6, we need 6 regs.
            # Lazy broadcast uses temps[reg_offset] as scratch for broadcast too.

            r_left = recurse(left_nodes, reg_offset)
            r_right = recurse(right_nodes, reg_offset + 1)

            # Compare
            v_split = self.get_vconst(split_idx)
            v_cmp = temps[reg_offset + 2] # Need distinct reg for cmp?
            # Actually we can reuse a temp if disjoint life?
            # No, select uses r_left, r_right, cmp. All live.
            # We need +2.

            self.emit_op("<", v_cmp, [idx, v_split])

            # Select into r_left
            self.packer.add_slot("flow", ("vselect", r_left, v_cmp, r_left, r_right),
                reads=tuple(range(v_cmp, v_cmp+VLEN)) + tuple(range(r_left, r_left+VLEN)) + tuple(range(r_right, r_right+VLEN)),
                writes=tuple(range(r_left, r_left+VLEN)))

            return r_left

        result_reg = recurse(sorted_nodes, 0)

        # Reset dest to zero before accumulating? No, Mux produces ONE value.
        # But we are in a loop chunk doing multiple Muxes?
        # No, Crown Phase logic calls this once per chunk item per round?
        # NO. We removed the "Accumulate" logic.
        # Binary Mux produces the final node value for this round.
        # We should OVERWRITE dest with result_reg.

        if result_reg != dest:
            # Move result_reg to dest.
            # Using Add 0.
            v_zero = self.get_vconst(0)
            self.emit_op("+", dest, [result_reg, v_zero])

    def emit_valu_mux_sharded(self, dest, idx, nodes, win, scratch_map):
        # Sharded Mux to use limited registers (v_tmp1, v_addr)
        # Supports Depth 0 (1 node) per shard.
        shard_size = 1
        sorted_nodes = sorted(list(nodes))

        # Initialize dest (accumulator) to 0
        v_zero = self.get_vconst(0)
        self.emit_op("&", dest, [dest, v_zero])

        for i in range(0, len(sorted_nodes), shard_size):
            chunk = sorted_nodes[i : i + shard_size]
            res_reg = self.emit_valu_mux_binary_internal(idx, chunk, win, scratch_map)
            self.emit_op("+", dest, [dest, res_reg])

    def emit_valu_mux_binary_internal(self, idx, node_list, win, scratch_map):
         # Internal version returning result_reg
         # Uses 3 aliased temps: v_tmp1, v_addr, v_val_tmp
         temps = win['mux_tmps']
         v_one = self.get_vconst(1)

         def recurse(nodes, reg_offset):
             if len(nodes) == 1:
                 # Base Case with Equality Check
                 node = nodes[0]
                 s_addr = scratch_map[node]
                 tgt = temps[reg_offset]

                 # Broadcast value
                 self.packer.add_slot("valu", ("vbroadcast", tgt, s_addr), reads=(s_addr,), writes=tuple(range(tgt, tgt+VLEN)))

                 # Equality Check: (idx < node+1) & !(idx < node)
                 # T0 (tgt) = Mask. T1 (scratch) = Temp.
                 s_node = self.get_const(node)
                 s_node_plus_1 = self.get_const(node + 1)
                 v_scratch = temps[reg_offset + 1]

                 # T0 = idx < node+1
                 # Broadcast node+1 to T1 (v_scratch)
                 self.packer.add_slot("valu", ("vbroadcast", v_scratch, s_node_plus_1), reads=(s_node_plus_1,), writes=tuple(range(v_scratch, v_scratch+VLEN)))
                 # Compare T0 = idx < T1
                 self.emit_op("<", tgt, [idx, v_scratch])

                 # T1 = idx < node
                 # Broadcast node to T1 (v_scratch)
                 self.packer.add_slot("valu", ("vbroadcast", v_scratch, s_node), reads=(s_node,), writes=tuple(range(v_scratch, v_scratch+VLEN)))
                 # Compare T1 = idx < T1
                 self.emit_op("<", v_scratch, [idx, v_scratch])

                 # T1 = !T1
                 self.emit_op("^", v_scratch, [v_scratch, v_one])

                 # T0 = T0 & T1
                 self.emit_op("&", tgt, [tgt, v_scratch])

                 # Load Value into T1
                 self.packer.add_slot("valu", ("vbroadcast", v_scratch, s_addr), reads=(s_addr,), writes=tuple(range(v_scratch, v_scratch+VLEN)))

                 # Select: tgt = (Mask) ? T1 : 0
                 v_zero = self.get_vconst(0)
                 self.packer.add_slot("flow", ("vselect", tgt, tgt, v_scratch, v_zero),
                     reads=tuple(range(tgt, tgt+VLEN)) + tuple(range(v_scratch, v_scratch+VLEN)) + tuple(range(v_zero, v_zero+VLEN)),
                     writes=tuple(range(tgt, tgt+VLEN)))
                 return tgt

             # Recursive Step (Standard Binary Mux)
             mid = len(node_list) // 2
             left_nodes = node_list[:mid]
             right_nodes = node_list[mid:]
             split_idx = right_nodes[0]

             r_left = recurse(left_nodes, reg_offset)
             r_right = recurse(right_nodes, reg_offset + 1)

             v_split = self.get_vconst(split_idx)
             v_cmp = temps[reg_offset + 2]
             self.emit_op("<", v_cmp, [idx, v_split])

             self.packer.add_slot("flow", ("vselect", r_left, v_cmp, r_left, r_right),
                 reads=tuple(range(v_cmp, v_cmp+VLEN)) + tuple(range(r_left, r_left+VLEN)) + tuple(range(r_right, r_right+VLEN)),
                 writes=tuple(range(r_left, r_left+VLEN)))

             return r_left

         return recurse(node_list, 0)

    def precipitate_crown_cache(self, p_forest_base, rounds):
        """Fabric Alpha: Load the tree crown (R0-R8) into SCALAR scratch only."""
        node_cache = {} # val -> scratch_addr

        # Calculate nodes in the crown (up to crown_depth)
        crown_nodes = set()
        current = {0}
        for r in range(min(rounds, self.config.crown_depth)):
            crown_nodes.update(current)
            next_lvl = set()
            for n in current:
                next_lvl.add(n*2 + 1)
                next_lvl.add(n*2 + 2)
            current = next_lvl

        # Load nodes into SCALAR scratch
        for node_idx in sorted(list(crown_nodes)):
            s_addr = self.alloc(f"crown_{node_idx}")
            s_const = self.get_const(node_idx)
            self.packer.add_slot("alu", ("+", s_addr, p_forest_base, s_const), reads=(p_forest_base, s_const), writes=(s_addr,))
            self.packer.add_slot("load", ("load", s_addr, s_addr), reads=(s_addr,), writes=(s_addr,), is_mem_read=True)
            node_cache[node_idx] = s_addr

        return node_cache, None # No v_regs returned


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
        possible_indices = [set() for _ in range(rounds)]
        current_indices = {0}
        for r in range(rounds):
            next_indices = set()
            for idx in current_indices:
                possible_indices[r].add(idx)
                n1 = idx * 2 + 1
                n2 = idx * 2 + 2
                if n1 < n_nodes: next_indices.add(n1)
                if n2 < n_nodes: next_indices.add(n2)
            if not next_indices: next_indices = {0}
            current_indices = next_indices

        N_VEC = 32
        n_windows = N_VEC
        windows = []
        for w in range(n_windows):
            win = {}
            win['v_idx'] = self.valloc(f"v_idx_{w}")
            win['v_hash'] = self.valloc(f"v_hash_{w}")
            win['v_node_val'] = self.valloc(f"v_node_val_{w}")
            win['v_tmp1'] = self.valloc(f"v_tmp1_{w}")
            win['v_addr'] = self.valloc(f"v_addr_{w}")
            # v_val_tmp removed to fit scratch
            # Alias mux_tmps for Sharded Mux
            win['mux_tmps'] = [win['v_tmp1'], win['v_addr']]
            windows.append(win)

        # Global Constants loading (optimized)
        vi_tmp_addrs = [self.alloc(f"vi_tmp_addr_{i}") for i in range(1)] # Scalar alloc!
        # Wait, if N_VEC=32, we loop 32 times.
        # But we loop in chunks?

        # Re-calc constants
        s_n_nodes = self.alloc("s_n_nodes")
        s_batch_size = self.alloc("s_batch_size")
        p_forest_base = self.alloc("p_forest_base")
        p_idx_base = self.alloc("p_idx_base")
        p_val_base = self.alloc("p_val_base")

        for i, addr in enumerate([None, s_n_nodes, s_batch_size, None, p_forest_base, p_idx_base, p_val_base]):
            if addr is not None:
                tmp_c = self.get_const(i)
                self.packer.add_slot("load", ("load", addr, tmp_c), reads=(tmp_c,), writes=(addr,), is_mem_read=True)

        v_n_nodes = self.valloc("v_n_nodes")
        self.packer.add_slot("valu", ("vbroadcast", v_n_nodes, s_n_nodes), reads=(s_n_nodes,), writes=tuple(range(v_n_nodes, v_n_nodes+VLEN)))
        v_zero, v_one, v_two = self.get_vconst(0), self.get_vconst(1), self.get_vconst(2)

        batch_stride = VLEN
        core_batch_size = batch_size // N_CORES
        n_core_batches = core_batch_size // VLEN

        s_core_id = self.alloc("s_core_id")
        self.packer.add_slot("flow", ("coreid", s_core_id), writes=(s_core_id,))
        s_core_batch = self.get_const(core_batch_size)
        s_core_offset = self.alloc("s_core_offset")
        self.packer.add_slot("alu", ("*", s_core_offset, s_core_id, s_core_batch), reads=(s_core_id, s_core_batch), writes=(s_core_offset,))
        self.packer.add_slot("alu", ("+", p_idx_base, p_idx_base, s_core_offset), reads=(p_idx_base, s_core_offset), writes=(p_idx_base,))
        self.packer.add_slot("alu", ("+", p_val_base, p_val_base, s_core_offset), reads=(p_val_base, s_core_offset), writes=(p_val_base,))

        # Precipitate Crown Cache
        crown_nodes, crown_idxs = self.precipitate_crown_cache(p_forest_base, rounds)

        for b_start in range(0, n_core_batches, n_windows):
            b_end = min(b_start + n_windows, n_core_batches)
            chunk_size = b_end - b_start

            for i in range(chunk_size):
                win = windows[i]
                s_offset = self.get_const((b_start + i) * batch_stride)
                # s_tmp_addr needs to be private if multiple loads in parallel?
                # No, packer handles dependency?
                # But we use vi_tmp_addrs[0] repeatedly.
                # If barrier is removed, this aliases!
                # But we have barrier later.
                s_tmp_addr = vi_tmp_addrs[0]
                self.packer.add_slot("alu", ("+", s_tmp_addr, p_idx_base, s_offset), reads=(p_idx_base, s_offset), writes=(s_tmp_addr,))
                self.packer.add_slot("load", ("vload", win['v_idx'], s_tmp_addr), reads=(s_tmp_addr,), writes=tuple(range(win['v_idx'], win['v_idx']+VLEN)), is_mem_read=True)
                self.packer.add_slot("alu", ("+", s_tmp_addr, p_val_base, s_offset), reads=(p_val_base, s_offset), writes=(s_tmp_addr,))
                self.packer.add_slot("load", ("vload", win['v_hash'], s_tmp_addr), reads=(s_tmp_addr,), writes=tuple(range(win['v_hash'], win['v_hash']+VLEN)), is_mem_read=True)

            self.packer.barrier()

            for r in range(rounds):
                saved_scratch_ptr = self.scratch_ptr
                if r < self.config.crown_depth:
                    # Crown Phase: Tiered solid-state muxing
                    distinct_nodes = sorted(list(possible_indices[r]))
                    active_crown_nodes = {k: v for k, v in crown_nodes.items() if k in distinct_nodes}

                    for i in range(chunk_size):
                        self.emit_valu_mux_sharded(windows[i]['v_node_val'], windows[i]['v_idx'], active_crown_nodes, windows[i], crown_nodes)
                else:
                    for i in range(chunk_size):
                        win = windows[i]
                        v_idx, v_node_val = win['v_idx'], win['v_node_val']
                        for vi in range(VLEN):
                            vi_tmp_addr = win['v_addr'] + vi
                            self.packer.add_slot("alu", ("+", vi_tmp_addr, p_forest_base, v_idx + vi), reads=(p_forest_base, v_idx + vi), writes=(vi_tmp_addr,))
                            self.packer.add_slot("load", ("load", v_node_val + vi, vi_tmp_addr), reads=(vi_tmp_addr,), writes=(v_node_val + vi,), is_mem_read=True)

                for i in range(chunk_size):
                    win = windows[i]
                    v_idx, v_hash, v_node_val = win['v_idx'], win['v_hash'], win['v_node_val']
                    v_tmp1, v_tmp2 = win['v_tmp1'], win['v_node_val']
                    self.emit_op("^", v_hash, [v_hash, v_node_val])
                    self.add_hash_hybrid(v_hash, v_tmp1, v_tmp2, hash_stages)
                    self.emit_op("&", v_tmp1, [v_hash, v_one])
                    self.emit_op("multiply_add", v_idx, [v_idx, v_two, v_one])
                    self.emit_op("+", v_idx, [v_idx, v_tmp1])
                    self.emit_op("<", v_tmp1, [v_idx, v_n_nodes])
                    self.packer.add_slot("flow", ("vselect", v_idx, v_tmp1, v_idx, v_zero), reads=tuple(range(v_tmp1, v_tmp1+VLEN)) + tuple(range(v_idx, v_idx+VLEN)) + tuple(range(v_zero, v_zero+VLEN)), writes=tuple(range(v_idx, v_idx+VLEN)))

                self.packer.barrier()
                # self.packer.add_slot("flow", ("pause",))
                # self.packer.barrier()

                self.scratch_ptr = saved_scratch_ptr
                self.global_const_map.clear()
                self.global_vconst_map.clear()

            for i in range(chunk_size):
                win = windows[i]
                s_offset = self.get_const((b_start + i) * batch_stride)
                s_tmp_addr = vi_tmp_addrs[0]
                self.packer.add_slot("alu", ("+", s_tmp_addr, p_idx_base, s_offset), reads=(p_idx_base, s_offset), writes=(s_tmp_addr,))
                self.packer.add_slot("store", ("vstore", s_tmp_addr, win['v_idx']), reads=(s_tmp_addr,) + tuple(range(win['v_idx'], win['v_idx']+VLEN)), is_mem_write=True)
                self.packer.add_slot("alu", ("+", s_tmp_addr, p_val_base, s_offset), reads=(p_val_base, s_offset), writes=(s_tmp_addr,))
                self.packer.add_slot("store", ("vstore", s_tmp_addr, win['v_hash']), reads=(s_tmp_addr,) + tuple(range(win['v_hash'], win['v_hash']+VLEN)), is_mem_write=True)
        return self.packer.get_instrs()
