

def load_missions(path="missions/missions.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    missions_data = data.get("missions", [])
    if not isinstance(missions_data, list):
        raise ValueError("missions.json format error: 'missions' must be a list")
    return missions_data


def _build_mission_briefing_text(selected_mission):
    objective_lines = []
    for i, objective in enumerate(selected_mission.get("objectives", []), start=1):
        objective_text = objective.get("description", "No objective description")
        objective_lines.append(f"{i}. {objective_text}")

    objectives_block = "\n".join(objective_lines) if objective_lines else "No objectives"
    return (
        f"Mission: {selected_mission.get('name', 'Unknown Mission')}\n\n"
        f"Briefing: {selected_mission.get('description', 'No briefing available')}\n\n"
        f"Objectives:\n{objectives_block}"
    )


missions = load_missions()
if not missions:
    raise ValueError("No missions found in missions/missions.json")

mission = random.choice(missions).copy()
mission["objectives"] = [obj.copy() for obj in mission.get("objectives", [])]

def typewriter_print(text, delay=0.02):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()  # final newline


briefing_text = _build_mission_briefing_text(mission)

print("\n=== MISSION BRIEFING ===\n")
typewriter_print(briefing_text, delay=0.015)

print("\nPress ENTER to begin...")
input()

mission_start_time = time.time()

                                                                                                           
