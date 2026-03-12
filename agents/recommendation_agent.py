def ai_recommendation(df):

    def recommendation(row):

        if row["risk_score"] >= 3:
            return "High risk → split task"

        elif row["delay"]:
            return "Delayed → increase priority"

        else:
            return "Monitor task"

    df["recommendation"] = df.apply(recommendation, axis=1)

    return df