def input(key):
    global throttle, models_index, autopilot, gravity, cockpit_view, speed
    global missile_count, flare_count, gun_ammo, locked_target, is_locking, lock_progress
    global radar_enabled, camera_offset
    global editor_mode, game_over
    global y

    if game_over:
        if key == 'r':
            restart_game()
        if key == 'escape':
            application.quit()
        return
    if key == 'enter' and 'intro_active' in globals() and intro_active:
        skip_intro()
        return
    if key == 'f1':
        editor_mode = not editor_mode

        if editor_mode:
            mouse.locked = False
            print("EditorCamera ENABLED")
        else:
            mouse.locked = True
            print("EditorCamera DISABLED")
    if key == 'escape': application.quit()
    if key == 'q' and throttle < 100.0: throttle += 1
    elif key == 'e' and throttle > 0.0: throttle -= 1
    elif key == 'left shift' or key == 'right shift':
        models_index = (models_index + (1 if key == 'left shift' else -1)) % len(models)
        plane.model = models[models_index]
    elif key == 'p':
        autopilot = not autopilot
        if autopilot:
            print("Autopilot ENGAGED")
            plane.rotation_y = get_bearing(plane.position, enemy_planes[0].position) if enemy_planes else plane.rotation_y
        else:
            print("Autopilot DISENGAGED")
    elif key == 'j':
        plane.position.y = enemy_planes[0].position.y if enemy_planes else plane.position.y
    elif key == 'space':
        print(f"Saving Airport at: {plane.position}")
    
    if key == 'c':
        cockpit_view = not cockpit_view
        cockpit_ui.visible = cockpit_view and ('cockpit_model' not in globals() or not cockpit_model.enabled)
        if 'cockpit_model' in globals():
            cockpit_model.visible = cockpit_view and cockpit_model.enabled
        plane.visible = not cockpit_view
    
    # Fire missile (only if fully locked)
    if key == 'm' and missile_count > 0:
        if locked_target and lock_progress >= lock_time_required:
            yaw_rad = math.radians(plane.rotation_y)
            forward_vector = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
            missile_pos = plane.position + forward_vector * 5 + Vec3(0, 1, 0)
            
            missile = Missile(
                position=missile_pos,
                forward_vector=forward_vector,
                velocity=missile_velocity,
                target=locked_target,
                missile_settings=missile_settings
            )
            missile.net_id = uuid.uuid4().hex
            missiles.append(missile)
            missile_count -= 1
            
            # Add visual/audio feedback
            lock_indicator.text = 'MISSILE AWAY'
        else:
            # No lock warning
            lock_indicator.text = 'NO LOCK - CANNOT FIRE'
            lock_indicator.color = color.red
    
    # Deploy flare
    if key == 'f' and flare_count > 0:
        flare = Flare(position=plane.position + Vec3(0, -2, 0))
        flares.append(flare)
        flare_count -= 1
    
    # Lock next target (cycle forward)
    if key == 't':
        cycle_target(1)
    
    # Lock previous target (cycle backward)
    if key == 'r':
        cycle_target(-1)
    
    # Break lock
    if key == 'b':
        locked_target = None
        is_locking = False
        lock_progress = 0
        lock_indicator.text = 'LOCK BROKEN'
    
    # Gun fire (simplified - just damage nearest enemy in front)
    if key == 'g' and gun_ammo > 0:
        gun_ammo -= 1
        # Check if enemy in crosshairs
        for enemy in enemy_planes:
            if distance(plane.position, enemy.position) < 500:
                # Simple angle check
                direction = (enemy.position - plane.position).normalized()
                yaw_rad = math.radians(plane.rotation_y)
                forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
                
                if direction.dot(forward) > 0.95:  # Within ~18 degrees
                    enemy.take_damage(5)
                    break
    
    
    # Toggle radar
    if key == 'h':
        radar_enabled = not radar_enabled
        radar_bg.visible = radar_enabled
        radar_grid.visible = radar_enabled
        radar_grid2.visible = radar_enabled
        radar_grid3.visible = radar_enabled
        radar_label.visible = radar_enabled
        radar_range_text.visible = radar_enabled
        radar_n.visible = radar_enabled
        radar_s.visible = radar_enabled
        radar_e.visible = radar_enabled
        radar_w.visible = radar_enabled
        radar_sweep.visible = radar_enabled
    
    # Camera zoom controls
    if key == 'z':
        camera_offset.z -= 2  # Zoom in
    if key == 'x' :
        camera_offset.z += 2  # Zoom out
    if key == 'v':
        camera_offset.z = 10  # Reset to default
        camera_offset.y = 3
    
    if key == 'l':
        explosion_3d(plane.position)
    if key == 'o':
        throttle = 0
        speed = 0
    if key == 'i':
        ground.position = plane.position - Vec3(0, 10, 0)
    if key == 'u':
        y += 1
    if key == 'y':
        y -= 1
# Bearing Calculation
def get_bearing(from_pos, to_pos):
    dx, dz = to_pos[0] - from_pos[0], to_pos[2] - from_pos[2]
    return math.degrees(math.atan2(dx, dz)) % 360

# Navigation Input
def navigate():
    global plane, airport_index
    loc = input_box.text.upper()
    if loc in airport_codes:
        airport_index = airport_codes.index(loc)
        plane.rotation_y = get_bearing(plane.position, airport_positions[airport_index])
    else:
        print("Invalid Airport Code!")
    input_box.visible = label.visible = submit_button.visible = False

