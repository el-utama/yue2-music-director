"""Shared response shape validation; no artistic quality claims."""
def fields(value, limits):
    if not isinstance(value,dict) or set(value)!=set(limits):
        raise ValueError("Unexpected creative fields")
    for k,n in limits.items():
        if not isinstance(value[k],str) or not value[k].strip() or len(value[k])>n:
            raise ValueError("Invalid creative field: "+k)
    return value

def object_schema(limits, enums=None):
    """Wire schema mirrors local field names and types; local limits stay authoritative."""
    enums=enums or {}
    props={k:{"type":"string",**({"enum":enums[k]} if k in enums else {})} for k in limits}
    return {"type":"object","properties":props,"required":list(limits),"additionalProperties":False}
