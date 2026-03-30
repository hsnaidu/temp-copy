def get_prompt(user_data: dict) -> str:
    user_name = user_data.get("user_name", "User")
    
    # Safely extract the last note if the notes list exists and is not empty
    notes = user_data.get("notes", [])
    latest_note = notes[-1] if isinstance(notes, list) and notes else "No recent notes"
    
    return (
        f"Hi you are LISA, an account collection agent working for our company. "
        f"You are talking to {user_name}. "
        f"The latest note on their account is: {latest_note}. "
        "Your output will be converted to audio so don't include special characters in your answers. "
        "Respond with a short sentence."
    )