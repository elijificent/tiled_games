# pylint: disable=missing-docstring,line-too-long

import unittest

from src.games.twenty_forty_eight.game import (
    Game,
    GameConfig,
    GameHelper,
    SlideDirection,
    SlideResult,
    Tile,
)
from src.tiled_tools.common.grid import Grid


class TestGameConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GameConfig()

    def test_str(self):
        self.assertEqual(
            str(self.config),
            "Game(grid_size=4, spawn_tile_count=2, starting_tile_count=2, win_tile_value=2048, mutation_probability=0.1, mutation_at_start=True, spawn_kill=False, root_tile_value=2)",
        )


class Test2048(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        full_config = GameConfig(starting_tile_count=16)
        self.full = Game(config=full_config)

    def test_init_with_default(self):
        self.assertEqual(self.game.config.grid_size, 4)
        self.assertEqual(self.game.config.starting_tile_count, 2)
        self.assertEqual(self.game.config.spawn_kill, False)

    def test_init_with_custom(self):
        config = GameConfig(grid_size=5, starting_tile_count=3, spawn_kill=True)
        game = Game(config=config)

        self.assertEqual(game.config.grid_size, 5)
        self.assertEqual(game.config.starting_tile_count, 3)
        self.assertEqual(game.config.spawn_kill, True)

    def test_board_full(self):
        self.assertFalse(self.game.board_full())

        # Fill the board
        for i in range(self.game.config.grid_size):
            for j in range(self.game.config.grid_size):
                self.game.grid.get(i, j).value = 2

        self.assertTrue(self.game.board_full())

        self.assertTrue(self.full.board_full())

    def test_spawn_new_tiles(self):
        non_empty_tiles = 0
        for i in range(self.game.config.grid_size):
            for j in range(self.game.config.grid_size):
                if self.game.grid.get(i, j).value != 0:
                    non_empty_tiles += 1

        self.assertEqual(non_empty_tiles, self.game.config.starting_tile_count)

        new_game = Game(GameConfig(starting_tile_count=4))

        for i in range(3):
            new_game.spawn_new_tiles()

        non_empty_tiles = 0
        for i in range(new_game.config.grid_size):
            for j in range(new_game.config.grid_size):
                if new_game.grid.get(i, j).value != 0:
                    non_empty_tiles += 1

        # 4 + 2 * 3
        self.assertEqual(non_empty_tiles, 10)

        for _ in range(5):
            self.full.spawn_new_tiles()

        self.assertTrue(self.full.board_full())

    def test_str(self):
        str_repr = str(self.game)
        lengths = [len(line) for line in str_repr.split("\n")]
        self.assertEqual(len(set(lengths)), 1)
        self.assertEqual(lengths[0], 7)  # 4 chars + 3 spaces


class TestGameOperations(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        # Disabling formating so grid is easier to read/follow
        # fmt: off
        self.full_tile_vals = [
            [1, 2, 3, 4],
            [8, 7, 6, 5],
            [9, 10, 11, 12],
            [16, 15, 14, 13],
        ]
        self.full_tile_list = [[Tile(val) for val in row] for row in self.full_tile_vals]
        self.power_vals = [
            [2, 2, 2, 2],
            [0, 0, 0, 0],
            [0, 0, 4, 0],
            [2, 2, 0, 2]
        ]
        self.power_list = [[Tile(val) for val in row] for row in self.power_vals]
        # fmt: on

    def test_get_high_tile(self):
        self.game.set_tiles(self.full_tile_list)
        self.assertEqual(self.game.get_highest_tile(), 16)

        self.game.set_tiles(self.power_list)
        self.assertEqual(self.game.get_highest_tile(), 4)

    def test_can_play(self):
        self.game.set_tiles(self.full_tile_list)
        self.assertFalse(self.game.can_play())

        self.game.set_tiles(self.power_list)
        self.assertTrue(self.game.can_play())

        all_twos = [[Tile(2) for _ in range(4)] for _ in range(4)]
        self.game.set_tiles(all_twos)
        self.assertTrue(self.game.can_play())

    def test_set_tiles(self):
        tile_list = [[Tile(val) for val in row] for row in self.full_tile_vals]
        self.assertNotEqual(self.game.grid.tolist(), tile_list)

        self.game.set_tiles(tile_list)
        self.assertEqual(self.game.grid.tolist(), tile_list)

        self.game.grid.set(0, 0, Tile(-10))

        self.assertNotEqual(self.game.grid.tolist(), tile_list)

    def test_slide_all_directions(self):
        game = Game()
        game.set_tiles(self.power_list)

        game.slide_tiles(SlideDirection.UP)
        expected = [
            [4, 4, 2, 4],
            [0, 0, 4, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        expected_movement = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, -1, 0],
            [-3, -3, 0, -3],
        ]
        expected_tiled = [[Tile(val) for val in row] for row in expected]
        self.assertListEqual(game.movement_matrix, expected_movement)
        self.assertEqual(game.grid, Grid(expected))

        game = Game()
        game.set_tiles(self.power_list)
        game.slide_tiles(SlideDirection.DOWN)
        expected = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 2, 0],
            [4, 4, 4, 4],
        ]
        expected_movement = [
            [3, 3, 2, 3],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0],
        ]
        expected_tiled = [[Tile(val) for val in row] for row in expected]
        self.assertListEqual(game.movement_matrix, expected_movement)
        self.assertEqual(game.grid, Grid(expected_tiled))

        game = Game()
        game.set_tiles(self.power_list)
        game.slide_tiles(SlideDirection.RIGHT)
        expected = [
            [0, 0, 4, 4],
            [0, 0, 0, 0],
            [0, 0, 0, 4],
            [0, 0, 2, 4],
        ]
        expected_movement = [
            [2, 1, 1, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [2, 2, 0, 0],
        ]
        expected_tiled = [[Tile(val) for val in row] for row in expected]
        self.assertListEqual(game.movement_matrix, expected_movement)
        self.assertEqual(game.grid, Grid(expected_tiled))

        game = Game()
        game.set_tiles(self.power_list)
        game.slide_tiles(SlideDirection.LEFT)
        expected = [
            [4, 4, 0, 0],
            [0, 0, 0, 0],
            [4, 0, 0, 0],
            [4, 2, 0, 0],
        ]
        expected_movement = [
            [0, -1, -1, -2],
            [0, 0, 0, 0],
            [0, 0, -2, 0],
            [0, -1, 0, -2],
        ]
        expected_tiled = [[Tile(val) for val in row] for row in expected]
        self.assertEqual(game.grid, Grid(expected_tiled))
        self.assertListEqual(game.movement_matrix, expected_movement)

        game = Game()
        game.set_tiles(self.full_tile_list)

        game.slide_tiles(SlideDirection.LEFT)
        self.assertEqual(game.grid, Grid(self.full_tile_list))

        game.slide_tiles(SlideDirection.RIGHT)
        self.assertEqual(game.grid, Grid(self.full_tile_list))

        game.slide_tiles(SlideDirection.UP)
        self.assertEqual(game.grid, Grid(self.full_tile_list))

        game.slide_tiles(SlideDirection.DOWN)
        self.assertEqual(game.grid, Grid(self.full_tile_list))

    def test_double_slide(self):
        game = Game()
        game.set_tiles(self.power_list)

        game.slide_tiles(SlideDirection.UP)
        game.slide_tiles(SlideDirection.RIGHT)
        expected = [
            [0, 8, 2, 4],
            [0, 0, 0, 4],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        expected_movement = [
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        expected_tiled = [[Tile(val) for val in row] for row in expected]
        self.assertEqual(game.grid, Grid(expected_tiled))
        self.assertListEqual(game.movement_matrix, expected_movement)

    def test_play_turn(self):
        result = self.game.play_turn(SlideDirection.UP)
        self.assertEqual(result, SlideResult.NORMAL)

        self.assertTrue(self.game.latest_spawn_locations)
        self.assertTrue(self.game.latest_spawn_result)


class TestTile(unittest.TestCase):
    def setUp(self):
        self.tile = Tile(2)

    def test_str(self):
        self.assertEqual(str(self.tile), "2")

    def test_eq(self):
        self.assertEqual(self.tile, Tile(2))
        self.assertEqual(self.tile, 2)
        self.assertNotEqual(self.tile, Tile(4))
        self.assertNotEqual(self.tile, "2")


class TestSaveAndLoad(unittest.TestCase):
    def setUp(self):
        self.config = GameConfig(grid_size=5, spawn_kill=True)
        self.game = Game(self.config)
        self.game_vals = [
            [0, 2, 4, 0, 16],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 8],
            [8, 0, 0, 0, 0],
            [0, 0, 0, 0, 2],
        ]
        self.game_tiles = [[Tile(val) for val in row] for row in self.game_vals]
        self.game.set_tiles(self.game_tiles)

    def test_save_and_load(self):
        save_string = self.game.to_json()
        loaded_game = GameHelper.load(save_string)

        self.assertEqual(loaded_game.grid, Grid(self.game_tiles))
        self.assertEqual(loaded_game.to_json(), save_string)
