import requests

import pandas as pd

import chess.pgn
import io

class DataCollector():
    """
    A class for collecting chess game data from Chess.com.

    Attributes:
        username (str): The Chess.com username of the player.

    Methods:
        fetch_games: Fetches the games played by the user and returns them as a pandas DataFrame.
        get_all_pgns: Returns all the PGNs (Portable Game Notation) of the user's games.
        pgn_to_san: Converts a PGN to Standard Algebraic Notation (SAN).
        get_user_color: Determines the color (white or black) of the user in a game.
        get_san_and_color: Returns a list of tuples containing the SAN moves and user color for each game.
        get_all_game_states: Returns a list of game states at each move for all games played by the user.
    """

    def __init__(self, username: str):
        """
        Initializes a DataCollector object.

        Args:
            username (str): The Chess.com username of the player.
        """
        self.username = username
    
    def fetch_games(self) -> pd.DataFrame:
        """
        Fetches the games played by the user and returns them as a pandas DataFrame.

        Returns:
            pd.DataFrame: A DataFrame containing the games played by the user.
        """
        headers = {"User-Agent": "MyChessDataFetcher/1.0"}
        archives_url = f"https://api.chess.com/pub/player/{self.username}/games/archives"

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

    def get_all_pgns(self) -> pd.DataFrame:
        """
        Returns all the PGNs (Portable Game Notation) of the user's games.

        Returns:
            pd.DataFrame: A DataFrame containing the PGNs of the user's games.
        """
        games = self.fetch_games()
        return games['pgn']

    def pgn_to_san(self, pgn: str) -> list[str]:
        """
        Converts a PGN to Standard Algebraic Notation (SAN).

        Args:
            pgn (str): The PGN to be converted.

        Returns:
            list[str]: A list of SAN moves extracted from the PGN.
        """
        # Parse the PGN using python-chess
        pgn_io = io.StringIO(pgn)
        game = chess.pgn.read_game(pgn_io)

        # Initialize an empty list to hold moves
        moves = []

        # Iterate through the moves of the main line
        board = game.board()
        for move in game.mainline_moves():
            # Convert the move to Standard Algebraic Notation (SAN)
           san = board.san(move)
           moves.append(san)
           board.push(move)
        
        return moves

    def get_user_color(self, pgn: str) -> str:
        """
        Determines the color (white or black) of the user in a game.

        Args:
            pgn (str): The PGN of the game.

        Returns:
            str: The color of the user in the game ('white' or 'black').
        """
        # Parse the PGN using python-chess
        pgn_io = io.StringIO(pgn)
        game = chess.pgn.read_game(pgn_io)

        # Get the color of the user
        if game.headers["White"] == self.username:
            return "white"
        else:
            return "black"

    def get_san_and_color(self) -> tuple[list, str]:
        """
        Returns a list of tuples containing the SAN moves and user color for each game.

        Returns:
            tuple[list, str]: A tuple containing a list of SAN moves and the user color for each game.
        """
        all_sans_and_colors = []
        
        all_pgns = self.get_all_pgns()
        for pgn in all_pgns:
            san = self.pgn_to_san(pgn)
            user_color = self.get_user_color(pgn)
            all_sans_and_colors.append((san, user_color))
        return all_sans_and_colors

    def get_all_game_states(self) -> list[str]:
        """
        Returns a list of game states at each move for all games played by the user.

        Returns:
            list[str]: A list of game states at each move for all games played by the user.
        """
        all_game_states = []
        for san, user_color in self.get_san_and_color():
            if user_color == 'white':
                first_user_move = 0
            else:
                first_user_move = 1
            for user_move in range(len(san) // 2):
                current_game_state = san[:first_user_move + 2 * user_move]
                all_game_states.append(current_game_state)
        return all_game_states