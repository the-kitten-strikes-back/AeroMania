def spawn_enemies(count=5):
    """Spawn enemy planes around the map at tactical distances"""
    for i in range(count):
        # Spawn at better engagement distances (2000-4000m away)
        angle = random.uniform(0, 360)
        distance_away = random.uniform(2000, 4000)
        
        spawn_pos = plane.position + Vec3(
            math.sin(math.radians(angle)) * distance_away,
            random.uniform(3000, 5000),
            math.cos(math.radians(angle)) * distance_away
        )
        enemy = EnemyPlane(position=spawn_pos)
        enemy_planes.append(enemy)
        
        # Add marker to minimap
        marker = Entity(parent=minimap, model='circle', color=color.red, scale=0.015)
        enemy_markers.append(marker)
        initial_enemy_count = len(enemy_planes)

def get_targetable_enemies():
    """Get list of enemies within radar range, sorted by distance"""
    targetable = []
    for enemy in enemy_planes:
        dist = distance(plane.position, enemy.position)
        if dist <= radar_range:
            targetable.append((enemy, dist))
    
    # Sort by distance
    targetable.sort(key=lambda x: x[1])
    return [e[0] for e in targetable]

def cycle_target(direction=1):
    """Cycle through available targets"""
    global target_index, locked_target, is_locking, lock_progress
    
    targets = get_targetable_enemies()
    if not targets:
        locked_target = None
        target_index = 0
        is_locking = False
        lock_progress = 0
        return
    
    # Cycle through targets
    target_index = (target_index + direction) % len(targets)
    locked_target = targets[target_index]
    is_locking = True
    lock_progress = 0

def update_targeting():
    """Update targeting system with lock progression"""
    global locked_target, is_locking, lock_progress, target_index
    
    # Clear target if destroyed
    if locked_target and locked_target not in enemy_planes:
        locked_target = None
        is_locking = False
        lock_progress = 0
        target_index = 0
    
    # Update lock progress
    if is_locking and locked_target:
        dist = distance(plane.position, locked_target.position)
        
        # Check if still in range
        if dist > radar_range:
            locked_target = None
            is_locking = False
            lock_progress = 0
            lock_indicator.text = 'OUT OF RANGE'
            lock_indicator.color = color.gray
        else:
            # Check if target is in front of player (simplified FOV check)
            direction = (locked_target.position - plane.position).normalized()
            yaw_rad = math.radians(plane.rotation_y)
            forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
            
            dot_product = direction.dot(forward)
            
            # Target must be within ~60 degree cone in front
            if dot_product > 0.5:
                # Increase lock progress
                lock_progress += time.dt
                
                # Lock achieved
                if lock_progress >= lock_time_required:
                    lock_indicator.text = '** LOCKED **'
                    lock_indicator.color = color.red
                    reticle.color = color.red
                else:
                    # Still locking
                    lock_indicator.text = 'LOCKING...'
                    lock_indicator.color = color.yellow
                    reticle.color = color.yellow
                
                # Update lock progress bar
                lock_bar_bg.visible = True
                lock_bar_fill.visible = True
                progress_ratio = min(lock_progress / lock_time_required, 1.0)
                lock_bar_fill.scale_x = 0.2 * progress_ratio
                lock_bar_fill.x = -0.1 + (0.1 * progress_ratio)
                lock_bar_fill.color = color.red if progress_ratio >= 1.0 else color.yellow
                
                # Show target info
                target_display.text = f'Target: {dist:.0f}m | {locked_target.health}HP'
                
                # Show targeting brackets
                show_targeting_brackets(True)
            else:
                # Target not in FOV
                lock_progress = max(0, lock_progress - time.dt * 2)  # Decay faster
                lock_indicator.text = 'TARGET OFF BORESIGHT'
                lock_indicator.color = color.orange
                reticle.color = color.orange
                show_targeting_brackets(False)
    else:
        # No active lock
        lock_indicator.text = ''
        target_display.text = ''
        lock_bar_bg.visible = False
        lock_bar_fill.visible = False
        reticle.color = color.green
        show_targeting_brackets(False)
        
        # Show available targets
        targets = get_targetable_enemies()
        if targets:
            lock_indicator.text = f'[T] to lock | {len(targets)} targets'
            lock_indicator.color = color.white
            lock_indicator.scale = 1.5

def show_targeting_brackets(visible):
    """Show/hide targeting brackets around locked enemy"""
    bracket_tl.visible = visible
    bracket_tr.visible = visible
    bracket_bl.visible = visible
    bracket_br.visible = visible
    bracket_tl2.visible = visible
    bracket_tr2.visible = visible
    bracket_bl2.visible = visible
    bracket_br2.visible = visible
editor_cam = EditorCamera(enabled=False)
editor_cam.ignore_paused = True

def trigger_mission_complete():
    currency_earned = 0
    new_badges = []
    if 'update_progression_on_win' in globals():
        currency_earned, new_badges = update_progression_on_win()

    # Freeze the world
    time.scale = 0

    # Stop sounds
    plane_engine.stop()
    bgm.stop()
    game_over_bg.visible = True
    game_over_title.text = "YOU WIN. MISSION COMPLETE."
    game_over_sub.text = f"All mission objectives fulfilled.\nEarned {currency_earned} AirBucks!"
    if new_badges:
        badge_text = "\nNew Badges: " + ", ".join([b["name"] for b in new_badges])
        game_over_sub.text += badge_text
    game_over_bg.visible = True
    game_over_title.visible = True
    game_over_sub.visible = True
    restart_text.visible = True
    quit_text.visible = True
