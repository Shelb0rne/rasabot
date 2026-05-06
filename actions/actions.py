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
        "аналитика данных",
        "дашборд",
        "метрики",
    ],
    "data_engineer": [
        "data engineer",
        "инженер данных",
        "data engineering",
        "etl",
        "пайплайн",
    ],
    "data_scientist": [
        "data scientist",
        "ds",
        "ml engineer",
        "машинное обучение",
        "модель",
    ],
    "mlops_engineer": [
        "mlops",
        "mlops engineer",
        "инфраструктура",
        "деплой",
        "production",
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
            return float(digits)
        except ValueError:
            return None

    if any(marker in text for marker in ["нет опыта", "почти нет", "без опыта", "начинающий"]):
        return 0.0
    return None


class ValidateInterviewForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_interview_form"

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
        return {"experience_years": years}

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
        return {"project_experience": str(slot_value or "").strip() or "нет опыта"}

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
        skills = tracker.get_slot("skills") or []
        project_experience = tracker.get_slot("project_experience") or ""
        technical_experience = tracker.get_slot("technical_experience") or ""
        business_experience = tracker.get_slot("business_experience") or ""

        if isinstance(skills, list):
            skills_text = " ".join(str(skill) for skill in skills)
        else:
            skills_text = str(skills)

        candidate_text = " ".join(
            [
                str(desired_role),
                skills_text,
                project_experience,
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
        message = (
            f"Итог первичного интервью: {result}.\n"
            f"{explanation}\n"
            f"Основные причины: {'; '.join(best_reasons)}.\n"
            f"Баллы по ролям: "
            f"Project Manager - {scores['project_manager']}, "
            f"Data Analyst - {scores['data_analyst']}, "
            f"Data Engineer - {scores['data_engineer']}, "
            f"Data Scientist - {scores['data_scientist']}, "
            f"MLOps Engineer - {scores['mlops_engineer']}."
        )

        dispatcher.utter_message(text=message)
        return [SlotSet("interview_result", result)]
