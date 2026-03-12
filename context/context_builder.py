def build_context(df):

    context = {
        "total_tasks": len(df),
        "completed_tasks": len(df[df["status"] == "Tamam"]),
        "delayed_tasks": len(df[df["delay"] == True]),
        "average_risk": df["risk_score"].mean(),
        "high_risk_tasks": len(df[df["risk_score"] >= 3])
    }

    return context