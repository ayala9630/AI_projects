import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE_FILE = ROOT / "venue_parser.py"
OUTPUT_FILE = ROOT / "data" / "venues.json"


def main() -> None:
    # The existing venue_parser.py contains JSON text,
    # not executable Python code.
    source_text = SOURCE_FILE.read_text(
        encoding="utf-8"
    )

    data = json.loads(source_text)

    venues = data.get("venues")

    if not isinstance(venues, list):
        raise ValueError(
            "Expected a JSON object containing a venues list"
        )

    for index, venue in enumerate(venues, start=1):
        if not isinstance(venue, dict):
            raise ValueError(
                f"Venue record {index} is not an object"
            )

        if not venue.get("id"):
            raise ValueError(
                f"Venue record {index} has no ID"
            )

        if not venue.get("name"):
            raise ValueError(
                f"Venue record {index} has no name"
            )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            venues,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Exported {len(venues)} venues")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()