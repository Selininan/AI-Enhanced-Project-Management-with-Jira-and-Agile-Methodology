def calculate_risk(df):

    def risk_score(row):
        score = 0

        if row["delay"]:
            score += 2

        if row["estimated_days"] > 5:
            score += 1

        if row["status"] != "Tamam":
            score += 1

        return score

    df["risk_score"] = df.apply(risk_score, axis=1)

    return df