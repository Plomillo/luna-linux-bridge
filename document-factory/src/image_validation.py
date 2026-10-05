from __future__ import annotations
import re
def validate_image_metadata(width,height,dpi_x,dpi_y,c):
    width=int(width); height=int(height); failures=[]; unknown=[]
    if c.get("minimum_dpi") is not None:
        if dpi_x is None or dpi_y is None: unknown.append("DPI_METADATA_MISSING")
        elif float(dpi_x)<float(c["minimum_dpi"]) or float(dpi_y)<float(c["minimum_dpi"]): failures.append("DPI_BELOW_MINIMUM")
    if c.get("exact_pixel_dimensions"):
        e=c["exact_pixel_dimensions"]
        if [width,height]!=[int(e[0]),int(e[1])]: failures.append("PIXEL_DIMENSIONS_NOT_EXACT")
    elif c.get("minimum_pixel_dimensions"):
        e=c["minimum_pixel_dimensions"]
        if width<int(e[0]) or height<int(e[1]): failures.append("PIXEL_DIMENSIONS_BELOW_MINIMUM")
    elif c.get("stated_dimensions"):
        m=re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*",str(c["stated_dimensions"]))
        unknown.append("STATED_DIMENSIONS_SEMANTICS_NOT_INFERRED"+(f":{m.group(1)}x{m.group(2)}" if m else ""))
    return {"status":"FAIL" if failures else ("UNKNOWN" if unknown else "PASS"),"failures":failures,"unknown":unknown,"dpi_and_pixel_dimensions_are_distinct":True}
