"""Shared response shape validation; no artistic quality claims."""
def fields(value, limits):
    if not isinstance(value,dict) or set(value)!=set(limits):
        raise ValueError("Unexpected creative fields")
    for k,n in limits.items():
        if not isinstance(value[k],str) or not value[k].strip() or len(value[k])>n:
            raise ValueError("Invalid creative field: "+k)
    return value
