def jira_support_answer(question):
    q = question.lower()

    if "story" in q and "task" in q:
        return "Story kullanıcı ihtiyacını anlatır, task teknik işi temsil eder."

    elif "epic" in q:
        return "Epic, birden fazla story veya taskı kapsayan büyük iş grubudur."

    elif "assignee" in q:
        return "Assignee, görevin atandığı kişidir."

    elif "priority" in q:
        return "Priority, işin önem seviyesini belirler."

    elif "sprint" in q:
        return "Sprint, belirli sürede tamamlanması hedeflenen görev grubudur."

    else:
        return "Jira'da issue type, epic, story ve task ilişkileri kontrol edilmelidir."