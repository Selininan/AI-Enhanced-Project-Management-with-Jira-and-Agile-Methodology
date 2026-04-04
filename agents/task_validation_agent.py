def validate_task(df):
    def check_task(row):
        problems = []

        if len(str(row.get("summary", "")).strip()) < 8:
            problems.append("Summary too short")

        if not str(row.get("description", "")).strip():
            problems.append("Description missing")

        if row.get("issue_type") in ["Task", "Görev"] and not row.get("epic", ""):
            problems.append("Epic link missing")

        if row.get("assignee") in ["Unassigned", "", None]:
            problems.append("Assignee missing")

        if row.get("priority") in ["None", "", None]:
            problems.append("Priority missing")

        if problems:
            return " ; ".join(problems)

        return "Valid"

    df["validation_result"] = df.apply(check_task, axis=1)
    return df