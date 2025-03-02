import requests

import pandas as pd
import numpy as np

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
        
        months.reverse() # Reverse the list so that the most recent months are first

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
            if len(all_games) > 10_000:
                break # Stop after collecting 10,000 games

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

    def pgn_to_boards(self, pgn: str) -> list[chess.Board]:
        """
        Converts a PGN to a list of chess.Board objects for each game state in the PGN (only on user turns). 

        Args:
            pgn (str): The PGN to be converted.

        Returns:
            list[chess.Board]: A list of chess.Board objects extracted from the PGN. The chess.Board objects only contain game states for which it is the user's turn.
        """
        # Parse the PGN using python-chess
        pgn_io = io.StringIO(pgn)
        game = chess.pgn.read_game(pgn_io)

        # Initialize an empty list to hold boards
        boards = []

        # Iterate through the moves of the main line
        board = game.board()
        user_color = self.get_user_color(pgn)
        if user_color == 'white':
            user_starting_move = 0
        else:
            user_starting_move = 1
        for move_number, move in enumerate(game.mainline_moves()):
            if move_number % 2 == user_starting_move: # Only add the board if it is the user's turn to move. Works by checking if move number is even if user is white, odd if user is black.
                if user_color == 'white':
                    boards.append(board.copy())
                else:
                    boards.append(board.mirror().copy()) # Mirror the board if user is black, so that resulting matrices are consistent whether white or black.
            board.push(move)
            
        return boards
    
    def get_boards(self) -> list[list[chess.Board]]:
        """
        Retrieves a list of chess boards from all available PGN files, with one board per game state where it is the user's turn.

        Returns:
            A list of lists, where each inner list represents the chess boards extracted from a single PGN file (single game).
        """
        all_boards = []
        all_pgns = self.get_all_pgns()
        for pgn in all_pgns:
            if type(pgn) != str: # Sometimes, the Chess.com API gives a None value or float value for a game, so we need to skip it
                continue
            all_boards.append(self.pgn_to_boards(pgn))
        return all_boards
            
    def piece_to_int(self, piece: chess.Piece) -> int:
        """
        Converts a chess piece object to an integer representation.

        Args:
            piece (chess.Piece): The chess piece object to be converted.

        Returns:
            int: The integer representation of the chess piece.
            No piece: 0
            Pawn: 1
            Knight: 2
            Bishop: 3
            Rook: 4
            Queen: 5
            King: 6
        """
        piece_to_int = {
            None: 0,
            chess.PAWN: 1,
            chess.KNIGHT: 2,
            chess.BISHOP: 3,
            chess.ROOK: 4,
            chess.QUEEN: 5,
            chess.KING: 6
        }
        return piece_to_int[piece.piece_type]
    
    def get_matrix_game_states(self) -> list[list[np.ndarray]]:
        """
        Converts the board game states into matrices representing the positions of the chess pieces.

        Returns:
            A list of lists of numpy arrays, where each numpy array in the inner list represents a game state as a matrix, and each outer list is one game.
        """
        all_board_game_states = self.get_boards()
        
        all_matrices = []
        i = 0
        for game in all_board_game_states:
            game_matrices = []
            for board in game:
                matrix = np.zeros((8, 8), dtype=int)
                for square in range(64):
                    piece = board.piece_at(square)
                    if piece is None:
                        continue
                    row, col = square // 8, square % 8
                    value = self.piece_to_int(piece)
                    if piece.color == chess.BLACK: # Although this seems like it switches black pieces to negative, it is actually switching the perspective of the board so that the user's pieces are always positive.
                        value *= -1
                    matrix[7 - row][col] = value

                game_matrices.append(matrix)
            all_matrices.append(game_matrices)
        return all_matrices
    
    def find_moved_piece(self, board_state_1: np.ndarray, board_state_2: np.ndarray) -> tuple[int, int] | None:
        """
        Finds the moved piece between two board states.

        Args:
            board_state_1 (np.ndarray): The initial board state.
            board_state_2 (np.ndarray): The next board state.

        Returns:
            None if no piece was moved.
            tuple[int, int]: A tuple containing the square number (0 to 63) and the value of the piece that was moved.
            Pawn: 1
            Knight: 2
            Bishop: 3
            Rook: 4
            Queen: 5
            King: 6
        """
        flattened_board_state_1 = board_state_1.flatten()
        flattened_board_state_2 = board_state_2.flatten()
        
        exists_moved_piece = False
        
        for square_number, piece_in_square in enumerate(flattened_board_state_1):
            if piece_in_square != flattened_board_state_2[square_number] and piece_in_square > 0: # If the piece in the square is different between the two board states and the piece is positive (user's piece)
                moved_square_number = square_number
                moved_piece = piece_in_square
                exists_moved_piece = True
        if exists_moved_piece:
            return moved_square_number, moved_piece
        return None
    

    def board_to_8x8x12(self, game_state: np.ndarray) -> np.ndarray:
        """
        Convert an 8x8 board matrix to an 8x8x12 representation.

        The board matrix should use:
          0 for empty squares,
          1 for white pawn, 2 for white knight, 3 for white bishop, 
          4 for white rook, 5 for white queen, 6 for white king,
         -1 for black pawn, -2 for black knight, -3 for black bishop,
         -4 for black rook, -5 for black queen, -6 for black king.
     
        Returns:
            A NumPy array of shape (8, 8, 12) with binary indicators.
        """
        # Initialize the 8x8x12 array with zeros
        board_12 = np.zeros((8, 8, 12), dtype=np.int8)
    
        # Loop over each square in the 8x8 board
        for i in range(8):
            for j in range(8):
                piece = game_state[i, j]
                if piece == 0:
                    continue  # Skip empty squares
                # For white pieces (positive values), channel = piece value - 1 (0-indexed)
                if piece > 0:
                    channel = int(piece) - 1
                # For black pieces (negative values), channel = (abs(piece) - 1) + 6
                else:
                    channel = int(abs(piece)) - 1 + 6
                board_12[i, j, channel] = 1

        # Transpose from (8,8,12) to (12,8,8)
        board_12 = np.transpose(board_12, (2, 0, 1))
        return board_12

    
    def get_data(self) -> list[tuple[list[np.ndarray], int]]:
        data = []
        
        matrix_game_states = self.get_matrix_game_states()
        
        for individual_game_states in matrix_game_states: # individual_game_states are all matrix game states for a single game
            for move_number, game_state in enumerate(individual_game_states): 
                if move_number == len(individual_game_states) - 1:
                    break # If move_number is the last available game_state of the game, break the loop and move to next game
                board_state_1 = game_state
                board_state_2 = individual_game_states[move_number + 1]
                try:
                    moved_square_number, moved_piece = self.find_moved_piece(board_state_1=board_state_1, board_state_2=board_state_2)
                except TypeError:
                    continue
                game_state_12 = self.board_to_8x8x12(game_state)
                
                data.append((game_state_12, moved_square_number))
        return data
