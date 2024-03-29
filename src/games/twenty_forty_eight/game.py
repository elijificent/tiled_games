# pylint: disable=too-few-public-methods
"""
A generalized game of "2048", a tiled game where the purpose
is to merge tiles of the same value together, while avoiding
filling the board. 

Original: https://play2048.co/
"""

import json
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import numpy as np

from src.tiled_tools.common.custom_typing import AnyNumber, is_numeric
from src.tiled_tools.common.grid import Grid


# pylint: disable=too-many-instance-attributes
@dataclass
class GameConfig:
    """
    Game config options for a game of 2048
    """

    grid_size: int = 4
    spawn_tile_count: int = 2
    starting_tile_count: int = 2
    win_tile_value: int = 2**11
    # Probability of a new tile being a 4 instead of a 2
    mutation_probability: float = 0.1
    # Whether to mutatation chance can occur at the start of the game
    mutation_at_start: bool = True
    # Whether to kill the game if a tile is spawned that cannot be placed
    spawn_kill: bool = False
    root_tile_value: int = 2

    def to_json(self) -> str:
        """
        Converts the config to a json string
        """
        return json.dumps(
            {
                "grid_size": self.grid_size,
                "spawn_tile_count": self.spawn_tile_count,
                "starting_tile_count": self.starting_tile_count,
                "win_tile_value": self.win_tile_value,
                "mutation_probability": self.mutation_probability,
                "mutation_at_start": self.mutation_at_start,
                "spawn_kill": self.spawn_kill,
                "root_tile_value": self.root_tile_value,
            }
        )

    def __repr__(self) -> str:
        return (
            f"Game(grid_size={self.grid_size}, "
            f"spawn_tile_count={self.spawn_tile_count}, "
            f"starting_tile_count={self.starting_tile_count}, "
            f"win_tile_value={self.win_tile_value}, "
            f"mutation_probability={self.mutation_probability}, "
            f"mutation_at_start={self.mutation_at_start}, "
            f"spawn_kill={self.spawn_kill}, "
            f"root_tile_value={self.root_tile_value})"
        )

    def __str__(self) -> str:
        return self.__repr__()


class SlideDirection(Enum):
    """
    Which direction to slide the tiles
    """

    NONE = 0
    UP = 1
    RIGHT = 2
    DOWN = 3
    LEFT = 4


class Tile:
    """
    A single tile and data

    Args:
        value: Value of the tile, if None, the tile is empty
        momentum: The direction the tile is moving, resprented as (c, r)
    """

    def __init__(self, value: int, momentum: SlideDirection = SlideDirection.NONE):
        """
        Create a new tile with a value and momentum
        """
        self.value = value
        self.momentum = momentum

    def __eq__(self, other: "Tile"):
        if isinstance(other, Tile):
            return self.value == other.value

        if is_numeric(other):
            return self.value == other

        return False

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return self.__repr__()


class TileHelper:
    """
    Methods useful for working with tiles
    """

    @staticmethod
    def build_grid_with_value(value: int, size: int) -> Grid:
        """
        Builds a grid of tiles with a given value

        Args:
            value: The value of the tiles
            size: The size of the grid

        Returns:
            Grid: A grid of tiles with the given value
        """
        tiles = [
            [Tile(value=value, momentum=SlideDirection.NONE) for _i in range(size)]
            for _j in range(size)
        ]
        return Grid(tiles)


class SlideResult(Enum):
    """
    The reason for a game failure
    """

    NORMAL = 1
    # The board is full after a slide
    BOARD_FULL = 2
    # A tile was spawned that could not be placed,
    # only occurs if config.spawn_kill is True
    SPAWN_KILL = 3
    # Spawn "fill", where is full after a spawn
    SPAWN_FILL = 4


class ArrayHelper:
    """
    Useful class for working with arrays
    """

    @staticmethod
    def first_non_zero_index(array: list[AnyNumber], start_index: int = 0) -> int:
        """
        Returns the index of the first non-zero element in an array
        """
        for i in range(start_index, len(array)):
            if array[i] != 0:
                return i
        return -1

    @staticmethod
    def first_zero_index(array: list[AnyNumber], start_index: int = 0) -> int:
        """
        Returns the index of the first zero element in an array
        """
        for i in range(start_index, len(array)):
            if array[i] == 0:
                return i
        return -1

    @staticmethod
    def transpose_columns(array: list[list[any]]) -> list[list[AnyNumber]]:
        """
        Transposes the columns of a 2D array
        """
        return [list(row) for row in zip(*array)]


class PlayBlocker(Enum):
    """
    Reasons why a game cannot be played
    """

    NONE = 0
    # The board is full
    BOARD_FULL = 1
    # No tiles can be merged
    NO_MERGE = 2


class Game:
    """
    All the logic and state for a game of 2048
    """

    def __init__(self, config: GameConfig = GameConfig()):
        self.config = config
        # Whether the game is in the initial spawn mode
        self.init_mode = True

        self.grid = TileHelper.build_grid_with_value(0, self.config.grid_size)
        self.score = 0

        # Useful for UIs, as they get richer information on what happened during a slide
        self.movement_matrix = [
            [0 for _i in range(self.config.grid_size)]
            for _j in range(self.config.grid_size)
        ]
        self.latest_spawn_result: Optional[SlideResult] = None
        self.latest_spawn_locations: list[tuple[int, int]] = []

        self.initial_spawn()

    def set_tiles(self, new_list: list[list[Tile]]):
        """
        Set the grid of the game
        """
        for r in range(self.config.grid_size):
            for c in range(self.config.grid_size):
                self.grid.set(c, r, new_list[r][c])

    def initial_spawn(self):
        """
        Spawn in the initial tiles and remove game from init mode
        """
        spawn_locations = []
        for _i in range(self.config.starting_tile_count):
            spawn_locations.append(self._spawn_new_tile())

        self.init_mode = False
        self.latest_spawn_locations = spawn_locations

    def play_turn(self, direction: SlideDirection) -> SlideResult:
        """
        Play a turn of the game, returning the result of the turn
        """
        self.slide_tiles(direction)

        # I don't think this is possible without ending the game
        if self.board_full():
            return SlideResult.BOARD_FULL

        spawn_result = self.spawn_new_tiles()
        self.latest_spawn_result = spawn_result
        if not spawn_result:
            if self.config.spawn_kill:
                return SlideResult.SPAWN_KILL

            return SlideResult.SPAWN_FILL

        return SlideResult.NORMAL

    def can_play(self) -> bool:
        """
        Returns whether the game can be played
        """

        # If any tile has a neighbor with the same value, the game can be played
        for r in range(self.config.grid_size):
            for c in range(self.config.grid_size):
                tile = self.grid.get(c, r)
                if tile.value == 0:
                    return True

                neighbors = self.grid.get_adjacent(c, r)
                for neighbor in neighbors:
                    if neighbor.value == tile.value:
                        return True
        return False

    def slide_tiles(self, direction: SlideDirection):
        """
        Slide all the tiles in a given direction

        Args:
            direction: The direction to slide the tiles
        """
        if direction in [SlideDirection.UP, SlideDirection.DOWN]:
            new_grid_values, movement_matrix = self.slide_each_column(direction)
        else:
            new_grid_values, movement_matrix = self.slide_each_row(direction)

        new_tiles = [[Tile(value) for value in row] for row in new_grid_values]
        self.set_tiles(new_tiles)
        self.movement_matrix = movement_matrix

        return movement_matrix

    def slide_each_column(
        self, direction: SlideDirection
    ) -> tuple[list[list[Any]], list[list[Any]]]:
        """
        Slide each column in the given direction.

        Args:
            direction: The direction to slide the columns, either up or down
        """

        new_grid_values = []
        movement_matrix = []

        for c in range(self.config.grid_size):
            column = [tile.value for tile in self.grid.get_col(c)]
            new_column, movement = self._slide_helper(direction, column)
            new_grid_values.append(new_column)
            movement_matrix.append(movement)

        new_grid_values = ArrayHelper.transpose_columns(new_grid_values)
        movement_matrix = ArrayHelper.transpose_columns(movement_matrix)

        return new_grid_values, movement_matrix

    def slide_each_row(
        self, direction: SlideDirection
    ) -> tuple[list[list[Any]], list[list[Any]]]:
        """
        Slide each row in the given direction.

        Args:
            direction: The direction to slide the rows, either left or right
        """

        new_grid_values = []
        movement_matrix = []

        for r in range(self.config.grid_size):
            row = [tile.value for tile in self.grid.get_row(r)]
            new_row, movement = self._slide_helper(direction, row)
            new_grid_values.append(new_row)
            movement_matrix.append(movement)

        return new_grid_values, movement_matrix

    def _slide_helper(
        self, direction: SlideDirection, row_o_col: list[AnyNumber]
    ) -> tuple[list[AnyNumber], list[AnyNumber]]:
        """
        Slide a single row or column in a given direction

        Args:
            direction: The direction to slide the row/column
            row_o_col: The row or column to slide
        """
        l_copy = list(row_o_col)

        # Reverse the list if sliding down or right
        if direction in [SlideDirection.DOWN, SlideDirection.RIGHT]:
            l_copy = l_copy[::-1]

        new_list = [0 for _ in l_copy]
        movement = [0 for _ in l_copy]

        new_index = 0
        start_index = ArrayHelper.first_non_zero_index(l_copy)
        for i in range(start_index, len(l_copy)):
            if l_copy[i] == 0:
                continue

            if l_copy[i] == new_list[new_index]:
                new_list[new_index] *= self.config.root_tile_value
                movement[i] = new_index - i
                new_index += 1
                self.score += l_copy[i] * self.config.root_tile_value
            else:
                if new_list[new_index] == 0:
                    new_list[new_index] = l_copy[i]
                    movement[i] = new_index - i
                else:
                    new_list[new_index + 1] = l_copy[i]
                    movement[i] = new_index + 1 - i
                    new_index += 1

        if direction in [SlideDirection.DOWN, SlideDirection.RIGHT]:
            new_list = new_list[::-1]
            movement = [-offset for offset in movement[::-1]]

        return new_list, movement

    def spawn_new_tiles(self) -> bool:
        """
        Spawns in new tiles on the board after successful slide. Returns
        true if all tiles could be placed, false otherwise
        """
        spawned_all = True
        self.latest_spawn_locations = []
        for _i in range(self.config.spawn_tile_count):
            new_location = self._spawn_new_tile()

            if not new_location:
                return False

            self.latest_spawn_locations.append(new_location)

        return spawned_all

    def board_full(self):
        """
        Checks if the board is full
        """

        for r in range(self.config.grid_size):
            for c in range(self.config.grid_size):
                # 0 is empty
                if self.grid.get(c, r).value == 0:
                    return False

        return True

    def get_empty_tiles(self) -> list[tuple[int, int]]:
        """
        Returns a list of empty tiles
        """
        empty_tiles = []
        for r in range(self.config.grid_size):
            for c in range(self.config.grid_size):
                if self.grid.get(c, r).value == 0:
                    empty_tiles.append((c, r))
        return empty_tiles

    def get_highest_tile(self) -> int:
        """
        Returns the value of the highest tile on the board
        """
        highest_tile = 0
        for r in range(self.config.grid_size):
            for c in range(self.config.grid_size):
                tile = self.grid.get(c, r)
                if tile.value > highest_tile:
                    highest_tile = tile.value
        return highest_tile

    def _spawn_new_tile(self) -> Optional[tuple[int, int]]:
        """
        Returns the position of the new tile if config allows it.

        Returns:
            Optional[tuple[int, int]]: The position of the new tile. None if the new tile
                could not be placed
        """
        new_tile = self._get_new_tile()
        new_tile_pos = self._get_random_empty_tile()

        if new_tile_pos is None:
            return None

        self.grid.set(new_tile_pos[0], new_tile_pos[1], new_tile)
        return new_tile_pos

    def _get_new_tile(self) -> Tile:
        """
        Returns a new tile with a value based on the config
        """
        new_tile_value = self._get_new_tile_value()
        return Tile(value=new_tile_value)

    def _get_random_empty_tile(self) -> Optional[tuple[int, int]]:
        """
        Returns a random empty tile. If there are no empty tiles, returns None
        """
        empty_tiles = self.get_empty_tiles()
        tiles_len = len(empty_tiles)

        if empty_tiles:
            random_index = random.randint(0, tiles_len - 1)
            return empty_tiles[random_index]
        return None

    def _get_new_tile_value(self) -> AnyNumber:
        """
        Returns the value of the new tile, either the root tile value or
        its square, depending on the mutation probability
        """
        root_tile_value = self.config.root_tile_value
        should_mutate = np.random.rand() < self.config.mutation_probability
        mutated_value = root_tile_value * root_tile_value

        if self.init_mode:
            if self.config.mutation_at_start and should_mutate:
                return mutated_value

            return root_tile_value

        return root_tile_value if not should_mutate else mutated_value

    def to_json(self) -> str:
        """
        Converts the game to a json string
        """
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the game to a dict
        """
        return {
            "config": self.config.__dict__,
            "grid": [[tile.value for tile in row] for row in self.grid.tolist()],
            "score": self.score,
            "movement_matrix": self.movement_matrix,
            "latest_spawn_result": self.latest_spawn_result,
            "latest_spawn_locations": self.latest_spawn_locations,
        }

    def __repr__(self) -> str:
        tile_matrix = self.grid.tolist()
        tile_matrix = [[str(tile) for tile in row] for row in tile_matrix]
        return "\n".join([" ".join(row) for row in tile_matrix])

    def __str__(self) -> str:
        return self.__repr__()


class GameHelper:
    """
    Methods for working with games
    """

    @staticmethod
    def load(json_string: str) -> Game:
        """
        Load a game from the given json strong
        """
        game_dict = json.loads(json_string)
        config = GameConfig(**game_dict["config"])
        game = Game(config=config)
        game.set_tiles(
            [[Tile(value=value) for value in row] for row in game_dict["grid"]]
        )
        game.score = game_dict["score"]
        game.movement_matrix = game_dict["movement_matrix"]
        game.latest_spawn_result = game_dict["latest_spawn_result"]
        game.latest_spawn_locations = game_dict["latest_spawn_locations"]

        return game
