#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

import torch
from aiter.mla import mla_decode
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    return mla_decode(q, kv_data, qo_indptr, kv_indptr, config)
