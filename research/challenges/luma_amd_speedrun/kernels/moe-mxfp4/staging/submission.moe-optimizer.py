import os,torch,sys
from task import input_t,output_t
from aiter.fused_moe import fused_moe as fm
from aiter import ActivationType as at,QuantType as qt
from reference import ref_kernel

# Set performance hints
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

def custom_kernel(data:input_t)->output_t:
    (
        hs, w1, w2, w1s, w2s, 
        w1sh, w2sh, w1ssh, w2ssh, 
        tw, ti, cfg
    ) = data
    
    ne=w1sh.shape[0]
    bs = cfg["bs"]
    
    estimated_m = bs / ne
    if estimated_m < 10:
        os.environ["AITER_KSPLIT"] = "4"
    elif estimated_m < 30:
        os.environ["AITER_KSPLIT"] = "2"
    else:
        os.environ["AITER_KSPLIT"] = "0"
        
    return fm(
        hs, w1sh, w2sh, tw, ti,
        expert_mask=None,
        activation=at.Silu,
        quant_type=qt.per_1x32,
        doweight_stage1=False,
        w1_scale=w1ssh,
        w2_scale=w2ssh,
        hidden_pad=cfg["d_hidden_pad"]-cfg["d_hidden"],
        intermediate_pad=cfg["d_expert_pad"]-cfg["d_expert"]
    )
