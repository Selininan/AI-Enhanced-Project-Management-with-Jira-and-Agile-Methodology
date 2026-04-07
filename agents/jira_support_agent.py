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
    "jira": ["jira", "tool", "platform", "software"],
    "epic": ["epic", "large body", "parent issue", "group"],
    "story": ["story", "user requirement", "user perspective"],
    "task": ["task", "technical work", "sub-task"],
    "sprint": ["sprint", "iteration", "time-boxed"],
    "backlog": ["backlog", "list of work", "queue"],
    "assignee": ["assignee", "responsible", "who"],
    "priority": ["priority", "urgent", "important"],
    "story point": ["story point", "effort", "estimate", "points"],
    "share_plan": ["share", "stakeholder", "export", "communicate", "link"],
    "scenarios": ["scenario", "alternative", "sandbox", "worst case", "best case"],
    "track_progress": ["track", "report", "progress", "summary screen", "snapshot"],
}


def normalize_text(text):
    return text.lower().strip()


def detect_topic(question):
    q = normalize_text(question)
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in q:
                score += 2 if " " in kw else 1
        if score > 0:
            scores[topic] = score

    if not scores:
        return None

    priority_order = [
        "share_plan", "scenarios", "track_progress", "who_uses_jira",
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

    # Özel Soru: Story vs Task farkı
    if "difference" in q and "story" in q and "task" in q:
        story_text = get_guide_value("story") or "Story section not found."
        task_text = get_guide_value("task") or "Task section not found."
        return (
            "🤖 AI Answer: A story represents a user requirement, while a task is the technical work needed to complete it.\n\n"
            f"📖 Guide (STORY): {story_text}\n\n"
            f"📖 Guide (TASK): {task_text}"
        )

    # Özel Soru: Task nasıl açılır
    if "how" in q and ("create" in q or "open" in q or "add" in q) and "task" in q:
        return (
            "🤖 AI Answer: When creating a task, you must provide a summary, description, priority, assignee, and link it to an Epic.\n\n"
            f"📖 Guide: {get_guide_value('task') or 'Task section not found.'}"
        )

    # Özel Soru: Task neden hatalı
    if ("why" in q or "what" in q) and ("invalid" in q or "wrong" in q or "error" in q):
        return (
            "🤖 AI Answer: A task is considered invalid if it lacks a description, assignee, epic link, or if the summary is too short.\n"
            "Our Validation Agent checks these fields automatically to maintain PMO standards."
        )
        
        
    if topic == "share_plan":
        return f"🤖 AI Answer: Plans are made to be shared easily!\n📖 Guide: {get_guide_value('how do i share a plan with stakeholders?')}"

    if topic == "scenarios":
        return f"🤖 AI Answer: You can use a sandbox environment to test different outcomes.\n📖 Guide: {get_guide_value('how do i plan for different scenarios?')}"

    if topic == "track_progress":
        return f"🤖 AI Answer: Tracking is essential. Check the summary screen.\n📖 Guide: {get_guide_value('how do i track and report progress of a plan?')}"

    if topic == "who_uses_jira":
        return f"🤖 AI Answer: Jira is for everyone, not just developers!\n📖 Guide: {get_guide_value('who uses jira?')}"
    if topic == "jira":
        return f"🤖 AI Answer: Jira is our main tracking tool.\n📖 Guide: {get_guide_value('what is jira?', 'jira')}"

    if topic == "epic":
        return f"🤖 AI Answer: Epics are used to group large bodies of work.\n📖 Guide: {get_guide_value('epic')}"

    if topic == "story":
        return f"🤖 AI Answer:\n📖 Guide: {get_guide_value('story')}"

    if topic == "task":
        return f"🤖 AI Answer:\n📖 Guide: {get_guide_value('task')}"

    if topic == "sprint":
        return f"🤖 AI Answer: We use sprints to complete planned work.\n📖 Guide: {get_guide_value('sprint')}"

    if topic == "backlog":
        return f"🤖 AI Answer:\n📖 Guide: {get_guide_value('backlog')}"

    if topic == "assignee":
        return f"🤖 AI Answer: Every task must have an owner.\n📖 Guide: {get_guide_value('assignee')}"

    if topic == "priority":
        return f"🤖 AI Answer: Prioritize tasks to manage workflow effectively.\n📖 Guide: {get_guide_value('priority')}"

    if topic == "story point":
        return f"🤖 AI Answer:\n📖 Guide: {get_guide_value('story point')}"

    return (
        "🤖 AI Answer: I understood the question but couldn't find an exact match in the guide. "
        "You can ask me about Epic, Story, Task, Sprint, Backlog, Assignee, or Priority."
    )
#eski hali (selin yaptı)
'''import os

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
    )'''