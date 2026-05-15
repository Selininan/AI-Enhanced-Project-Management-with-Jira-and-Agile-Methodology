import pandas as pd

def capacity_analysis(df):
    # Null (boş) eforları 0 yapıyoruz
    df["effort_hours"] = df["estimated_hours"].fillna(0)
    total_effort = df["effort_hours"].sum()

    # 1. AI'IN KENDİ KENDİNE TAKIM KAPASİTESİNİ ÖĞRENMESİ (Dinamik)
    # Kimseye atanmamış satırları eliyoruz
    valid_tasks = df[(df["assignee"] != "Unassigned") & (df["assignee"].notna())].copy()
    
    dynamic_role_capacities = {}
    team_capacity = 0
    sprint_hours_per_person = 80 # 2 Haftalık sprint için varsayılan kişi başı kapasite
    
    if not valid_tasks.empty:
        # Tıpkı tavsiye ajanındaki gibi, her kişinin ana uzmanlığını buluyoruz
        learned_expertise = valid_tasks.groupby('assignee')['expertise'].agg(lambda x: x.value_counts().index[0])

        # Hangi uzmanlıkta KAÇ KİŞİ olduğunu sayıyoruz (Örn: "Backend": 3 kişi)
        role_counts = learned_expertise.value_counts().to_dict()

        # Rollerin toplam kapasitesini hesapla (Kişi Sayısı * 80 Saat)
        for role, count in role_counts.items():
            if role != "Unspecified":
                dynamic_role_capacities[role] = count * sprint_hours_per_person
                team_capacity += (count * sprint_hours_per_person)

    # 2. UZMANLIK ALANINA GÖRE İŞ YÜKÜ (EFOR) GRUPLAMA
    role_efforts = df.groupby("expertise")["effort_hours"].sum().to_dict()

    bottleneck_report = []

    # 3. KONTROL VE RAPORLAMA AŞAMASI
    for role, effort in role_efforts.items():
        if effort == 0:
            continue

        if role == "Unspecified":
            bottleneck_report.append(f"⚠️ WARNING: There are {effort} hours of work with no expertise assigned! These assignments create hidden risk.")
            continue

        # AI'ın öğrendiği takımdan bu rolün kapasitesini çek (Eğer takımda o rolde kimse yoksa kapasite 0 döner)
        cap = dynamic_role_capacities.get(role, 0)

        if cap == 0:
            bottleneck_report.append(f"🚨 CRITICAL GAP: There are {effort} hours of work requiring {role} expertise, but no one with this role was detected in the team!")
        elif effort > cap:
            bottleneck_report.append(f"🚨 BOTTLENECK: {role} team is assigned {effort} hours of work (Available Capacity: {cap} hours). Very high risk of delay!")
        else:
            bottleneck_report.append(f"✅ OK: {role} team workload is {effort} hours (Available Capacity: {cap} hours).")

    return team_capacity, total_effort, bottleneck_report