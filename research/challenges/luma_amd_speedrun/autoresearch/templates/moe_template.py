"""MoE submission template.

Parameters (JSON):
  ksplit_table: dict mapping "E_dexpert_bs" -> KSPLIT value (int)
                e.g. {"257_256_16": 4, "257_256_128": 2, ...}
  default_ksplit: str, fallback KSPLIT when shape not in table (default "0")
  use_bypass: bool, set AITER_BYPASS_TUNE_CONFIG=1 (default True)
  use_opus: bool, set AITER_USE_NT=1 (default True)
"""

TEMPLATE = '''\
import os,torch
from task import input_t,output_t
from aiter.fused_moe import fused_moe as fm
from aiter import ActivationType as at,QuantType as qt

os.environ["AITER_USE_NT"]="$USE_NT"
_ks_table=$KSPLIT_TABLE
_default_ks="$DEFAULT_KSPLIT"
_last_k=None

def _set_ksplit(e, d, bs):
    global _last_k
    key=f"{e}_{d}_{bs}"
    ks=str(_ks_table.get(key, _default_ks))
    if _last_k==ks:
        return
    _last_k=ks
    if ks=="0":
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG",None)
        os.environ.pop("AITER_KSPLIT",None)
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"]="1"
        os.environ["AITER_KSPLIT"]=ks

def custom_kernel(data:input_t)->output_t:
    hs,w1,w2,w1s,w2s,w1sh,w2sh,w1ssh,w2ssh,tw,ti,cfg=data
    ne=w1sh.shape[0]
    em=ti.numel()//ne
    _set_ksplit(ne, cfg["d_expert"], cfg["bs"])
    return fm(hs,w1sh,w2sh,tw,ti,expert_mask=None,activation=at.Silu,quant_type=qt.per_1x32,doweight_stage1=False,w1_scale=w1ssh,w2_scale=w2ssh,hidden_pad=cfg["d_hidden_pad"]-cfg["d_hidden"],intermediate_pad=cfg["d_expert_pad"]-cfg["d_expert"])
'''

# Default parameters for the template
DEFAULT_PARAMS = {
    "USE_NT": "1",
    "KSPLIT_TABLE": {
        "257_256_16": 4,
        "257_256_128": 2,
        "257_256_512": 0,
        "33_512_16": 2,
        "33_512_128": 2,
        "33_512_512": 0,
        "33_2048_512": 0,
    },
    "DEFAULT_KSPLIT": "2",
}

# Benchmark shapes from task.yml
SHAPES = [
    {"E": 257, "d_expert": 256, "bs": 16},
    {"E": 257, "d_expert": 256, "bs": 128},
    {"E": 257, "d_expert": 256, "bs": 512},
    {"E": 33, "d_expert": 512, "bs": 16},
    {"E": 33, "d_expert": 512, "bs": 128},
    {"E": 33, "d_expert": 512, "bs": 512},
    {"E": 33, "d_expert": 2048, "bs": 512},
]
