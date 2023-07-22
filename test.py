while True:
    print("hi")
    await db.staff.find_first(where={"discord_id": str(305246941992976386)}, include={"tickets": True})