def update_altitude_meter():
    alt_percentage = min(plane.y / 10000, 1)
    altitude_bar.position = (-0.8, -0.1 + (alt_percentage * 0.2))
    altitude_bar.scale_y = max(0.02, alt_percentage * 0.2)

def update_horizon():
    horizon.y = -0.3 + (plane.rotation_x / 90) * 0.05
    horizon.rotation_z = -(plane.rotation_y)

def update_radar():
    """Update radar display with enemies, sweep, and bearing information"""
    global enemy_markers, enemy_distance_texts
    
    if not radar_enabled:
        # Hide all radar elements
        for marker in enemy_markers:
            marker.visible = False
        for text in enemy_distance_texts:
            text.visible = False
        locked_marker.visible = False
        locked_marker_ring.visible = False
        return
    
    # Rotate radar sweep line
    radar_sweep.rotation_z += 120 * time.dt  # 2 rotations per second
    
    # Radar parameters
    radar_radius = 0.12  # Visual radius on screen
    radar_max_range = radar_range  # 5000m
    radar_center = Vec2(0.65, -0.35)
    
    # Clear old markers if count doesn't match
    if len(enemy_markers) != len(enemy_planes):
        for marker in enemy_markers:
            destroy(marker)
        for text in enemy_distance_texts:
            destroy(text)
        enemy_markers.clear()
        enemy_distance_texts.clear()
        
        # Create new markers
        for _ in enemy_planes:
            marker = Entity(
                parent=camera.ui, 
                model='circle', 
                color=color.red, 
                scale=0.012, 
                z=-0.22,
                visible=False
            )
            enemy_markers.append(marker)
            
            # Distance text for each enemy
            dist_text = Text(
                parent=camera.ui,
                text='',
                scale=0.8,
                color=color.red,
                origin=(0, 0),
                visible=False
            )
            enemy_distance_texts.append(dist_text)
    
    # Update enemy positions on radar
    for i, enemy in enumerate(enemy_planes):
        if i >= len(enemy_markers):
            continue
            
        # Calculate relative position
        relative_pos = enemy.position - plane.position
        distance_to_enemy = math.sqrt(relative_pos.x**2 + relative_pos.z**2)
        
        # Only show if within radar range
        if distance_to_enemy <= radar_max_range:
            # Calculate bearing (angle from north)
            angle = math.degrees(math.atan2(relative_pos.x, relative_pos.z))
            
            # Adjust for player's heading (rotate relative to player's facing)
            relative_angle = angle - plane.rotation_y
            angle_rad = math.radians(relative_angle)
            
            # Scale distance to radar display
            scaled_distance = (distance_to_enemy / radar_max_range) * radar_radius
            
            # Calculate screen position
            x_offset = scaled_distance * math.sin(angle_rad)
            y_offset = scaled_distance * math.cos(angle_rad)
            
            marker_pos = Vec2(
                radar_center.x + x_offset,
                radar_center.y + y_offset
            )
            
            # Update marker
            enemy_markers[i].position = (marker_pos.x, marker_pos.y, -0.22)
            enemy_markers[i].visible = True
            
            # Change color if this is the locked target
            if enemy == locked_target:
                enemy_markers[i].color = color.yellow
                enemy_markers[i].scale = 0.018
                
                # Update locked marker ring
                locked_marker.position = (marker_pos.x, marker_pos.y, -0.25)
                locked_marker.visible = True
                locked_marker_ring.position = (marker_pos.x, marker_pos.y, -0.26)
                locked_marker_ring.visible = True
                # Pulsing effect
                pulse = 0.03 + 0.01 * math.sin(time.time() * 5)
                locked_marker_ring.scale = pulse
                locked_marker_ring.color = color.rgba(255, 0, 0, 100 + 50 * math.sin(time.time() * 5))
            else:
                enemy_markers[i].color = color.red
                enemy_markers[i].scale = 0.012
            
            # Update distance text (show for closest 3 enemies or locked target)
            if i < 3 or enemy == locked_target:
                # Ensure text element exists
                while len(enemy_distance_texts) <= i:
                    dist_text = Text(
                        parent=minimap,
                        text='',
                        scale=0.8,
                        color=color.red,
                        position=(0, 0),
                        visible=False
                    )
                    enemy_distance_texts.append(dist_text)
                
                enemy_distance_texts[i].text = f'{int(distance_to_enemy)}m'
                enemy_distance_texts[i].position = (marker_pos.x + 0.02, marker_pos.y + 0.01)
                enemy_distance_texts[i].visible = True
                if enemy == locked_target:
                    enemy_distance_texts[i].color = color.yellow
                else:
                    enemy_distance_texts[i].color = color.red
            elif i < len(enemy_distance_texts):
                enemy_distance_texts[i].visible = False
        else:
            # Out of range
            enemy_markers[i].visible = False
            if i < len(enemy_distance_texts):
                enemy_distance_texts[i].visible = False
    
    # Hide locked marker if no lock
    if not locked_target:
        locked_marker.visible = False
        locked_marker_ring.visible = False

def update_offscreen_arrows():
    """Show arrows at screen edge pointing to offscreen enemies"""
    screen_edge = 0.9

    for enemy in enemy_planes:
        if enemy not in offscreen_arrows:
            offscreen_arrows[enemy] = Entity(
                parent=camera.ui,
                model='quad',
                color=color.red,
                scale=(0.04, 0.04),
                visible=False
            )


        arrow = offscreen_arrows[enemy]

        # Vector from player to enemy
        rel = enemy.position - plane.position
        dist = rel.length()


        # Angle relative to player heading
        angle = math.atan2(rel.x, rel.z) - math.radians(plane.rotation_y)
        angle = (angle + math.pi) % (2 * math.pi) - math.pi

        # Screen position
        x = math.sin(angle) * screen_edge
        y = math.cos(angle) * screen_edge
        arrow.position = (x, y)

        # Rotate arrow to point toward enemy
        arrow.rotation_z = -math.degrees(angle)
        arrow.visible = True

    # Cleanup arrows for destroyed enemies
    for enemy in list(offscreen_arrows.keys()):
        if enemy not in enemy_planes:
            destroy(offscreen_arrows[enemy])
            del offscreen_arrows[enemy]


def update_minimap():
    world_size = 50000
    minimap_size = 0.3
    
    norm_x = plane.x / world_size
    norm_z = plane.z / world_size
    
    plane_marker.x = norm_x * (minimap_size / 2)
    plane_marker.y = norm_z * (minimap_size / 2)
    
    # Update enemy markers
    for i, enemy in enumerate(enemy_planes):
        if i < len(enemy_markers):
            norm_ex = enemy.x / world_size
            norm_ez = enemy.z / world_size
            enemy_markers[i].x = norm_ex * (minimap_size / 2)
            enemy_markers[i].y = norm_ez * (minimap_size / 2)
            enemy_markers[i].visible = True
    
    # Hide unused markers
    for i in range(len(enemy_planes), len(enemy_markers)):
        enemy_markers[i].visible = False
