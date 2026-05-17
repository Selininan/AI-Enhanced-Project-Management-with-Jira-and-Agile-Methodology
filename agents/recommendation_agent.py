import pandas as pd

def ai_recommendation(df):
    
    # 1. AI'IN KENDİ KENDİNE ÖĞRENME AŞAMASI (Dinamik Uzmanlık Çıkarımı)
    # Kimseye atanmamış ve uzmanlığı belli olmayan satırları çöpe atıyoruz
    valid_tasks = df[(df["assignee"] != "Unassigned") & (df["expertise"] != "Belirtilmemiş")].copy()
    
    team_expertise = {}
    
    if not valid_tasks.empty:
        # Pandas ile her 'assignee'nin en çok hangi 'expertise' alanında çalıştığını buluyoruz
        # value_counts().index[0] -> O kişinin en çok tekrar eden uzmanlık alanını getirir
        learned_expertise = valid_tasks.groupby('assignee')['expertise'].agg(lambda x: x.value_counts().index[0]).to_dict()
        
        # İsimleri küçük harfe çevirerek sistemin hafızasına (sözlüğe) yazıyoruz
        team_expertise = {k.lower(): v for k, v in learned_expertise.items()}
        
        # Sadece geliştirme aşamasında AI'ın neleri öğrendiğini görmek için terminale basalım
        print("\n🧠 AI Learning Report (Person -> Expertise):")
        for person, expertise in team_expertise.items():
            print(f"- {person.title()}: {expertise}")

    # 2. ÖĞRENİLEN VERİLERLE TAVSİYE VERME AŞAMASI
    def recommendation(row):
        assignee = str(row.get("assignee", "")).strip().lower()
        expertise = str(row.get("expertise", "")).strip()

        # Atanmamış (Unassigned) Kontrolü
        if assignee == "unassigned":
            if expertise != "Belirtilmemiş":
                return f"Atama Bekliyor → Bu task acilen bir {expertise} uzmanına atanmalı."
            else:
                return "Belirsizlik → Görevin uzmanlık alanı ve yapacak kişi eksik, netleştirin."

        # AI'ın Öğrendiği Bilgiyle Yanlış Uzmanlık (Mismatch) Kontrolü
        user_expertise = team_expertise.get(assignee, "Bilinmiyor")
        
        if user_expertise != "Bilinmiyor" and expertise != "Belirtilmemiş":
            # Kişinin sistemden öğrenilen uzmanlığı, o anki taskın uzmanlığından farklıysa:
            if user_expertise.lower() not in expertise.lower():
                return f"Yanlış Atama Riski → {assignee.title()} genel olarak {user_expertise} çalışıyor ama bu iş {expertise}. Atamayı kontrol edin."

        # Yüksek Risk Kontrolü
        if row.get("risk_score", 0) >= 3:
            return "Yüksek Risk → Taskı daha küçük parçalara bölün veya destek atayın."

        # Gecikme Kontrolü
        if row.get("delay", False):
            return "Gecikme Var → Engelleri (Blockers) sorun veya önceliği artırın."

        return "İyi Durumda → İzlemeye devam edin."

    # Fonksiyonu tüm tabloya uygula
    df["recommendation"] = df.apply(recommendation, axis=1)

    return df