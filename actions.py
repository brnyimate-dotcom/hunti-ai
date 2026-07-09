import pyautogui
from typing import Any, Dict

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def safe_click(x: int, y: int) -> None:
    """Move to a valid screen coordinate and click there."""
    screen_width, screen_height = pyautogui.size()
    safe_x = _clamp(x, 0, screen_width - 1)
    safe_y = _clamp(y, 0, screen_height - 1)
    pyautogui.moveTo(safe_x, safe_y)
    pyautogui.click()


def safe_type(text: str) -> None:
    """Type text using the keyboard."""
    if text is None:
        raise ValueError("No text provided for typing.")
    pyautogui.write(str(text), interval=0.03)


def safe_scroll(amount: int) -> None:
    """Scroll the mouse wheel by the given amount."""
    pyautogui.scroll(amount)


def perform_action(action_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a parsed action payload from the AI safely."""
    action = action_payload.get("action")
    x = int(action_payload.get("x", 0))
    y = int(action_payload.get("y", 0))
    text = action_payload.get("text", "")

    if action == "click":
        safe_click(x, y)
        return {"status": "clicked", "x": x, "y": y}
    if action == "type":
        safe_type(text)
        return {"status": "typed", "text": text}
    if action == "scroll":
        safe_scroll(int(text) if str(text).lstrip("-+").isdigit() else 0)
        return {"status": "scrolled", "amount": text}
    if action == "done":
        return {"status": "done"}

    raise ValueError(f"Unsupported action: {action}")
