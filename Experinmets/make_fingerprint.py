from get_flashes import get_flashes
from calc_amp import amplitude

outpost, flashes = get_flashes()

#print(outpost, len(flashes))

#for flash in flashes:
#    flash["amplitude"] = amplitude(flash["distance"] * 1000)
#    print(
#        f"time={flash['time']:.2f}s "
#        f"lat={flash['lat']:.4f} "
#        f"lon={flash['lon']:.4f} "
#        f"distance={flash['distance']:.2f}km "
#        f"amplitude={flash['amplitude']:.3f}"
#    )