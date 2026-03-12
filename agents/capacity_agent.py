def capacity_analysis(df):

    team_members = 3
    hours_per_member = 40
    sprint_weeks = 2

    team_capacity = team_members * hours_per_member * sprint_weeks

    df["effort_hours"] = df["estimated_days"] * 6

    total_effort = df["effort_hours"].sum()

    return team_capacity, total_effort