class Flare(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='sphere',
            color=color.rgb(255, 200, 100),
            scale=1.8,
            position=position,
            emissive=True,
            **kwargs
        )
        self.lifetime = 3
        self.velocity = Vec3(random.uniform(-2, 2), -5, random.uniform(-2, 2))
        invoke(self.cleanup, delay=self.lifetime)
    
    def update(self):
        self.position += self.velocity * time.dt
        self.velocity.y -= 9.8 * time.dt  # Gravity
    
    def cleanup(self):
        if self in flares:
            flares.remove(self)
        destroy(self)

class Missile(Entity):
    def __init__(self, position, forward_vector, velocity, target=None, is_enemy=False, lifetime=10, missile_settings=None, **kwargs):
        if missile_settings is None:
            missile_settings = {"color": (255, 0, 0), "speed": 1.0, "turn_rate": 1.0, "damage": 100}
        
        color_rgb = missile_settings.get("color", (255, 0, 0))
        missile_color = color.rgb(color_rgb[0]/255, color_rgb[1]/255, color_rgb[2]/255) if not is_enemy else color.orange
        
        super().__init__(
            scale=0.8, 
            model='missile', 
            color=missile_color, 
            rotationscale=0.02, 
            position=position, 
            collider='box', 
            **kwargs
        )
        self.rotation_x += 90
        self.velocity = velocity * missile_settings.get("speed", 1.0)
        self.target = target
        self.is_enemy = is_enemy
        self.tracking = target is not None
        self.turn_rate = 2.5 * missile_settings.get("turn_rate", 1.0)  # degrees per frame
        self.damage = missile_settings.get("damage", 100)
        
        self.forward_vec = Vec3(forward_vector.x, forward_vector.y, forward_vector.z).normalized()
        self.trail = TrailRenderer(
            size=Vec3(1, 0.01, 1),
            segments=16,
            min_spacing=0.05,
            fade_speed=0,
            color_gradient=[missile_color, color.orange, color.clear],
            parent=self
        )
        invoke(self.cleanup, delay=lifetime)

    def update(self):
        # Heat-seeking logic
        if self.tracking and self.target and hasattr(self.target, 'position'):
            # Check for flare distraction
            closest_flare = None
            min_flare_dist = 100
            for flare in flares:
                dist = distance(self.position, flare.position)
                if dist < min_flare_dist:
                    min_flare_dist = dist
                    closest_flare = flare
            
            # If flare is close, track it instead
            if closest_flare and min_flare_dist < 50:
                target_pos = closest_flare.position
            else:
                target_pos = self.target.position
            
            # Calculate direction to target
            direction = (target_pos - self.position).normalized()
            
            # Gradually turn towards target
            self.forward_vec = vec3_lerp(self.forward_vec, direction, self.turn_rate * time.dt)
            self.forward_vec = self.forward_vec.normalized()
            
            # Update rotation to match direction
            self.look_at(self.position + self.forward_vec)
        
        # Move forward
        self.position += self.forward_vec * self.velocity * time.dt

    def cleanup(self):
        if self in missiles:
            missiles.remove(self)
        destroy(self)

class EnemyPlane(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='models/f167',
            scale=0.1,
            position=position,
            color=color.red,
            collider='mesh',
            **kwargs
        )
        self.health = 50
        ai_scale = difficulty_scale if 'difficulty_scale' in globals() else 1.0
        self.speed = random.uniform(100, 285) * (0.85 + ai_scale * 0.25)
        self.target = None
        self.state = 'patrol'  # patrol, engage, circle, evade
        self.last_shot_time = 0
        self.shot_cooldown = random.uniform(25, 50) / max(0.75, ai_scale)  # Time between shots
        self.ai_timer = 0
        
        # Initial patrol point relative to spawn
        angle = random.uniform(0, math.pi * 2)
        self.patrol_point = self.position + Vec3(
            math.sin(angle) * 2000,
            random.uniform(-200, 200),
            math.cos(angle) * 2000
        )
        
    def update(self):
        global plane
        self.ai_timer += time.dt
        
        # Check distance to player
        dist_to_player = distance(self.position, plane.position)
        
        # State machine with better distance thresholds
        if dist_to_player > 3000:
            self.state = 'patrol'
        elif dist_to_player > 2000:
            self.state = 'engage'
        elif dist_to_player > 1000:
            self.state = 'circle'  # Circle around player to stay in view
        elif dist_to_player < 300:
            self.state = 'evade'  #RUN!!
        else:
            self.state = 'engage'  # Default to engage in mid-range
        
        # Behavior based on state
        if self.state == 'patrol':
            self.patrol_behavior()
        elif self.state == 'engage':
            self.engage_behavior()
        elif self.state == 'circle':
            self.circle_behavior()
        elif self.state == 'evade':
            self.evade_behavior()
        
        # Fire missiles at optimal range (not too close)
        if self.state in ['engage', 'circle'] and time.time() - self.last_shot_time > self.shot_cooldown:
            if 100 < dist_to_player < 1100:  # Optimal firing range
                # Check if player is roughly in front before firing
                to_player = (plane.position - self.position).normalized()
                yaw_rad = math.radians(self.rotation_y)
                my_forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
                
                if to_player.dot(my_forward) > 0.7:  # Player in front cone
                    self.fire_missile()
                    self.last_shot_time = time.time()
        
        # Keep altitude reasonable
        if self.y < 100:
            self.y = 100
        elif self.y > 3000:
            self.y = 3000
    
    def patrol_behavior(self):
        """Patrol in patterns that will cross player's field of view"""
        # Move towards patrol point
        direction = (self.patrol_point - self.position).normalized()
        self.position += direction * self.speed * time.dt
        
        # Look in movement direction
        self.look_at(self.position + direction)
        
        # Set new patrol point when reached
        if distance(self.position, self.patrol_point) < 200:
            # Create patrol points that cross in front of player
            # This makes enemies more visible
            angle_to_player = math.atan2(
                plane.position.x - self.position.x,
                plane.position.z - self.position.z
            )
            
            # Random offset from player direction
            offset_angle = angle_to_player + random.uniform(-math.pi/2, math.pi/2)
            patrol_distance = random.uniform(750, 1500)
            
            self.patrol_point = self.position + Vec3(
                math.sin(offset_angle) * patrol_distance,
                random.uniform(-200, 200),
                math.cos(offset_angle) * patrol_distance
            )
    
    def engage_behavior(self):
        """Approach player from angles that will cross their boresight"""
        if not self.target:
            self.target = plane
        
        # Get player's forward direction
        yaw_rad = math.radians(self.target.rotation_y)
        player_forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
        
        # Calculate vector from player to enemy
        to_enemy = (self.position - self.target.position).normalized()
        
        # Check if we're behind the player (dot product < 0 means behind)
        dot = to_enemy.dot(player_forward)
        
        if dot < -0.3:  # We're behind player - move to their side/front
            # Circle around to get in front of player
            # Calculate perpendicular direction (to move to side)
            perpendicular = Vec3(-player_forward.z, 0, player_forward.x).normalized()
            
            # Alternate sides based on AI timer
            if math.sin(self.ai_timer * 0.5) > 0:
                perpendicular = -perpendicular
            
            # Move in a circular arc to get ahead of player
            target_pos = self.target.position + player_forward * 750 + perpendicular * 400
            direction = (target_pos - self.position).normalized()
            
        else:  # We're in front or to the side - maintain position or approach
            # Stay at medium range in front of player
            target_pos = self.target.position + player_forward * 1200
            direction = (target_pos - self.position).normalized()
        
        # Move towards target position
        self.position += direction * self.speed * time.dt
        
        # Look at player
        self.look_at(self.target.position)
    
    def circle_behavior(self):
        """Circle around the player to stay visible and in engagement range"""
        # Calculate vector from player to this enemy
        to_enemy = self.position - plane.position
        distance_xz = math.sqrt(to_enemy.x**2 + to_enemy.z**2)
        
        # Desired orbit radius
        orbit_radius = 500
        
        # Calculate tangent direction (perpendicular to radius) for circular motion
        tangent = Vec3(-to_enemy.z, 0, to_enemy.x).normalized()
        
        # Add radial component to maintain distance
        radial = to_enemy.normalized()
        
        if distance_xz < orbit_radius:
            # Too close - move outward while circling
            move_direction = tangent * 0.7 + radial * 0.3
        elif distance_xz > orbit_radius + 200:
            # Too far - move inward while circling
            move_direction = tangent * 0.7 - radial * 0.3
        else:
            # Just right - pure circular motion
            move_direction = tangent
        
        move_direction = move_direction.normalized()
        
        # Move in circular pattern
        self.position += move_direction * self.speed * time.dt
        
        # Add slight altitude variation for more interesting patterns
        altitude_target = plane.y + math.sin(self.ai_timer * 0.3) * 200
        if abs(self.y - altitude_target) > 50:
            self.y += (altitude_target - self.y) * 0.02
        
        # Always face the player (good for firing position)
        self.look_at(plane.position)
    
    def evade_behavior(self):
        """Break away when too close to avoid collision"""
        # Move away from player aggressively
        away_direction = (self.position - plane.position).normalized()
        
        # Add vertical component to evade (go up or down)
        if self.y < plane.y:
            away_direction.y = -0.5  # Dive if below player
        else:
            away_direction.y = 0.5  # Climb if above player
        
        away_direction = away_direction.normalized()
        
        # Add evasive jinking
        jink = Vec3(
            math.sin(self.ai_timer * 8) * 30,
            math.cos(self.ai_timer * 4) * 20,
            math.cos(self.ai_timer * 6) * 30
        )
        
        # Move away at high speed
        self.position += away_direction * self.speed * 1.8 * time.dt
        self.position += jink * time.dt
        
        # Look where we're going
        self.look_at(self.position + away_direction * 100)
    
    def fire_missile(self):
        """Fire missile at player with lead calculation"""
        # Calculate firing direction with lead
        relative_pos = plane.position - self.position
        time_to_target = distance(self.position, plane.position) / missile_velocity  # Missile speed
        
        # Lead the target
        yaw_rad = math.radians(plane.rotation_y)
        player_velocity = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)) * speed
        predicted_pos = plane.position + player_velocity * time_to_target
        
        # Fire towards predicted position
        forward_vector = (predicted_pos - self.position).normalized()
        missile_pos = self.position + forward_vector * 5 + Vec3(0, 1, 0)
        
        missile = Missile(
            position=missile_pos,
            forward_vector=forward_vector,
            velocity=missile_velocity,
            target=plane,
            is_enemy=True,
            lifetime=20
        )
        missiles.append(missile)
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.destroy_plane()
    
    def destroy_plane(self):
        explosion_3d(self.position)
        explosion.play()
        enemy_destroyed_display.text = 'Good job! Enemy Destroyed!'
        points_display.text = f'Points: {int(points_display.text.split(": ")[1]) + 100}'
        if self in enemy_planes:
            enemy_planes.remove(self)
        destroy(self)

