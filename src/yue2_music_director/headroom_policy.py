"""Shared conservative attenuation policy; never infer clipping repair."""
import math

TARGET_DBTP=-1.05
CEILING_DBTP=-1.0
MAX_ATTENUATION_DB=1.5


def gain_for_true_peak(tp):
    if type(tp) not in (int,float) or not math.isfinite(tp) or not CEILING_DBTP<tp<=0:
        raise ValueError("Not a peak-only attenuation candidate")
    gain=math.floor((TARGET_DBTP-tp)*100+1e-8)/100
    if not -MAX_ATTENUATION_DB<=gain<0:
        raise ValueError("Headroom correction exceeds bounded gain budget")
    return gain
