def calculate_risk(df):
    def risk_score(row):
        score = 0

        if row["delay"]:
            score += 2

        if row["estimated_hours"] > 6:
            score += 1

        if row["status"] not in ["Done", "Tamam"]:
            score += 1

        if row["priority"] in ["High", "Highest"]:
            score += 1

        return score

    df["risk_score"] = df.apply(risk_score, axis=1)
    return df