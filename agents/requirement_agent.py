import pandas as pd

def requirement_analysis(df):

    def check_requirement(row):
        # Analizi yapabilmek için açıklamayı (description) alıp küçük harfe çeviriyoruz
        description = str(row.get("description", "")).lower()

        # Eğer açıklama tamamen boşsa baştan uyarıyı ver
        if not description or description == "none":
            return "Critical Missing → Task description is completely empty!"

        actor_keywords = ["actor", "aktör", "user", "kullanıcı", "müşteri", "admin", "client"]
        criteria_keywords = ["acceptance criteria", "kabul kriteri", "kabul kriterleri", "expected result", "beklenen", "test steps"]

        has_actor = any(k in description for k in actor_keywords)
        has_criteria = any(k in description for k in criteria_keywords)

        if has_actor and has_criteria:
            return "PMI Compliant → Actor and Acceptance Criteria are present. (Quality Analysis)"

        elif has_actor and not has_criteria:
            return "Incomplete → Actor is specified but Acceptance Criteria is missing. Definition of done is unclear."

        elif not has_actor and has_criteria:
            return "Incomplete → Acceptance criteria exists but Actor (who will use it?) is not specified."

        else:
            return "Weak Requirement → Description exists but Actor and Acceptance Criteria are missing. Scope is very vague, needs rewriting."

    # Fonksiyonu DataFrame'in tüm satırlarına uygula
    df["requirement_alignment"] = df.apply(check_requirement, axis=1)

    return df