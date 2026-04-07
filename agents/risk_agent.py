def calculate_risk(df):
    def risk_score(row):
        score = 0

        # 1. Gecikme Durumu (En büyük risk, tahmini süreyi aşmış)
        if row["delay"]:
            score += 2

        # 2. Görev Büyüklüğü Riski (6 saat yerine 24 saate çıkardık)
        if row["estimated_hours"] > 24:
            score += 1

        # 3. Akıllı Statü Riski (Türkçe ve İngilizce Jira durumlarını kapsar)
        status = str(row["status"]).strip().upper()
        
        if status in ["YAPILACAKLAR", "TO DO", "OPEN"]:
            score += 1
        elif status in ["DEVAM EDIYOR", "DEVAM EDİYOR", "IN PROGRESS"]:
            score += 0.5
        # "DONE", "TAMAM", "TAMAMLANDI" gibi durumlara 0 puan veriyoruz (Risk yok)

        # 4. Öncelik Riski
        priority = str(row.get("priority", "")).strip().upper()
        if priority in ["HIGH", "HIGHEST", "YÜKSEK", "EN YÜKSEK"]:
            score += 1

        # 5. YENİ: Belirsizlik Riski (Uzmanlık alanı yoksa veya atanmamışsa)
        if row["assignee"] == "Unassigned" or row["expertise"] == "Belirtilmemiş":
            score += 1

        return score

    # Hesaplanan puanları yeni bir sütun olarak tabloya ekle
    df["risk_score"] = df.apply(risk_score, axis=1)
    return df