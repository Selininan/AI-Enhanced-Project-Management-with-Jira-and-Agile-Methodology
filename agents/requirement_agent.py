def requirement_analysis(df):

    def check_requirement(row):

        text = row["summary"].lower()

        keywords = ["feature", "ai", "system", "analysis", "integration"]

        for k in keywords:
            if k in text:
                return "Aligned with requirement"

        return "Low requirement alignment"

    df["requirement_alignment"] = df.apply(check_requirement, axis=1)

    return df