import pandas as pd

def requirement_analysis(df):

    def check_requirement(row):
        # Analizi yapabilmek için açıklamayı (description) alıp küçük harfe çeviriyoruz
        description = str(row.get("description", "")).lower()

        # Eğer açıklama tamamen boşsa baştan uyarıyı ver
        if not description or description == "none":
            return "Kritik Eksik → Görev açıklaması (Description) tamamen boş!"

        # PMI Standartlarına göre aranacak anahtar kelimeler (Türkçe ve İngilizce)
        actor_keywords = ["actor", "aktör", "user", "kullanıcı", "müşteri", "admin", "client"]
        criteria_keywords = ["acceptance criteria", "kabul kriteri", "kabul kriterleri", "expected result", "beklenen", "test steps"]

        # Metnin içinde bu kelimeler geçiyor mu diye kontrol ediyoruz
        has_actor = any(k in description for k in actor_keywords)
        has_criteria = any(k in description for k in criteria_keywords)

        # Duruma göre AI'ın vereceği PMO tepkileri:
        if has_actor and has_criteria:
            return "PMI Standardına Uygun → Aktör ve Kabul Kriterleri mevcut. (Kaliteli Analiz)"
        
        elif has_actor and not has_criteria:
            return "Eksik Analiz → Aktör belirtilmiş ama 'Kabul Kriteri' (Acceptance Criteria) eksik. İşin ne zaman biteceği belirsiz."
        
        elif not has_actor and has_criteria:
            return "Eksik Analiz → Kabul kriteri var ama işin 'Aktörü' (Kim kullanacak?) belirtilmemiş. Hedef kitle netleşmeli."
        
        else:
            return "Zayıf Gereksinim → Açıklama var ancak Aktör ve Kabul Kriteri yok. Kapsam (Scope) çok belirsiz, yeniden yazılmalı."

    # Fonksiyonu DataFrame'in tüm satırlarına uygula
    df["requirement_alignment"] = df.apply(check_requirement, axis=1)

    return df