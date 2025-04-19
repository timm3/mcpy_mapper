"""
This file seriously needs to be renamed, lmao

At time of writing, none of this is used.
I was exploring how logic and data might be organized differently.
"""

import pathlib


class World(object):
    """
    Either create object with just `directory` (and `save_path`?) argument and call `.inflate()`
    OR create object with all arguments provided.
    """

    def __init__(
        self,
        directory: pathlib.Path | None = None,
        name: str | None = None,
        save_path: pathlib.Path | None = None,  # note: is this even necessary?
        mc_nbt_version: str | None = None,
        mc_version: str | None = None,
        is_modded: bool | None = None,
        mods: list | None = None,
        modloader_name: str | None = None,
        modloader_version: str | None = None,
    ):
        if directory is not None and any(
            x is not None
            for x in (name, is_modded, mods, modloader_name, modloader_version)
        ):
            raise ValueError("invalid combination of arguments")
        if directory is None and not any(
            x is not None
            for x in (name, is_modded, mods, modloader_name, modloader_version)
        ):
            pass  # instead of raising exception, let's let this be valid for now
            # raise ValueError("invalid combination of arguments")

        self.directory = directory
        self.name = name
        self.save_path = (
            save_path  # directory / name  # <- that's what pycharm suggested
        )
        self.mc_nbt_version = mc_nbt_version
        self.mc_version = mc_version
        self.is_modded = is_modded
        self.mods = mods
        self.modloader_name = modloader_name
        self.modloader_version = modloader_version

    def inflate(self):
        """
        Will overwrite pretty much every attribute and property of the class.

        :return:
        """
        if not self.directory:
            raise TypeError("`directory` must be specified")
        if not self.directory.exists():
            raise FileNotFoundError(f"`directory` does not exist: {self.directory}")
        self.save_path = self._find_world_save_path()
        self._load_world_data()

    def _find_world_save_path(self):
        possible_level_filenames = ["level.dat", "level.nbt", "Level.dat", "Level.nbt"]
        for possible_filename in possible_level_filenames:
            if self.directory.joinpath(possible_filename).exists():
                return self.directory.joinpath(possible_filename)
        raise FileNotFoundError

    # def _load_world_data(self):
    #     level = get_loaded_level_java(save_path)
    #     data = extract_data(level)


class WorldLoader(object):
    directory: pathlib.Path
    save_path: pathlib.Path | None
    engine_info: dict | None
    mods: list

    def __init__(self, directory: pathlib.Path):
        self.directory = directory
        self.save_path = None
        self.engine_info = None
        self.mods = []

    def load(self):
        raise NotImplementedError()
