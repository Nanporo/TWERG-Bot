import math

LON_SCALE, LON_OFF =  161.4957, -19262.5674
LAT_SCALE, LAT_OFF = -9012.2994,   4120.8375

def to_proj(lon, lat):
    x = LON_SCALE * lon + LON_OFF
    y = LAT_SCALE * math.log(math.tan(math.pi/4 + lat*math.pi/360)) + LAT_OFF
    return x, y

def to_lonlat(x, y):
    lon = (x - LON_OFF) / LON_SCALE
    lat = (math.atan(math.exp((y - LAT_OFF) / LAT_SCALE)) - math.pi/4) * 360 / math.pi
    return lon, lat

x, y = to_proj(121.5, 25.0)
print(to_lonlat(x, y))
