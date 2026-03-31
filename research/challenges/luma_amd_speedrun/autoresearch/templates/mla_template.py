"""MLA submission template."""

TEMPLATE = """\
import os,torch,ctypes,sys
from task import input_t,output_t
from aiter import dtypes as dt
import aiter
from reference import ref_kernel

os.environ["AITER_MLA_USE_PERSISTENT"]="1"
os.environ["AITER_USE_NT"]="1"

_splits_table=$SPLITS_TABLE
_default_splits=$DEFAULT_SPLITS
_fast_mode=$FAST_MODE
_kv_gran=$KV_GRANULARITY
_kv_format="$KV_FORMAT"
_c={}

def _bm(b,q,n,qd,kd,qi,ki,kl,ns):
    from aiter import get_mla_metadata_info_v1 as gi,get_mla_metadata_v1 as gv
    i=gi(b,q,n,qd,kd,is_sparse=False,fast_mode=_fast_mode,num_kv_splits=ns,intra_batch_mode=True)
    w=[torch.empty(s,dtype=t,device="cuda") for s,t in i]
    wm,wi,ws,ri,rf,rp=w
    gv(qi,ki,kl,n,1,True,wm,ws,wi,ri,rf,rp,page_size=1,kv_granularity=_kv_gran,max_seqlen_qo=q,uni_seqlen_qo=q,fast_mode=_fast_mode,max_split_per_batch=ns,intra_batch_mode=True,dtype_q=qd,dtype_kv=kd)
    return {"wm":wm,"wi":wi,"ws":ws,"ri":ri,"rf":rf,"rp":rp,"ns":ns}

def custom_kernel(data:input_t)->output_t:
    q,kd,qi,ki,cfg=data
    b,sl,nh=cfg["batch_size"],cfg["kv_seq_len"],cfg["num_heads"]
    qsl=cfg["q_seq_len"]
    
    # Metadata cache (STATIC ONLY)
    mkey = (qi.data_ptr(), ki.data_ptr(), b, sl, nh, qsl)
    if mkey not in _c:
        ns=_splits_table.get(f"{b}_{sl}_{nh}", _splits_table.get(f"{b}_{sl}", _default_splits))
        kl=(ki[1:]-ki[:-1]).to(torch.int32)
        kv_dt=dt.fp4x2 if _kv_format=="mxfp4" else torch.float8_e4m3fnuz
        _c[mkey]={"meta":_bm(b,qsl,nh,torch.bfloat16,kv_dt,qi,ki,kl,ns),"kl":kl,"idx":torch.arange(int(ki[-1].item()),dtype=torch.int32,device="cuda")}
    
    m=_c[mkey]
    mt=m["meta"]
    
    kf,ks=kd["mxfp4"] if _kv_format=="mxfp4" else kd["fp8"]
    k4=kf.view(kf.shape[0],1,1,kf.shape[-1])
    
    from aiter.mla import mla_decode_fwd as mf
    ot=torch.empty((q.shape[0],nh,512),dtype=torch.bfloat16,device="cuda")
    return mf(q.view(-1,nh,576),k4,ot,qi,ki,m["idx"],m["kl"],qsl,page_size=1,nhead_kv=1,sm_scale=1.0/(576**.5),q_scale=None,kv_scale=ks,num_kv_splits=mt["ns"],intra_batch_mode=True,work_meta_data=mt["wm"],work_indptr=mt["wi"],work_info_set=mt["ws"],reduce_indptr=mt["ri"],reduce_final_map=mt["rf"],reduce_partial_map=mt["rp"])
"""

DEFAULT_PARAMS = {
    "SPLITS_TABLE": {
        "4_1024": 4,
        "4_8192": 16,
        "32_1024": 8,
        "32_8192": 32,
        "128_8192": 32,
    },
    "DEFAULT_SPLITS": 16,
    "FAST_MODE": False,
    "KV_GRANULARITY": 16,
    "KV_FORMAT": "mxfp4",
}
