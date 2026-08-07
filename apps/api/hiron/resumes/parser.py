"""Structured NER Resume Parser module extracting candidate profile fields and confidence scoring per Database Design §5.6."""

import re
from typing import Any

import structlog

logger = structlog.get_logger("hiron.resumes.parser")

PARSER_MODEL_VERSION = "spacy-en_core_web_trf-3.8.0"

_nlp: Any = None

def get_nlp() -> Any:
    """Lazy load the SpaCy transformer model to avoid slow process startup."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            # Load the specific transformer model required by architecture
            _nlp = spacy.load("en_core_web_trf")
        except Exception as e:
            logger.warning("Failed to load SpaCy model en_core_web_trf", error=str(e))
            _nlp = "failed"  # Type hack to avoid repeatedly trying to load if failed
    return _nlp if _nlp != "failed" else None

TECH_SKILLS_TAXONOMY = {
    "Python",
    "Java",
    "C++",
    "C#",
    "Go",
    "Golang",
    "Rust",
    "JavaScript",
    "TypeScript",
    "React",
    "React.js",
    "Vue",
    "Vue.js",
    "Angular",
    "Node.js",
    "Express",
    "Next.js",
    "FastAPI",
    "Django",
    "Flask",
    "Spring",
    "Spring Boot",
    "ASP.NET",
    "Ruby",
    "Rails",
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "MongoDB",
    "Redis",
    "Elasticsearch",
    "Cassandra",
    "Docker",
    "Kubernetes",
    "AWS",
    "Amazon Web Services",
    "GCP",
    "Google Cloud",
    "Azure",
    "Terraform",
    "Ansible",
    "Jenkins",
    "GitHub Actions",
    "GitLab CI",
    "CI/CD",
    "Git",
    "REST",
    "RESTful",
    "GraphQL",
    "gRPC",
    "Kafka",
    "RabbitMQ",
    "Celery",
    "Machine Learning",
    "Deep Learning",
    "PyTorch",
    "TensorFlow",
    "scikit-learn",
    "spaCy",
    "NLTK",
    "Pandas",
    "NumPy",
    "OpenCV",
    "SQL",
    "NoSQL",
    "Linux",
    "Unix",
    "HTML",
    "CSS",
    "Sass",
    "Tailwind",
    "TailwindCSS",
    "Redux",
    "Zustand",
    "Webpack",
    "Vite",
}

DEGREE_KEYWORDS = [
    "Bachelor",
    "B.S.",
    "B.A.",
    "B.Sc.",
    "B.E.",
    "B.Tech",
    "Master",
    "M.S.",
    "M.A.",
    "M.Sc.",
    "M.E.",
    "M.Tech",
    "MBA",
    "Doctor",
    "Ph.D.",
    "PhD",
    "Associate",
    "Diploma",
]


class ResumeParser:
    """Structured resume parser using regex and NLP taxonomy matching."""

    def __init__(self, model_version: str = PARSER_MODEL_VERSION) -> None:
        self.model_version = model_version

    def extract_email(self, text: str) -> str | None:
        """Extract email address from text using regex."""
        match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        return match.group(0) if match else None

    def extract_phone(self, text: str) -> str | None:
        """Extract phone number from text using regex."""
        match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        return match.group(0) if match else None

    def extract_linkedin(self, text: str) -> str | None:
        """Extract LinkedIn profile URL from text."""
        match = re.search(
            r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", text, re.IGNORECASE
        )
        if match:
            return match.group(0)
        match_handle = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if match_handle:
            return f"https://linkedin.com/in/{match_handle.group(1)}"
        return None

    def extract_full_name(self, text: str) -> str:
        """Extract candidate full name from top header section of raw text."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            # Skip lines containing email, phone, or URLs
            if "@" in line or "http" in line or "www." in line or "linkedin" in line:
                continue
            # Clean non-alphabetical title characters
            cleaned = re.sub(r"[^\w\s.-]", "", line).strip()
            words = cleaned.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w[0].isalpha()):
                return cleaned

        if lines:
            first_line = re.sub(r"[^\w\s.-]", "", lines[0]).strip()
            if first_line:
                return first_line
        return "Parsed Candidate"

    def extract_location(self, text: str) -> str | None:
        """Extract location string (e.g. San Francisco, CA or London, UK)."""
        match = re.search(r"\b([A-Z][a-zA-S\s]+,\s*(?:[A-Z]{2}|[A-Z][a-z]+))\b", text)
        return match.group(1).strip() if match else None

    def extract_skills(self, text: str) -> list[str]:
        """Extract matching tech skills from taxonomy."""
        extracted: list[str] = []
        text_lower = text.lower()
        for skill in TECH_SKILLS_TAXONOMY:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                extracted.append(skill)

        # Preserve canonical order and uniqueness
        return sorted(set(extracted))

    def extract_summary(self, text: str) -> str | None:
        """Extract professional summary section if present."""
        match = re.search(
            r"(?:SUMMARY|PROFILE|ABOUT ME|OBJECTIVE)[:\n\s]+(.*?)(?=\n\n|\n[A-Z\s]{4,}:|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            summary_text = match.group(1).strip()
            return summary_text[:500] if summary_text else None
        return None

    def extract_experience(self, text: str) -> list[dict[str, Any]]:
        """Extract work experience entries."""
        experience_list: list[dict[str, Any]] = []
        exp_section_match = re.search(
            r"(?:EXPERIENCE|WORK HISTORY|EMPLOYMENT)[:\n\s]+(.*?)(?=\n[A-Z\s]{4,}:|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        exp_text = exp_section_match.group(1) if exp_section_match else text

        lines = [line_str.strip() for line_str in exp_text.split("\n") if line_str.strip()]
        for line in lines:
            # Look for job title / company patterns
            if any(
                title in line.lower()
                for title in [
                    "engineer",
                    "developer",
                    "manager",
                    "lead",
                    "architect",
                    "analyst",
                    "consultant",
                    "specialist",
                ]
            ):
                title_company = line.split(" at ") if " at " in line else line.split(" - ")
                title = title_company[0].strip()
                company = title_company[1].strip() if len(title_company) > 1 else None
                experience_list.append(
                    {
                        "title": title,
                        "company": company,
                        "location": None,
                        "start_date": None,
                        "end_date": None,
                        "is_current": "present" in line.lower() or "current" in line.lower(),
                        "description": line,
                    }
                )
                if len(experience_list) >= 5:
                    break
        return experience_list

    def extract_education(self, text: str) -> list[dict[str, Any]]:
        """Extract education entries."""
        education_list: list[dict[str, Any]] = []
        edu_section_match = re.search(
            r"(?:EDUCATION|ACADEMIC BACKGROUND)[:\n\s]+(.*?)(?=\n[A-Z\s]{4,}:|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        edu_text = edu_section_match.group(1) if edu_section_match else text

        lines = [line_str.strip() for line_str in edu_text.split("\n") if line_str.strip()]
        for line in lines:
            if any(degree.lower() in line.lower() for degree in DEGREE_KEYWORDS):
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", line)
                year = int(year_match.group(1)) if year_match else None
                education_list.append(
                    {
                        "degree": line,
                        "institution": None,
                        "graduation_year": year,
                    }
                )
                if len(education_list) >= 3:
                    break
        return education_list

    def calculate_confidence(self, parsed_data: dict[str, Any]) -> float:
        """Calculate parse confidence score between 0.0 and 1.0 based on field presence."""
        score = 0.0
        if parsed_data.get("full_name") and parsed_data["full_name"] != "Parsed Candidate":
            score += 0.25
        if parsed_data.get("email") or parsed_data.get("phone"):
            score += 0.25
        if parsed_data.get("skills"):
            score += 0.25
        if parsed_data.get("experience") or parsed_data.get("education"):
            score += 0.25
        return round(score, 2)

    def parse(self, text: str) -> tuple[dict[str, Any], float, dict[str, Any] | None]:  # noqa: C901
        """Parse raw resume text into structured parsed_data JSON schema and calculate confidence."""
        full_name = self.extract_full_name(text)
        email = self.extract_email(text)
        phone = self.extract_phone(text)
        location = self.extract_location(text)
        linkedin_url = self.extract_linkedin(text)
        summary = self.extract_summary(text)
        skills = self.extract_skills(text)
        experience = self.extract_experience(text)
        education = self.extract_education(text)

        parsed_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin_url": linkedin_url,
            "summary": summary,
            "skills": skills,
            "experience": experience,
            "education": education,
            "certifications": [],
            "languages": [],
        }

        # Hybrid SpaCy Enhancement
        nlp = get_nlp()
        telemetry: dict[str, Any] | None = None

        if nlp:
            import time
            start_time = time.time()
            try:
                # Truncate to first 10,000 characters to prevent massive transformer memory spikes
                doc = nlp(text[:10000])

                persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
                # Only override if deterministic failed or SpaCy found a more complete name
                if persons and (parsed_data["full_name"] == "Parsed Candidate" or len(persons[0].split()) > len(str(parsed_data.get("full_name", "")).split())):
                    parsed_data["full_name"] = persons[0]

                if not parsed_data["location"]:
                    locations = [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")]
                    if locations:
                        parsed_data["location"] = locations[0]

                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]

                # Enhance experience companies if missing
                if orgs and isinstance(experience, list):
                    for exp in experience:
                        if isinstance(exp, dict) and not exp.get("company"):
                            exp["company"] = orgs[0]  # Simplistic enhancement

                # Enhance education institutions if missing
                if orgs and isinstance(education, list):
                    for edu in education:
                        if isinstance(edu, dict) and not edu.get("institution"):
                            edu["institution"] = orgs[0]  # Simplistic enhancement

                # Enhance dates if missing
                if dates and isinstance(experience, list):
                    for exp in experience:
                        if isinstance(exp, dict) and not exp.get("start_date"):
                            exp["start_date"] = dates[0]

                latency_ms = int((time.time() - start_time) * 1000)
                telemetry = {
                    "model_version": self.model_version,
                    "latency_ms": latency_ms,
                    "status": "success",
                    "error_type": None,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                telemetry = {
                    "model_version": self.model_version,
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error_type": e.__class__.__name__,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
                logger.warning("SpaCy inference failed, falling back to deterministic extraction", error=str(e))

        confidence = self.calculate_confidence(parsed_data)
        return parsed_data, confidence, telemetry
