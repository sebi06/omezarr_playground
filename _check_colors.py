from czitools.metadata_tools.czi_metadata import CziMetadata

m = CziMetadata(r"f:\Github\omezarr_playground\data\CellDivision5D.czi")
ci = m.channelinfo
print("colors:", ci.colors)
print("names:", ci.names)
for i, c in enumerate(ci.colors):
    print(f"  ch{i}: raw={c!r}  -> [3:]={c[3:]!r}")
from czitools.metadata_tools.czi_metadata import CziMetadata

m = CziMetadata(r"f:\Github\omezarr_playground\data\CellDivision5D.czi")
ci = m.channelinfo
print("colors:", ci.colors)
print("names:", ci.names)
# show what [3:] produces
for i, c in enumerate(ci.colors):
    print(f"  ch{i}: raw={c!r}  -> [3:]={c[3:]!r}")
