"""MoE submission template."""

TEMPLATE = """\
import os,torch,sys
from task import input_t,output_t
from aiter.fused_moe import fused_moe as fm
from aiter import ActivationType as at,QuantType as qt
from reference import ref_kernel

os.environ["AITER_USE_NT"]="$USE_NT"
_ks_table=$KSPLIT_TABLE
_default_ks="$DEFAULT_KSPLIT"

def _set_ksplit(e, d, bs):
    key=f"{e}_{d}_{bs}"
    ks=str(_ks_table.get(key, _default_ks))
    if ks=="0":
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG",None)
        os.environ.pop("AITER_KSPLIT",None)
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"]="1"
        os.environ["AITER_KSPLIT"]=ks

def custom_kernel(data:input_t)->output_t:
    hs,w1,w2,w1s,w2s,w1sh,w2sh,w1ssh,w2ssh,tw,ti,cfg=data
    ne=w1sh.shape[0]
    _set_ksplit(ne, cfg["d_expert"], cfg["bs"])
    return fm(hs,w1sh,w2sh,tw,ti,expert_mask=None,activation=at.Silu,quant_type=qt.per_1x32,doweight_stage1=False,w1_scale=w1ssh,w2_scale=w2ssh,hidden_pad=cfg["d_hidden_pad"]-cfg["d_hidden"],intermediate_pad=cfg["d_expert_pad"]-cfg["d_expert"])
"""

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
