def runcamera(y=4):
    """Advanced smooth chase camera with inertia & immersion effects"""

    global previous_speed

    if cockpit_view:
        cockpit_pos = (
            plane.world_position
            + plane.up * 1.35
            + plane.forward * 1.8
        )
        camera.position = lerp(camera.position, cockpit_pos, time.dt * 12)
        camera.rotation = lerp(camera.rotation, plane.world_rotation, time.dt * 10)
        camera.fov = lerp(camera.fov, 78, time.dt * 4)

        if 'cockpit_model' in globals():
            cockpit_model.visible = cockpit_model.enabled
        return

    if 'cockpit_model' in globals():
        cockpit_model.visible = False

    desired_pos = plane.position - Vec3(
        math.sin(math.radians(plane.rotation_y)) * camera_offset.z,
        -camera_offset.y,
        math.cos(math.radians(plane.rotation_y)) * camera_offset.z
    )
    bank_factor = clamp(plane.rotation_z / 45, -1, 1)
    desired_pos += plane.right * (bank_factor * 0.8)

    g_force = Lift / (mass * g) if mass > 0 and 'Lift' in globals() else 1

    lag_multiplier = clamp(g_force * 0.15, 0, 1.5)

    follow_speed = y - lag_multiplier

    camera.position = lerp(
        camera.position,
        desired_pos,
        time.dt * follow_speed
    )

    target_position = plane.world_position + plane.forward * 40 + plane.up * 2

    camera.look_at(target_position)

    # Apply mouse look offset AFTER look_at
    camera.rotation_x += mouse_pitch * 0.5
    camera.rotation_y += mouse_yaw * 0.5

    base_fov = 90
    max_extra_fov = 20

    speed_ratio = clamp(speed / 600, 0, 1)
    target_fov = base_fov + max_extra_fov * speed_ratio

    camera.fov = lerp(camera.fov, target_fov, time.dt * 2)

    if speed > 400:
        shake_intensity = (speed - 400) / 4000
        shake_t = time.time() * 35
        camera.position += Vec3(
            math.sin(shake_t) * shake_intensity,
            math.cos(shake_t * 1.3) * shake_intensity * 0.6,
            0
        )



def runmissile():
    if missiles:
        camera.position = missiles[0].position - Vec3(
            math.sin(math.radians(plane.rotation_y)) * camera_offset.z,
            -camera_offset.y,
            math.cos(math.radians(plane.rotation_y)) * camera_offset.z
        )
        camera.look_at(missiles[0])

