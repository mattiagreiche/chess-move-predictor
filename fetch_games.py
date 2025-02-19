import requests
import pandas as pd

def fetch_games(username: str) -> pd.DataFrame:

    headers = {"User-Agent": "MyChessDataFetcher/1.0"}
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    # Get the list of archive URLs
    archives_response = requests.get(archives_url, headers=headers)
    if archives_response.status_code != 200:
        print(f"Failed to fetch archives: {archives_response.status_code}")
        exit()

    months = archives_response.json().get("archives", [])


    all_games = []  # Initialize an empty list to collect all games
    
    # Fetch games from each archive
    for month_url in months:
        month_response = requests.get(month_url, headers=headers)
        if month_response.status_code != 200:
            print(f"Failed to fetch month {month_url}: {month_response.status_code}")
            continue  # Skip this month and continue with the next
        month_data = month_response.json()
        games = month_data.get("games", [])
        all_games.extend(games)  # Add games to the list

    # Return the games as a pandas DataFrame
    return pd.DataFrame(all_games)
