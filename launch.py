import datetime
import traceback
from pathlib import Path


def main() -> None:
    try:
        from main import run_app

        run_app()
    except Exception:
        log_path = Path(__file__).with_name("launch.log")
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write("=== Hunti AI launch failure ===\n")
            log_file.write(datetime.datetime.now().isoformat() + "\n")
            traceback.print_exc(file=log_file)
            log_file.write("\n")
        raise


if __name__ == "__main__":
    main()
