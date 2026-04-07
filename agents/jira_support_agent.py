import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
GUIDE_PATH = os.path.join(BASE_DIR, "jira_guide.txt")


def load_guide():
    with open(GUIDE_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


GUIDE_TEXT = load_guide()


def parse_guide_sections(text):
    sections = {}
    current_title = None
    buffer = []

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.endswith(":") and len(stripped) < 120:
            if current_title is not None:
                sections[current_title] = " ".join(buffer).strip()

            current_title = stripped[:-1].strip().lower()
            buffer = []
        else:
            if current_title is not None:
                buffer.append(stripped)

    if current_title is not None:
        sections[current_title] = " ".join(buffer).strip()

    return sections


GUIDE_SECTIONS = parse_guide_sections(GUIDE_TEXT)


def get_guide_value(*possible_keys):
    for key in possible_keys:
        value = GUIDE_SECTIONS.get(key.lower())
        if value:
            return value
    return None


TOPIC_KEYWORDS = {
    "jira": [
        "jira", "tool", "platform", "araç", "uygulama"
    ],
    "epic": [
        "epic", "epik", "büyük iş", "ana iş", "üst iş", "parent issue"
    ],
    "story": [
        "story", "hikaye", "user story", "kullanıcı ihtiyacı"
    ],
    "task": [
        "task", "görev", "iş kalemi", "technical work", "teknik iş"
    ],
    "sprint": [
        "sprint", "iterasyon", "iteration"
    ],
    "backlog": [
        "backlog", "bekleyen işler", "iş listesi"
    ],
    "assignee": [
        "assignee", "atanan", "atanmış", "sorumlu",
        "kime at", "kime atıyoruz", "kim yapacak",
        "görevi kim", "atama"
    ],
    "priority": [
        "priority", "öncelik", "önceliği", "kritik", "urgent", "acil"
    ],
    "story point": [
        "story point", "story points", "puan", "efor", "effort", "estimate", "tahmin"
    ],
}


def normalize_text(text):
    text = text.lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    text = text.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return text


def detect_topic(question):
    q = normalize_text(question)
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_norm = normalize_text(kw)
            if kw_norm in q:
                score += 2 if " " in kw_norm else 1
        if score > 0:
            scores[topic] = score

    if not scores:
        return None

    priority_order = [
        "assignee", "priority", "story point",
        "epic", "story", "task", "sprint", "backlog", "jira"
    ]

    max_score = max(scores.values())
    candidates = [topic for topic, score in scores.items() if score == max_score]

    for topic in priority_order:
        if topic in candidates:
            return topic

    return candidates[0]


def jira_support_answer(question):
    q = normalize_text(question)
    topic = detect_topic(question)

    if ("story" in q or "hikaye" in q) and ("task" in q or "gorev" in q):
        story_text = get_guide_value("story") or "Story bölümü bulunamadı."
        task_text = get_guide_value("task", "jira for task management") or "Task bölümü bulunamadı."
        return (
            "Story kullanıcı ihtiyacını anlatır, task ise bu ihtiyacı gerçekleştiren teknik iştir.\n\n"
            f"Guide - STORY:\n{story_text}\n\n"
            f"Guide - TASK:\n{task_text}"
        )

    if "nasil ac" in q and ("task" in q or "gorev" in q):
        return (
            "Task açarken summary, description, priority, assignee ve mümkünse epic bağlantısı girilmelidir.\n\n"
            f"Guide - TASK:\n{get_guide_value('task', 'jira for task management') or 'Task bölümü bulunamadı.'}"
        )

    if "neden hatali" in q or "niye hatali" in q or "validation" in q:
        return (
            "Bir task description eksikse, assignee yoksa, epic link yoksa veya summary yetersizse problemli sayılabilir.\n"
            "Bu projede validation agent bu alanları kontrol ediyor."
        )

    if topic == "jira":
        return f"Guide - JIRA:\n{get_guide_value('jira', 'what is jira?') or 'JIRA bölümü bulunamadı.'}"

    if topic == "epic":
        return f"Guide - EPIC:\n{get_guide_value('epic', 'what are epics?') or 'Epic bölümü bulunamadı.'}"

    if topic == "story":
        return f"Guide - STORY:\n{get_guide_value('story') or 'Story bölümü bulunamadı.'}"

    if topic == "task":
        return f"Guide - TASK:\n{get_guide_value('task', 'jira for task management') or 'Task bölümü bulunamadı.'}"

    if topic == "sprint":
        return f"Guide - SPRINT:\n{get_guide_value('sprint') or 'Sprint bölümü bulunamadı.'}"

    if topic == "backlog":
        return f"Guide - BACKLOG:\n{get_guide_value('backlog') or 'Backlog bölümü bulunamadı.'}"

    if topic == "assignee":
        return f"Guide - ASSIGNEE:\n{get_guide_value('assignee') or 'Assignee bölümü bulunamadı.'}"

    if topic == "priority":
        return f"Guide - PRIORITY:\n{get_guide_value('priority') or 'Priority bölümü bulunamadı.'}"

    if topic == "story point":
        return f"Guide - STORY POINT:\n{get_guide_value('story point', 'story_point') or 'Story Point bölümü bulunamadı.'}"

    return (
        "Soruyu anlayabildim ama uygun konu bulunamadı. Epic, Story, Task, Sprint, Backlog, Assignee, Priority veya Story Point hakkında sorabilirsin."
    )