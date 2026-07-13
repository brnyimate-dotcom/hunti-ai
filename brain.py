import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from groq import Groq
from database import get_connection

load_dotenv()


def _load_api_key(name: str) -> str:
    """Load an API key from the environment or .env file."""
    api_key = os.getenv(name)
    if not api_key:
        raise EnvironmentError(
            f"{name} not found. Set it in your environment or in a .env file."
        )
    return api_key


def init_groq_client() -> Groq:
    """Initialize the Groq client for text tasks."""
    api_key = _load_api_key("GROQ_API_KEY")
    return Groq(api_key=api_key)


def save_leads_to_db(leads: List[Dict[str, Any]]) -> int:
    """Save leads to the database and return the count."""
    conn = get_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    for lead in leads:
        cursor.execute('''
            INSERT INTO leads (company_name, address, website, phone, rating)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            lead.get('name', 'Unknown'),
            lead.get('address', ''),
            lead.get('website', ''),
            lead.get('phone', ''),
            lead.get('rating', 0.0)
        ))
        saved_count += 1
    
    conn.commit()
    conn.close()
    return saved_count


def get_all_leads_from_db() -> List[Dict[str, Any]]:
    """Retrieve all leads from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_lead_count_from_db() -> int:
    """Get total number of leads."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM leads')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def read_leads(file_path: str = "leads.json") -> List[Dict[str, Any]]:
    """Read leads - now from database instead of JSON."""
    return get_all_leads_from_db()


def build_sales_prompt(lead: Dict[str, Any]) -> str:
    """Build the prompt for a single lead."""
    company_name = lead.get("company_name", lead.get("name", "Company"))
    website = lead.get("website", "their website")

    return (
        f"Act as a professional B2B sales rep. "
        f"Write a short, personalized cold email to the owner of {company_name} at {website}. "
        "We offer AI automation services to help them save time on data entry and admin tasks. "
        "Keep it under 100 words, friendly, and end with a call to action to book a 10-minute demo."
    )


def generate_pitch(client: Groq, lead: Dict[str, Any]) -> str:
    """Generate a personalized pitch using GROQ and save to database."""
    prompt = build_sales_prompt(lead)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API request failed for {lead.get('company_name', 'unknown')}: {exc}") from exc

    pitch_text = response.choices[0].message.content
    if not pitch_text:
        raise RuntimeError(f"Groq response did not include text for lead {lead.get('company_name', 'unknown')}")
    
    # Save pitch to database
    lead_id = lead.get('id')
    if lead_id:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pitches (lead_id, pitch_text)
            VALUES (?, ?)
        ''', (lead_id, pitch_text.strip()))
        conn.commit()
        conn.close()
    
    return pitch_text.strip()


def save_pitches(pitches: List[Dict[str, str]], output_path: str = "pitches.json") -> None:
    """Save generated pitches to database (JSON file is now optional)."""
    try:
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(pitches, out_file, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"Warning: Could not save JSON file: {exc}")


def build_pitches(
    leads_file: str = "leads.json",
    output_file: str = "pitches.json",
) -> List[Dict[str, str]]:
    """Read leads from database, generate pitches with Groq, and save."""
    leads = get_all_leads_from_db()
    
    if not leads:
        raise ValueError("No leads found in database. Please scrape leads first.")
    
    client = init_groq_client()
    pitches: List[Dict[str, str]] = []

    for lead in leads:
        company_name = lead.get("company_name", "Unknown")
        try:
            pitch = generate_pitch(client, lead)
            pitches.append({"company_name": company_name, "pitch": pitch})
        except Exception as exc:
            print(f"Warning: Skipping lead {company_name}: {exc}")

    save_pitches(pitches, output_file)
    return pitches


def get_pitches_from_db() -> List[Dict[str, Any]]:
    """Get all pitches with their associated lead info."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.pitch_text, p.created_at, l.company_name, l.website
        FROM pitches p
        JOIN leads l ON p.lead_id = l.id
        ORDER BY p.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_email_sent(pitch_id: int, recipient_email: str, subject: str) -> None:
    """Log that an email was sent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO emails (pitch_id, recipient_email, subject, status)
        VALUES (?, ?, ?, 'sent')
    ''', (pitch_id, recipient_email, subject))
    conn.commit()
    conn.close()


def ask_assistant(user_task: str, temperature: float = 0.2) -> Dict[str, Any]:
    """Query GROQ text model to act as a smart assistant."""
    client = init_groq_client()
    
    prompt = (
        "You are Hunti, a highly intelligent desktop AI assistant. "
        "Analyze the user's request and provide a helpful, concise, and professional response. "
        "Return ONLY valid JSON with keys: thought, text. "
        "'thought' should be a brief internal reasoning. 'text' is your final answer to the user. "
        f"User task: {user_task}."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            temperature=max(0.0, min(1.0, temperature)),
            max_tokens=500,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq assistant request failed: {exc}") from exc

    response_text = response.choices[0].message.content
    return parse_text_response(response_text)


def parse_text_response(response_text: str) -> Dict[str, Any]:
    """Parse the model output as JSON, with a fallback for raw text."""
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "").strip()
    
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Fallback if the model just returns raw text instead of JSON
        return {"thought": "Raw text response", "text": cleaned}

    # Ensure we have the required keys
    if "text" not in parsed:
        parsed["text"] = str(parsed)
    if "thought" not in parsed:
        parsed["thought"] = "Processing request..."

    return parsed


def _run_pitch_generation() -> None:
    """Generate pitches from leads and save them to database."""
    try:
        pitches = build_pitches()
        print(f"Generated {len(pitches)} pitches and saved to database.")
    except Exception as exc:
        print(f"Pitch generation failed: {exc}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        _run_pitch_generation()
    elif len(sys.argv) >= 2 and sys.argv[1].lower() in {"generate", "pitches"}:
        _run_pitch_generation()
    else:
        print("Usage:")
        print("  python brain.py")
        print("  python brain.py generate")
        sys.exit(1)