from bs4 import BeautifulSoup
import csv
from datetime import datetime


def parse_duration(duration_str):
    """Convert duration HH:MM:SS to decimal hours"""
    parts = duration_str.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return round(hours + minutes / 60 + seconds / 3600, 2)


def parse_winloss(winloss_str):
    """Extract numeric value from win/loss string"""
    clean_str = winloss_str.replace("$", "").replace(",", "").strip()
    return float(clean_str)


def parse_stakes(stakes_str):
    """Convert $0.05/$0.1 to 0.05/0.1"""
    stakes = stakes_str.strip().replace("$", "").replace(" ", "")
    return stakes


def parse_date(date_str, year=None):
    """Convert 'Nov 10, 23:00' to MM/DD/YYYY format"""
    try:
        date_part = date_str.split(",")[0].strip()

        if year is None:
            year = datetime.now().year

        date_obj = datetime.strptime(f"{date_part} {year}", "%b %d %Y")
        return date_obj.strftime("%m/%d/%Y")
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return ""


def parse_game_type(table_name):
    """Extract game type from table name"""
    table_upper = table_name.upper()
    if "NLH" in table_upper or "HOLDEM" in table_upper or "HOLD'EM" in table_upper:
        return "Texas Hold'em"
    elif "PLO" in table_upper or "OMAHA" in table_upper:
        return "Omaha"
    else:
        return "Texas Hold'em"


def estimate_buyin_from_stakes(stakes_str):
    """Estimate typical buy-in based on stakes (100 big blinds)"""
    parts = stakes_str.replace("$", "").split("/")
    big_blind = float(parts[1])
    return round(big_blind * 100, 2)


def convert_pokercraft_to_bink(
    html_file,
    output_csv,
    year=None,
    default_buy_in=None,
    location="Natural8",
    bankroll="Natural8",
):
    """
    Convert Pokercraft HTML to Bink CSV format

    Args:
        html_file: Path to HTML file containing tbody
        output_csv: Path for output CSV file
        year: Year for sessions (default: current year)
        default_buy_in: Default buy-in amount (if None, auto-estimate from stakes)
        location: Location name
        bankroll: Bankroll name
    """

    # Read HTML file
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all table rows
    rows = soup.find_all("tr", {"mat-row": True})

    if not rows:
        print(
            "Warning: No table rows found. Make sure HTML contains <tr mat-row> elements"
        )
        return []

    sessions = []

    for idx, row in enumerate(rows):
        cells = row.find_all("td", {"mat-cell": True})
        session = {}

        for cell in cells:
            classes = cell.get("class", [])

            # Session Start
            if "mat-column-SessionStart" in classes:
                date_span = cell.find("span", class_="mat-tooltip-trigger")
                if date_span:
                    date_text = date_span.get_text(strip=True)
                    date_text = " ".join(date_text.split())
                    session["Date"] = parse_date(date_text, year)

            # Stakes
            elif "mat-column-Stakes" in classes:
                stakes_text = cell.get_text(strip=True)
                session["Stakes"] = parse_stakes(stakes_text)

            # Table
            elif "mat-column-Table" in classes:
                table_name = cell.get_text(strip=True)
                session["Table"] = table_name
                session["Game Type"] = parse_game_type(table_name)

            # Hands
            elif "mat-column-Hands" in classes:
                session["Hands"] = cell.get_text(strip=True)

            # Duration
            elif "mat-column-Duration" in classes:
                duration_text = cell.get_text(strip=True)
                session["Duration"] = parse_duration(duration_text)

            # Win/Loss
            elif "mat-column-Winloss" in classes:
                winloss = parse_winloss(cell.get_text(strip=True))
                session["Winloss"] = winloss

        # Calculate Buyin and Cashout
        if session:
            if default_buy_in:
                buyin = default_buy_in
            else:
                buyin = estimate_buyin_from_stakes(session.get("Stakes", ""))

            session["Buyin"] = buyin
            # IMPORTANT: Cashout = Buyin + Winloss
            session["Cashout"] = round(buyin + session.get("Winloss", 0), 2)

            sessions.append(session)
            print(
                f"Session {idx + 1}: Buyin=${session['Buyin']}, Winloss=${session.get('Winloss', 0)}, Cashout=${session['Cashout']}"
            )

    if not sessions:
        print("No sessions found. Please check your HTML file.")
        return []

    # Write CSV in Bink format
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Date",
            "Duration",
            "Buyin",
            "Cashout",
            "Stakes",
            "Cash/Tourney",
            "Live/online",
            "Location",
            "Game Type",
            "Limit Type",
            "Expenses",
            "Bankroll",
            "Action Sold Percentage",
            "Notes",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for session in sessions:
            # Create notes without commas to avoid CSV issues
            table = session.get("Table", "")
            hands = session.get("Hands", "")
            notes = f"{table} - {hands} hands" if table and hands else ""

            row = {
                "Date": session.get("Date", ""),
                "Duration": session.get("Duration", 0.0),
                "Buyin": session.get("Buyin", 0.0),
                "Cashout": session.get("Cashout", 0.0),
                "Stakes": session.get("Stakes", ""),
                "Cash/Tourney": "Cash",
                "Live/online": "Online",
                "Location": location,
                "Game Type": session.get("Game Type", "Texas Hold'em"),
                "Limit Type": "No Limit",
                "Expenses": 0.0,
                "Bankroll": bankroll,
                "Action Sold Percentage": 0.0,
                "Notes": notes,
            }
            writer.writerow(row)

    print(f"\n✓ Conversion complete! {len(sessions)} sessions exported to {output_csv}")
    return sessions


# Usage
if __name__ == "__main__":
    import sys

    # Configuration
    CONFIG = {
        "html_file": "pokercraft_sessions.html",  # Your input HTML file
        "output_csv": "bink_import.csv",  # Output CSV file
        "year": 2024,  # Year for sessions (or None for current year)
        "default_buy_in": None,  # Fixed buy-in amount (or None to auto-estimate)
        "location": "Natural8",  # Poker site/location name
        "bankroll": "Natural8",  # Bankroll name
    }

    print("=" * 70)
    print("Pokercraft to Bink Converter")
    print("=" * 70)
    print(f"Input file: {CONFIG['html_file']}")
    print(f"Output file: {CONFIG['output_csv']}")
    print(f"Year: {CONFIG['year'] or 'Current year'}")
    print(f"Buy-in: ${CONFIG['default_buy_in'] or 'Auto-estimate from stakes'}")
    print(f"Location: {CONFIG['location']}")
    print(f"Bankroll: {CONFIG['bankroll']}")
    print("=" * 70)
    print()

    try:
        sessions = convert_pokercraft_to_bink(**CONFIG)

        if sessions:
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            total_buy_in = sum(s.get("Buyin", 0) for s in sessions)
            total_cashout = sum(s.get("Cashout", 0) for s in sessions)
            total_profit = total_cashout - total_buy_in

            print(f"Total sessions: {len(sessions)}")
            print(f"Total buy-in: ${total_buy_in:.2f}")
            print(f"Total cash-out: ${total_cashout:.2f}")
            print(f"Total profit/loss: ${total_profit:.2f}")
            print("=" * 70)
    except FileNotFoundError:
        print(f"Error: Could not find file '{CONFIG['html_file']}'")
        print("Please save your Pokercraft HTML to this file and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
