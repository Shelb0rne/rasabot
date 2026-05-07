import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Text

from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict


ROLE_LABELS = {
    "project_manager": "Project Manager",
    "data_analyst": "Data Analyst",
    "data_engineer": "Data Engineer",
    "data_scientist": "Data Scientist",
    "mlops_engineer": "MLOps Engineer",
}

ROLE_ALIASES = {
    "project_manager": [
        "project manager",
        "pm",
        "проджект",
        "менеджер проекта",
        "project",
    ],
    "data_analyst": [
        "data analyst",
        "аналитик",
        "аналитик данных"
    ],
    "data_engineer": [
        "data engineer",
        "инженер данных",
        "data engineering",
        "дата инженер"
    ],
    "data_scientist": [
        "data scientist",
        "ds",
        "ml engineer",
        "дата сайентист"
    ],
    "mlops_engineer": [
        "mlops",
        "mlops engineer",
        "млопс инжинер",
        "млопс"
    ],
}

ROLE_KEYWORDS = {
    "project_manager": [
        "agile",
        "scrum",
        "jira",
        "roadmap",
        "стейкхолдер",
        "срок",
        "команд",
        "план",
        "бизнес",
        "требован",
    ],
    "data_analyst": [
        "sql",
        "dashboard",
        "дашборд",
        "power bi",
        "tableau",
        "метрик",
        "a/b",
        "ab-тест",
        "отчет",
        "аналит",
        "требован",
    ],
    "data_engineer": [
        "etl",
        "elt",
        "airflow",
        "spark",
        "pipeline",
        "пайплайн",
        "хранилищ",
        "бд",
        "database",
        "kafka",
        "данных",
    ],
    "data_scientist": [
        "python",
        "sklearn",
        "pytorch",
        "tensorflow",
        "ml",
        "модель",
        "feature",
        "метрик",
        "классификац",
        "регрес",
        "эксперимент",
    ],
    "mlops_engineer": [
        "docker",
        "kubernetes",
        "k8s",
        "ci/cd",
        "cicd",
        "mlflow",
        "monitoring",
        "мониторинг",
        "деплой",
        "production",
        "cloud",
    ],
}

LEGACY_ROLE_SPECIFIC_QUESTIONS = {
    "project_manager": (
        "Расскажите о случае, когда вы координировали команду, сроки и "
        "ожидания бизнеса в проекте. Как вы принимали решения при конфликте приоритетов?"
    ),
    "data_analyst": (
        "Опишите аналитическую задачу: какие метрики вы выбрали, какие SQL-запросы "
        "или дашборды сделали и как ваши выводы повлияли на бизнес-решение?"
    ),
    "data_engineer": (
        "Расскажите про пайплайн данных, который вы проектировали или поддерживали: "
        "источники, обработка, расписание, контроль качества и отказоустойчивость."
    ),
    "data_scientist": (
        "Опишите ML-задачу, которую вы решали: постановка, признаки, модель, "
        "метрики качества, валидация и что вы улучшали после первого результата."
    ),
    "mlops_engineer": (
        "Расскажите, как вы выводили модель или ML-сервис в production: упаковка, "
        "CI/CD, мониторинг, откаты, инфраструктура и контроль качества модели."
    ),
    "unknown": (
        "Расскажите подробнее, какие задачи вам интересны в ML-проекте: управление, "
        "аналитика, инженерия данных, моделирование или инфраструктура?"
    ),
}


ROLE_SPECIFIC_QUESTIONS = {
    "project_manager": {
        "role_specific_answer_1": (
            "Вопрос по роли Project Manager 1/2: какие 3 артефакта или метрики "
            "вы будете вести, чтобы контролировать ML-проект?"
        ),
        "role_specific_answer_2": (
            "Вопрос по роли Project Manager 2/2: что вы сделаете, если бизнес требует "
            "срок, а команда говорит, что модель пока не готова?"
        ),
    },
    "data_analyst": {
        "role_specific_answer_1": (
            "Вопрос по роли Data Analyst 1/2: какие метрики вы проверите, "
            "чтобы разобраться с падением конверсии или продаж?"
        ),
        "role_specific_answer_2": (
            "Вопрос по роли Data Analyst 2/2: как вы проверите гипотезу, "
            "что новая фича улучшила продукт?"
        ),
    },
    "data_engineer": {
        "role_specific_answer_1": (
            "Вопрос по роли Data Engineer 1/2: из каких шагов состоит надежный "
            "ETL или ELT pipeline?"
        ),
        "role_specific_answer_2": (
            "Вопрос по роли Data Engineer 2/2: что вы будете проверять, "
            "если пайплайн стал падать ночью?"
        ),
    },
    "data_scientist": {
        "role_specific_answer_1": (
            "Вопрос по роли Data Scientist 1/2: какие метрики выберете для "
            "бинарной классификации при дисбалансе классов?"
        ),
        "role_specific_answer_2": (
            "Вопрос по роли Data Scientist 2/2: что вы сделаете, если модель "
            "сильно переобучается?"
        ),
    },
    "mlops_engineer": {
        "role_specific_answer_1": (
            "Вопрос по роли MLOps Engineer 1/2: что нужно для безопасного деплоя "
            "ML-модели в production?"
        ),
        "role_specific_answer_2": (
            "Вопрос по роли MLOps Engineer 2/2: какие сигналы мониторинга модели "
            "вы настроите после релиза?"
        ),
    },
    "unknown": {
        "role_specific_answer_1": (
            "Вопрос 1/2: назовите 2-3 задачи в ML-проекте, которые вам ближе всего, "
            "и объясните почему."
        ),
        "role_specific_answer_2": (
            "Вопрос 2/2: какую конкретную пользу вы могли бы принести ML-команде "
            "в первые недели работы?"
        ),
    },
}

ROLE_SPECIFIC_CRITERIA = {
    "project_manager": {
        "role_specific_answer_1": [
            "roadmap", "роадмап", "план", "backlog", "беклог", "sprint", "спринт",
            "risk", "риск", "срок", "deadline", "метрик", "stakeholder", "стейкхолдер",
        ],
        "role_specific_answer_2": [
            "scope", "скоуп", "приоритет", "риск", "mvp", "компромисс", "trade",
            "stakeholder", "стейкхолдер", "соглас", "эскал", "срок",
        ],
    },
    "data_analyst": {
        "role_specific_answer_1": [
            "конверс", "воронк", "segment", "сегмент", "cohort", "когорт", "sql",
            "дашборд", "dashboard", "retention", "выруч", "продаж",
        ],
        "role_specific_answer_2": [
            "a/b", "ab", "эксперимент", "контроль", "тестов", "p-value", "значим",
            "метрик", "выборк", "sample", "гипотез",
        ],
    },
    "data_engineer": {
        "role_specific_answer_1": [
            "source", "источник", "extract", "transform", "load", "schedule",
            "распис", "quality", "качест", "лог", "retry", "airflow", "etl", "elt",
        ],
        "role_specific_answer_2": [
            "лог", "retry", "повтор", "schema", "схем", "источник", "монитор",
            "alert", "алерт", "данн", "ошиб", "качест",
        ],
    },
    "data_scientist": {
        "role_specific_answer_1": [
            "precision", "recall", "f1", "roc", "auc", "pr-auc", "confusion",
            "матриц", "полнот", "точност", "дисбаланс",
        ],
        "role_specific_answer_2": [
            "validation", "валидац", "cross-validation", "кросс", "regularization",
            "регуляризац", "feature", "признак", "data leakage", "утеч", "прост",
        ],
    },
    "mlops_engineer": {
        "role_specific_answer_1": [
            "docker", "kubernetes", "k8s", "ci/cd", "cicd", "mlflow", "registry",
            "монитор", "rollback", "откат", "production", "деплой",
        ],
        "role_specific_answer_2": [
            "latency", "задерж", "error", "ошиб", "drift", "дрифт", "quality",
            "качест", "alert", "алерт", "монитор", "метрик",
        ],
    },
}

NO_EXPERIENCE_MARKERS = [
    "нет опыта",
    "почти нет",
    "без опыта",
    "начинающий",
    "меньше года",
    "менее года",
    "полгода",
    "0 лет",
]

NO_PROJECT_MARKERS = [
    "не участв",
    "не было проекта",
    "не было проектов",
    "нет проекта",
    "нет проектов",
    "без проекта",
    "без проектов",
    "не работал над проект",
    "не работала над проект",
    "релевантных проектов пока не было",
]


def _latest_text(tracker: Tracker) -> Text:
    return (tracker.latest_message.get("text") or "").strip()


def _latest_text_lower(tracker: Tracker) -> Text:
    return _latest_text(tracker).lower()


def _entities(tracker: Tracker, entity_type: Text) -> List[Any]:
    values = []
    for entity in tracker.latest_message.get("entities", []):
        if entity.get("entity") == entity_type:
            values.append(entity.get("value"))
    return [value for value in values if value]


def _requested_slot(tracker: Tracker, slot_name: Text) -> bool:
    return tracker.get_slot("requested_slot") == slot_name


def _normalize_role(value: Any) -> Text:
    text = str(value or "").lower()
    for role, aliases in ROLE_ALIASES.items():
        if role == text or any(alias in text for alias in aliases):
            return role
    if any(marker in text for marker in ["не знаю", "не уверен", "любая", "unknown"]):
        return "unknown"
    return "unknown"


def _extract_number(text: Text) -> float | None:
    digits = ""
    for char in text:
        if char.isdigit() or char in [".", ","]:
            digits += "." if char == "," else char
        elif digits:
            break

    if digits:
        try:
            value = float(digits)
        except ValueError:
            return None

        if any(marker in text for marker in ["месяц", "месяцев", "месяца", "мес."]):
            return round(value / 12, 2)
        return value

    if any(marker in text for marker in NO_EXPERIENCE_MARKERS):
        return 0.0
    return None


def _has_any_marker(text: Text, markers: List[Text]) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in markers)


def _latest_metadata(tracker: Tracker) -> Dict[Text, Any]:
    return tracker.latest_message.get("metadata") or {}


def _format_telegram_username(username: Any) -> Text:
    if not username:
        return "не указан"
    username = str(username).strip()
    if username.startswith("@"):
        return username
    return f"@{username}"


def _score_role_specific_answers(
    role: Text,
    answer_1: Text,
    answer_2: Text,
) -> tuple[int, List[Text]]:
    criteria = ROLE_SPECIFIC_CRITERIA.get(role)
    if not criteria:
        return 0, []

    score = 0
    reasons = []
    answers = {
        "role_specific_answer_1": str(answer_1 or "").lower(),
        "role_specific_answer_2": str(answer_2 or "").lower(),
    }

    for slot_name, answer_text in answers.items():
        matched = sorted(
            {keyword for keyword in criteria.get(slot_name, []) if keyword in answer_text}
        )
        answer_score = min(len(matched), 3)
        score += answer_score
        if matched:
            question_number = "1" if slot_name.endswith("_1") else "2"
            reasons.append(
                f"ролевой вопрос {question_number}: совпали признаки "
                + ", ".join(matched[:5])
            )

    return score, reasons


def _send_admin_message(text: Text) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID")
    if not token or not admin_chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": admin_chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        response_data = json.loads(response.read().decode("utf-8"))
    return bool(response_data.get("ok"))


class ValidateInterviewForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_interview_form"

    async def required_slots(
        self,
        domain_slots: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Text]:
        if tracker.get_slot("early_rejection_reason"):
            return []
        return domain_slots

    def extract_candidate_name(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not _requested_slot(tracker, "candidate_name"):
            return {}

        names = _entities(tracker, "name")
        if names:
            return {"candidate_name": names[0]}

        text = _latest_text(tracker)
        lowered = text.lower()
        for prefix in ["меня зовут", "мое имя", "моё имя", "я "]:
            if lowered.startswith(prefix):
                return {"candidate_name": text[len(prefix):].strip()}
        return {"candidate_name": text}

    def validate_candidate_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        value = str(slot_value or "").strip()
        if len(value) < 2:
            dispatcher.utter_message(text="Пожалуйста, напишите ваше имя.")
            return {"candidate_name": None}
        return {"candidate_name": value}

    def extract_desired_role(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not _requested_slot(tracker, "desired_role"):
            return {}

        roles = _entities(tracker, "role")
        if roles:
            return {"desired_role": _normalize_role(roles[0])}
        return {"desired_role": _normalize_role(_latest_text(tracker))}

    def validate_desired_role(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        return {"desired_role": _normalize_role(slot_value)}

    def extract_experience_years(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not _requested_slot(tracker, "experience_years"):
            return {}

        years = _entities(tracker, "experience_years")
        if years:
            try:
                return {"experience_years": float(str(years[0]).replace(",", "."))}
            except ValueError:
                pass
        return {"experience_years": _extract_number(_latest_text_lower(tracker))}

    def validate_experience_years(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text="Укажите опыт числом, например: 2 года.")
            return {"experience_years": None}

        years = float(slot_value)
        if years < 0:
            dispatcher.utter_message(text="Опыт не может быть отрицательным. Укажите корректное число лет.")
            return {"experience_years": None}
        if years < 1:
            return {
                "experience_years": years,
                "early_rejection_reason": (
                    "недостаточно опыта: меньше одного года релевантного опыта"
                ),
            }
        return {"experience_years": years, "early_rejection_reason": None}

    def extract_expected_salary(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "expected_salary"):
            return {"expected_salary": _latest_text(tracker)}
        return {}

    def validate_expected_salary(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        value = str(slot_value or "").strip()
        if not value:
            dispatcher.utter_message(
                text="Укажите зарплатные ожидания, например: 180000 рублей или 2000 долларов."
            )
            return {"expected_salary": None}
        return {"expected_salary": value}

    def extract_skills(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not _requested_slot(tracker, "skills"):
            return {}

        skills = _entities(tracker, "skill")
        if skills:
            return {"skills": skills}
        text = _latest_text(tracker)
        return {"skills": [text] if text else []}

    def validate_skills(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="Перечислите хотя бы один навык или инструмент.")
            return {"skills": None}
        return {"skills": slot_value}

    def extract_project_experience(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "project_experience"):
            return {"project_experience": _latest_text(tracker)}
        return {}

    def validate_project_experience(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        value = str(slot_value or "").strip() or "нет опыта"
        if _has_any_marker(value, NO_PROJECT_MARKERS):
            return {
                "project_experience": value,
                "early_rejection_reason": (
                    "недостаточно релевантного проектного опыта"
                ),
            }
        return {"project_experience": value, "early_rejection_reason": None}

    def extract_role_specific_answer_1(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "role_specific_answer_1"):
            return {"role_specific_answer_1": _latest_text(tracker)}
        return {}

    def validate_role_specific_answer_1(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        return {
            "role_specific_answer_1": str(slot_value or "").strip()
            or "нет ответа"
        }

    def extract_role_specific_answer_2(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "role_specific_answer_2"):
            return {"role_specific_answer_2": _latest_text(tracker)}
        return {}

    def validate_role_specific_answer_2(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        return {
            "role_specific_answer_2": str(slot_value or "").strip()
            or "нет ответа"
        }

    def extract_technical_experience(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "technical_experience"):
            return {"technical_experience": _latest_text(tracker)}
        return {}

    def validate_technical_experience(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        return {"technical_experience": str(slot_value or "").strip() or "нет опыта"}

    def extract_business_experience(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if _requested_slot(tracker, "business_experience"):
            return {"business_experience": _latest_text(tracker)}
        return {}

    def validate_business_experience(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        return {"business_experience": str(slot_value or "").strip() or "нет опыта"}


class ActionAskInterviewFormRoleSpecificAnswer1(Action):
    def name(self) -> Text:
        return "action_ask_interview_form_role_specific_answer_1"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        desired_role = _normalize_role(tracker.get_slot("desired_role"))
        questions = ROLE_SPECIFIC_QUESTIONS.get(desired_role, ROLE_SPECIFIC_QUESTIONS["unknown"])
        question = questions["role_specific_answer_1"]
        dispatcher.utter_message(text=question)
        return []


class ActionAskInterviewFormRoleSpecificAnswer2(Action):
    def name(self) -> Text:
        return "action_ask_interview_form_role_specific_answer_2"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        desired_role = _normalize_role(tracker.get_slot("desired_role"))
        questions = ROLE_SPECIFIC_QUESTIONS.get(desired_role, ROLE_SPECIFIC_QUESTIONS["unknown"])
        question = questions["role_specific_answer_2"]
        dispatcher.utter_message(text=question)
        return []


class ActionEvaluateCandidate(Action):
    def name(self) -> Text:
        return "action_evaluate_candidate"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        desired_role = tracker.get_slot("desired_role") or "unknown"
        experience_years = float(tracker.get_slot("experience_years") or 0)
        expected_salary = tracker.get_slot("expected_salary") or "не указано"
        skills = tracker.get_slot("skills") or []
        project_experience = tracker.get_slot("project_experience") or ""
        role_specific_answer_1 = tracker.get_slot("role_specific_answer_1") or ""
        role_specific_answer_2 = tracker.get_slot("role_specific_answer_2") or ""
        technical_experience = tracker.get_slot("technical_experience") or ""
        business_experience = tracker.get_slot("business_experience") or ""
        early_rejection_reason = tracker.get_slot("early_rejection_reason")
        candidate_name = tracker.get_slot("candidate_name") or "не указано"
        metadata = _latest_metadata(tracker)
        telegram_username = _format_telegram_username(metadata.get("telegram_username"))
        telegram_chat_id = metadata.get("telegram_chat_id") or "неизвестен"
        telegram_full_name = metadata.get("telegram_full_name") or "не указано"

        if isinstance(skills, list):
            skills_text = " ".join(str(skill) for skill in skills)
        else:
            skills_text = str(skills)

        if early_rejection_reason:
            result = "Пока не готовы пригласить кандидата на следующий этап"
            admin_message = (
                f"Новый результат первичного интервью\n\n"
                f"Кандидат: {candidate_name}\n"
                f"Telegram: {telegram_username}\n"
                f"Telegram имя: {telegram_full_name}\n"
                f"Chat ID: {telegram_chat_id}\n\n"
                f"Желаемая роль: {ROLE_LABELS.get(str(desired_role), desired_role)}\n"
                f"Опыт: {experience_years:g} лет\n"
                f"Ожидаемая зарплата: {expected_salary}\n"
                f"Навыки: {skills_text or 'не указано'}\n"
                f"Проектный опыт: {project_experience or 'не указано'}\n\n"
                f"Итог: {result}\n"
                f"Причина: {early_rejection_reason}."
            )

            try:
                _send_admin_message(admin_message)
            except Exception as error:
                print(f"Failed to send admin interview report: {error}")

            dispatcher.utter_message(
                text=(
                    "Спасибо за ответы. На текущем этапе мы пока не готовы пригласить "
                    "вас дальше, потому что для этой позиции нужен более релевантный "
                    "практический опыт. Рекомендую добрать опыт на учебных, pet- или "
                    "командных проектах и вернуться к нам позже."
                )
            )
            return [SlotSet("interview_result", result)]

        candidate_text = " ".join(
            [
                str(desired_role),
                skills_text,
                project_experience,
                role_specific_answer_1,
                role_specific_answer_2,
                technical_experience,
                business_experience,
            ]
        ).lower()

        scores = {role: 0 for role in ROLE_LABELS}
        reasons = {role: [] for role in ROLE_LABELS}

        for role, keywords in ROLE_KEYWORDS.items():
            matched = sorted({keyword for keyword in keywords if keyword in candidate_text})
            scores[role] += min(len(matched), 6)
            if matched:
                reasons[role].append("найдены релевантные навыки: " + ", ".join(matched[:5]))

        normalized_desired_role = _normalize_role(desired_role)
        if normalized_desired_role in scores:
            scores[normalized_desired_role] += 2
            reasons[normalized_desired_role].append("кандидат сам выбрал эту роль")
            role_specific_score, role_specific_reasons = _score_role_specific_answers(
                normalized_desired_role,
                role_specific_answer_1,
                role_specific_answer_2,
            )
            scores[normalized_desired_role] += role_specific_score
            reasons[normalized_desired_role].extend(role_specific_reasons)

        if experience_years >= 3:
            for role in scores:
                scores[role] += 1
        elif experience_years < 1:
            for role in scores:
                scores[role] -= 1

        if "нет опыта" in candidate_text or "не занимался" in candidate_text:
            for role in scores:
                scores[role] -= 1

        best_role = max(scores, key=scores.get)
        best_score = scores[best_role]
        role_name = ROLE_LABELS[best_role]

        if best_score >= 5:
            result = f"Подходит на роль {role_name}"
            explanation = "Уровень совпадения: высокий."
        elif best_score >= 3:
            result = f"Возможно подходит на роль {role_name}, но нужен ручной просмотр HR"
            explanation = "Уровень совпадения: средний."
        else:
            result = "Не подходит ни на одну из пяти ролей ML-команды"
            explanation = "Уровень совпадения: низкий."

        best_reasons = reasons.get(best_role) or ["ответы содержат мало явных признаков конкретной роли"]
        admin_message = (
            f"Новый результат первичного интервью\n\n"
            f"Кандидат: {candidate_name}\n"
            f"Telegram: {telegram_username}\n"
            f"Telegram имя: {telegram_full_name}\n"
            f"Chat ID: {telegram_chat_id}\n\n"
            f"Желаемая роль: {ROLE_LABELS.get(str(desired_role), desired_role)}\n"
            f"Опыт: {experience_years:g} лет\n"
            f"Ожидаемая зарплата: {expected_salary}\n"
            f"Навыки: {skills_text}\n"
            f"Проектный опыт: {project_experience}\n"
            f"Ролевой вопрос 1: {role_specific_answer_1}\n"
            f"Ролевой вопрос 2: {role_specific_answer_2}\n"
            f"Технический опыт: {technical_experience}\n"
            f"Бизнес/коммуникации: {business_experience}\n\n"
            f"Итог: {result}\n"
            f"{explanation}\n"
            f"Основные причины: {'; '.join(best_reasons)}.\n"
            f"Баллы по ролям: "
            f"Project Manager - {scores['project_manager']}, "
            f"Data Analyst - {scores['data_analyst']}, "
            f"Data Engineer - {scores['data_engineer']}, "
            f"Data Scientist - {scores['data_scientist']}, "
            f"MLOps Engineer - {scores['mlops_engineer']}."
        )

        admin_sent = False
        try:
            admin_sent = _send_admin_message(admin_message)
        except Exception as error:
            print(f"Failed to send admin interview report: {error}")

        if admin_sent:
            dispatcher.utter_message(
                text="Спасибо! Я завершил первичное интервью и передал результаты HR."
            )
        else:
            dispatcher.utter_message(
                text=(
                    "Спасибо! Я завершил первичное интервью, но не смог отправить "
                    "результат HR. Проверьте ADMIN_CHAT_ID и доступ action server к Telegram API."
                )
            )
        return [SlotSet("interview_result", result)]
