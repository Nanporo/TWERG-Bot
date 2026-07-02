import logging
import math
import os
import io
import uuid
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# Re-use utilities from dyfi_map
from cogs.dyfi_map import TOPO_LOCAL, load_topo, CDI_MAP, cdi_style

def distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def simulate_pga(mag, depth, lon, lat, fault_type, target_lon, target_lat):
    D = distance(lat, lon, target_lat, target_lon)
    R = math.sqrt(D**2 + depth**2)
    R = max(R, 3.0)
    log_pga = -0.01 + 0.6 * mag - 0.005 * R - math.log10(R)
    if fault_type == '逆斷層':
        log_pga += 0.1
    elif fault_type == '正斷層':
        log_pga -= 0.05
    return 10 ** log_pga

def pga_to_cdi(pga):
    if pga < 0.8: return 0.0
    elif pga < 2.5: return 0.35 + (pga - 0.8) / (2.5 - 0.8) * (1.1 - 0.35)
    elif pga < 8.0: return 1.1 + (pga - 2.5) / (8.0 - 2.5) * (1.9 - 1.1)
    elif pga < 25.0: return 1.9 + (pga - 8.0) / (25.0 - 8.0) * (2.8 - 1.9)
    elif pga < 80.0: return 2.8 + (pga - 25.0) / (80.0 - 25.0) * (3.7 - 2.8)
    elif pga < 140.0: return 3.7 + (pga - 80.0) / (140.0 - 80.0) * (4.35 - 3.7)
    elif pga < 250.0: return 4.35 + (pga - 140.0) / (250.0 - 140.0) * (4.85 - 4.35)
    elif pga < 400.0: return 4.85 + (pga - 250.0) / (400.0 - 250.0) * (5.55 - 4.85)
    elif pga < 800.0: return 5.55 + (pga - 400.0) / (800.0 - 400.0) * (6.3 - 5.55)
    else: return min(7.0, 6.3 + (pga - 800.0) / 1000.0 * (7.0 - 6.3))

def render_emulator_map_pil(mag, depth, lon, lat, fault_type):
    topo = load_topo()
    scale = topo['transform']['scale']
    translate = topo['transform']['translate']
    arcs = topo['arcs']

    decoded_arcs = []
    for arc in arcs:
        x, y = 0, 0
        decoded = []
        for point in arc:
            x += point[0]
            y += point[1]
            decoded.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        decoded_arcs.append(decoded)

    lines = []
    matsu_x_list, matsu_y_list = [], []
    kinmen_x_list, kinmen_y_list = [], []
    penghu_x_list, penghu_y_list = [], []

    for geom in topo['objects']['towns']['geometries']:
        props = geom.get('properties', {})
        county = props.get('COUNTYNAME', '')
        
        geom_lines = []
        if geom['type'] == 'Polygon':
            for ring in geom['arcs']:
                line = []
                for arc_idx in ring:
                    arc = decoded_arcs[~arc_idx][::-1] if arc_idx < 0 else decoded_arcs[arc_idx]
                    line.extend(arc)
                geom_lines.append(line)
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['arcs']:
                for ring in poly:
                    line = []
                    for arc_idx in ring:
                        arc = decoded_arcs[~arc_idx][::-1] if arc_idx < 0 else decoded_arcs[arc_idx]
                        line.extend(arc)
                    geom_lines.append(line)
        
        if county == '金門縣':
            for line in geom_lines:
                for pt in line:
                    kinmen_x_list.append(pt[0])
                    kinmen_y_list.append(pt[1])
            continue
        elif county == '連江縣':
            for line in geom_lines:
                for pt in line:
                    matsu_x_list.append(pt[0])
                    matsu_y_list.append(pt[1])
            continue
        elif county == '澎湖縣':
            for line in geom_lines:
                for pt in line:
                    penghu_x_list.append(pt[0])
                    penghu_y_list.append(pt[1])
        
        is_main = county != '澎湖縣'
        # We need the original centroid for distance calculation
        orig_x_pts = [p[0] for line in geom_lines for p in line]
        orig_y_pts = [p[1] for line in geom_lines for p in line]
        cx = sum(orig_x_pts) / len(orig_x_pts) if orig_x_pts else 0
        cy = sum(orig_y_pts) / len(orig_y_pts) if orig_y_pts else 0

        lines.append({
            'is_main': is_main, 
            'county': county, 
            'coords': geom_lines,
            'orig_cx': cx,
            'orig_cy': cy
        })

    main_x = [pt[0] for item in lines if item['is_main'] for line in item['coords'] for pt in line]
    main_y = [pt[1] for item in lines if item['is_main'] for line in item['coords'] for pt in line]
    min_x, max_x = min(main_x), max(main_x)
    min_y, max_y = min(main_y), max(main_y)

    WGS_MIN_LON, WGS_MAX_LON = 120.036, 122.001
    WGS_MIN_LAT, WGS_MAX_LAT = 21.896, 25.300

    def merc_y(lat_deg):
        return math.log(math.tan(math.pi/4 + lat_deg * math.pi/360))

    penghu_offset_x = 0
    penghu_offset_y = 0
    if penghu_x_list:
        fake_cx = (min(penghu_x_list) + max(penghu_x_list)) / 2
        fake_cy = (min(penghu_y_list) + max(penghu_y_list)) / 2
        
        real_cx = min_x + (119.5664 - WGS_MIN_LON) / (WGS_MAX_LON - WGS_MIN_LON) * (max_x - min_x)
        my = merc_y(23.5711)
        my_max = merc_y(WGS_MAX_LAT)
        my_min = merc_y(WGS_MIN_LAT)
        real_cy = min_y + (my_max - my) / (my_max - my_min) * (max_y - min_y)
        
        penghu_offset_x = real_cx - fake_cx
        penghu_offset_y = real_cy - fake_cy

    for item in lines:
        if item['county'] == '澎湖縣':
            for line in item['coords']:
                for i in range(len(line)):
                    line[i] = (line[i][0] + penghu_offset_x, line[i][1] + penghu_offset_y)

    county_lines = []
    if 'counties' in topo['objects']:
        for geom in topo['objects']['counties']['geometries']:
            geom_lines = []
            if geom['type'] == 'Polygon':
                for ring in geom['arcs']:
                    line = []
                    for arc_idx in ring:
                        arc = decoded_arcs[~arc_idx][::-1] if arc_idx < 0 else decoded_arcs[arc_idx]
                        line.extend(arc)
                    geom_lines.append(line)
            elif geom['type'] == 'MultiPolygon':
                for poly in geom['arcs']:
                    for ring in poly:
                        line = []
                        for arc_idx in ring:
                            arc = decoded_arcs[~arc_idx][::-1] if arc_idx < 0 else decoded_arcs[arc_idx]
                            line.extend(arc)
                    geom_lines.append(line)
                    
            filtered_geom_lines = []
            for line in geom_lines:
                if not line: continue
                pt = line[0]
                is_kinmen = kinmen_x_list and (min(kinmen_x_list)-5 <= pt[0] <= max(kinmen_x_list)+5) and (min(kinmen_y_list)-5 <= pt[1] <= max(kinmen_y_list)+5)
                is_matsu = matsu_x_list and (min(matsu_x_list)-5 <= pt[0] <= max(matsu_x_list)+5) and (min(matsu_y_list)-5 <= pt[1] <= max(matsu_y_list)+5)
                if is_kinmen or is_matsu:
                    continue
                    
                is_penghu = penghu_x_list and (min(penghu_x_list)-5 <= pt[0] <= max(penghu_x_list)+5) and (min(penghu_y_list)-5 <= pt[1] <= max(penghu_y_list)+5)
                if is_penghu:
                    moved_line = [(p[0] + penghu_offset_x, p[1] + penghu_offset_y) for p in line]
                    filtered_geom_lines.append(moved_line)
                else:
                    filtered_geom_lines.append(line)
                    
            if filtered_geom_lines:
                county_lines.append(filtered_geom_lines)

    all_x = [pt[0] for item in lines for line in item['coords'] for pt in line]
    all_y = [pt[1] for item in lines for line in item['coords'] for pt in line]
    img_min_x, img_max_x = min(all_x), max(all_x)
    img_min_y, img_max_y = min(all_y), max(all_y)

    IMG_W = 800
    pad = 40
    scale_factor = (IMG_W - 2 * pad) / (img_max_x - img_min_x)
    IMG_H = int((img_max_y - img_min_y) * scale_factor) + 2 * pad

    def map_to_img(x, y):
        px = pad + (x - img_min_x) * scale_factor
        py = pad + (y - img_min_y) * scale_factor
        return px, py

    def lonlat_to_img(lon, lat):
        x = min_x + (lon - WGS_MIN_LON) / (WGS_MAX_LON - WGS_MIN_LON) * (max_x - min_x)
        my = merc_y(lat)
        my_max = merc_y(WGS_MAX_LAT)
        my_min = merc_y(WGS_MIN_LAT)
        y = min_y + (my_max - my) / (my_max - my_min) * (max_y - min_y)
        return map_to_img(x, y)
    
    def img_to_lonlat(x, y):
        mx = (x - pad) / scale_factor + img_min_x
        my = (y - pad) / scale_factor + img_min_y
        
        lon = (mx - min_x) / (max_x - min_x) * (WGS_MAX_LON - WGS_MIN_LON) + WGS_MIN_LON
        # Reverse merc_y
        # my_val = min_y + (my_max - merc_y(lat)) / (my_max - my_min) * (max_y - min_y)
        # my_val - min_y = (my_max - merc_y(lat)) / (my_max - my_min) * (max_y - min_y)
        merc_y_lat = my_max - (my - min_y) * (my_max - my_min) / (max_y - min_y)
        # merc_y_lat = math.log(math.tan(math.pi/4 + lat * math.pi/360))
        lat = (math.atan(math.exp(merc_y_lat)) - math.pi/4) * 360 / math.pi
        return lon, lat

    img = Image.new('RGBA', (IMG_W, IMG_H), "#0f1113")
    draw = ImageDraw.Draw(img)
    
    for item in lines:
        fill_color = "#1a1d20"
        outline_color = "#292e33"
        for line in item['coords']:
            px_line = [map_to_img(pt[0], pt[1]) for pt in line]
            if len(px_line) >= 3:
                draw.polygon(px_line, fill=fill_color, outline=outline_color)

    county_outline_color = "#3e454b"
    for geom_lines in county_lines:
        for line in geom_lines:
            px_line = [map_to_img(pt[0], pt[1]) for pt in line]
            if len(px_line) >= 2:
                draw.line(px_line, fill=county_outline_color, width=2)

    font_paths = [
        "fonts/Noto_Sans_TC/NotoSansTC-Regular.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "PingFang.ttc",
        "C:\\Windows\\Fonts\\msjh.ttc",
        "msjh.ttc"
    ]
    font_title = font_time = font_intensity = font_legend = font_legend_title = None
    for path in font_paths:
        try:
            font_title = ImageFont.truetype(path, 36)
            font_time = ImageFont.truetype(path, 20)
            font_intensity = ImageFont.truetype(path, 16)
            font_legend = ImageFont.truetype(path, 14)
            font_legend_title = ImageFont.truetype(path, 16)
            break
        except Exception:
            continue
            
    if font_title is None:
        font_title = ImageFont.load_default()
        font_time = ImageFont.load_default()
        font_intensity = ImageFont.load_default()
        font_legend = ImageFont.load_default()
        font_legend_title = ImageFont.load_default()

    draw.text((25, 25), " 地震模擬", fill="#ffffff", font=font_title)

    current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    time_text = f"M{mag}  深度 {depth}km\n{fault_type}\n經度 {lon} 緯度 {lat}\n模擬時間 {current_time}"
    
    if hasattr(draw, 'multiline_textbbox'):
        text_bbox = draw.multiline_textbbox((0, 0), time_text, font=font_time)
        text_h = text_bbox[3] - text_bbox[1]
    else:
        _, text_h = draw.textsize(time_text, font=font_time)
        
    draw.multiline_text((25, IMG_H - text_h - 25), time_text, fill="#cccccc", font=font_time)

    # 繪製各鄉鎮震度
    for item in lines:
        cx, cy = item['orig_cx'], item['orig_cy']
        px, py = map_to_img(cx, cy)
        # Apply penghu offset if needed
        if item['county'] == '澎湖縣':
            px, py = map_to_img(cx + penghu_offset_x, cy + penghu_offset_y)
        
        # We need real lon/lat for distance calculation
        # However, orig_cx/cy are in pseudo coordinates. We need to convert them to WGS84
        t_lon, t_lat = img_to_lonlat(pad + (cx - img_min_x) * scale_factor, pad + (cy - img_min_y) * scale_factor)
        
        pga = simulate_pga(mag, depth, lon, lat, fault_type, t_lon, t_lat)
        cdi = pga_to_cdi(pga)
        
        if cdi >= 0.35:
            col, grade, label = cdi_style(cdi)
            # Draw dot
            rpx = 12
            draw.ellipse((px - rpx, py - rpx, px + rpx, py + rpx), fill=col, outline='white', width=1)
            
            grade_str = str(grade).replace('弱', '-').replace('強', '+')
            text_col = '#1a1a1a' if cdi < 5.55 else 'white'
            
            if hasattr(draw, 'textbbox'):
                bbox = draw.textbbox((0, 0), grade_str, font=font_intensity)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            else:
                tw, th = draw.textsize(grade_str, font=font_intensity)
                
            # offset roughly to center
            draw.text((px - tw/2, py - th/2 - 2), grade_str, fill=text_col, font=font_intensity)

    # 繪製震央 ❌
    epx, epy = lonlat_to_img(lon, lat)
    draw.line((epx-8, epy-8, epx+8, epy+8), fill="#ff3333", width=4)
    draw.line((epx-8, epy+8, epx+8, epy-8), fill="#ff3333", width=4)

    # 繪製右下角圖例
    leg = [(col, grade, label) for maxc, col, grade, label in CDI_MAP if maxc > 0.35]
    leg_w = 100
    leg_h = len(leg) * 20 + 30
    leg_x = IMG_W - leg_w - 20
    leg_y = IMG_H - leg_h - 20
    
    draw.rectangle((leg_x, leg_y, leg_x + leg_w, leg_y + leg_h), fill=(13, 14, 17, 230), outline='#1a1a1a', width=1)
    
    title_bbox = draw.textbbox((0, 0), "模擬震度", font=font_legend_title) if hasattr(draw, 'textbbox') else (0, 0, *draw.textsize("模擬震度", font=font_legend_title))
    draw.text((leg_x + (leg_w - (title_bbox[2]-title_bbox[0]))/2, leg_y + 8), "模擬震度", fill="#aaaaaa", font=font_legend_title)
    
    for i, (col, grade, label) in enumerate(leg):
        iy = leg_y + leg_h - 20 - i * 20
        draw.ellipse((leg_x + 10, iy + 4, leg_x + 18, iy + 12), fill=col, outline='#404040', width=1)
        draw.text((leg_x + 26, iy + 2), str(grade), fill="#e5e5e5", font=font_legend)
        draw.text((leg_x + 60, iy + 2), str(label), fill="#888888", font=font_legend)

    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output

if __name__ == '__main__':
    out = render_emulator_map_pil(6.0, 10, 121.5, 24.0, '逆斷層')
    with open('test_emulator.png', 'wb') as f:
        f.write(out.read())
    logging.info("Done")
