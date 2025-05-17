import argparse
import json
import os
import pathlib
import re
from typing import Any

import amulet_nbt
import mutf8  # type: ignore[import-untyped]

from .local_crawler import crawl_modloaders, crawl_mods
from .organize import make_bundle


WEIRD_VERSION_NUMBER_REGEX = re.compile(r"[@+%{].+[@+%}]")


def make_some_noise(data: dict):
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def save_data(data: dict, save_location: pathlib.Path):
    with open(save_location, "w+") as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)


def get_world_name(level: amulet_nbt.NamedTag) -> str:
    # TODO: convert the returned value from StringTag / IntTag object to str
    return level["Data"]["LevelName"]  # type: ignore[index]


def get_engine_info(level: amulet_nbt.NamedTag) -> dict[str, str | None]:
    # TODO: convert all the StringTag and IntTag objects in returned object to str/int as appropriate
    ret: dict[str, str | None] = {
        "mc_version": None,
        "mc_version_name": None,
        "mc_data_version": None,
        "mod_type": None,
        "mod_version": None,
        "mod_version_name": None,
        "mod_data_version": None,
        "mod_player_data_version": None,
    }
    if "forge" in level.keys():  # type: ignore[attr-defined]
        ret["mod_type"] = "forge"
        ret["mod_data_version"] = level["Data"]["ForgeDataVersion"]["minecraft"]  # type: ignore[index]
        ret["mod_player_data_version"] = level["Data"]["Player"]["ForgeDataVersion"][  # type: ignore[index]
            "minecraft"
        ]
        for mod in level["FML"]["ModList"]:  # type: ignore[index]
            if mod["ModId"] == "minecraft":
                ret["mc_version_name"] = mod["ModVersion"]
            if mod["ModId"] == "forge":
                ret["mod_version_name"] = mod["ModVersion"]
            if ret["mc_version_name"] and ret["mod_version_name"]:
                break
    # note: if "forge" not in keys, may need to look through fml mod list (FML.ModList or fml.LoadingModList)
    #   and find the 'forge' mod to get its version
    elif "fml" in level.keys():  # type: ignore[attr-defined]
        ret["mod_type"] = "forge"
        # note: I don't see anywhere to grab `mod_data_version` or `mod_player_data_version` when using
        #   world "modded createsparkycraft" as an example.
        for mod in level["fml"]["LoadingModList"]:  # type: ignore[index]
            if mod["ModId"] == "minecraft":
                ret["mc_version_name"] = mod["ModVersion"]
            if mod["ModId"] == "forge":
                ret["mod_version_name"] = mod["ModVersion"]
            if ret["mc_version_name"] and ret["mod_version_name"]:
                break
    else:
        # NOTE: this does not handle getting fabric versions yet
        # this works for "Apple Land" which is 1.16.4 but not for "existence.af15" which lacks a lot of other data points as well...
        try:
            ret["mc_version_name"] = level["Data"]["Version"]["Name"]  # type: ignore[index]
        except KeyError:
            print(
                f"could not find minecraft version name for level name: {level["Data"]["LevelName"]}"  # type: ignore[index]
            )

    ret["mc_version"] = level["Data"]["version"]  # type: ignore[index]
    try:
        ret["mc_data_version"] = level["Data"]["DataVersion"]  # type: ignore[index]
    except KeyError:
        # for some reason, a world called "AF15.Existence" or "existence.af15" doesn't have level.Data.DataVersion
        ret["mc_data_version"] = None
    return ret


def _check_for_weird_version(version: str) -> bool:
    return re.search(WEIRD_VERSION_NUMBER_REGEX, version) is not None


def get_forge_mod_list(
    level: amulet_nbt.NamedTag,
) -> list[Any] | list[dict[str, bool | Any]]:
    skippable = ["minecraft", "forge"]
    is_forge = False  # todo: do something with this :)

    forge_keys = ["FML", "fml"]
    for forge_key in forge_keys:
        try:
            level[forge_key]  # type: ignore[index]
            is_forge = True
            break  # found it! let's keep going
        except KeyError:
            pass
    mod_list_key = (
        "ModList"
        if forge_key == "FML"
        else "LoadingModList" if forge_key == "fml" else None
    )

    if not is_forge:
        # TODO: support fabric mods/engine -- might be able to check "modded either way" using "if len(keys) > 1" or "if more keys than just 'Data'"?
        return []

    return [
        {
            "name": _mod["ModId"].py_str,
            "version": _mod["ModVersion"].py_str,
            "version_is_weird": _check_for_weird_version(_mod["ModVersion"].py_str),
        }
        for _mod in level[forge_key].py_dict[mod_list_key].py_list  # type: ignore[index]
        if _mod["ModId"].py_str not in skippable
    ]


def extract_data(level: amulet_nbt.NamedTag) -> dict:
    return {
        "engine_info": get_engine_info(level),
        "world_name": get_world_name(level),
        "mod_list": get_forge_mod_list(level),
    }


def get_loaded_level_java(level_path: pathlib.Path):
    with open(level_path, "rb") as f:
        return amulet_nbt.load(
            f.read(),
            compressed=True,
            little_endian=False,
            string_decoder=mutf8.decode_modified_utf8,
        )


def get_loaded_level_bedrock(level_path: pathlib.Path):
    with open(level_path, "rb") as f:
        return amulet_nbt.load(
            f.read(),
            compressed=False,
            little_endian=True,
            string_decoder=amulet_nbt.utf8_escape_decoder,
        )


def get_world_save_filepath(world_dir: pathlib.Path) -> pathlib.Path:
    proposed_path = pathlib.Path(world_dir).joinpath("level.dat")
    if proposed_path.exists():
        return proposed_path
    else:
        # todo: remove this later -> I renamed some files to *.nbt so a PyCharm plugin would load them
        second_possible_path = world_dir.joinpath("level.nbt")
        if second_possible_path.exists():
            return second_possible_path
        else:
            raise FileNotFoundError


def get_world_save_filepath_v2(world_dir: pathlib.Path) -> pathlib.Path:
    possible_level_filenames = ["level.dat", "level.nbt", "Level.dat", "Level.nbt"]
    for possible_filename in possible_level_filenames:
        if world_dir.joinpath(possible_filename).exists():
            return world_dir.joinpath(possible_filename)
    raise FileNotFoundError


def load_world(world_directory: pathlib.Path) -> dict | None:
    try:
        # save_path = get_world_save_filepath(world_directory)
        save_path = get_world_save_filepath_v2(world_directory)
    except FileNotFoundError:
        # could not find world to extract
        return None
    level = get_loaded_level_java(save_path)
    data = extract_data(level)

    try:
        print(f"{data["world_name"]} || {data["engine_info"]["mc_version_name"]}")
    except KeyError:
        pass

    return data


def _change_world_arg_to_pathlib_path(world_path: str) -> pathlib.Path:
    path = pathlib.Path(world_path)
    if path.exists():
        return path
    else:
        raise ValueError(f"world path does not exist - {world_path}")


def _change_many_worlds_arg_to_pathlib_path(worlds_path: str) -> pathlib.Path:
    path = pathlib.Path(worlds_path)
    if path.exists():
        if path.is_dir():
            return path
        else:
            raise ValueError(f"worlds directory must be a directory - {worlds_path}")
    else:
        raise ValueError(f"worlds directory does not exist - {worlds_path}")


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    world_group = parser.add_mutually_exclusive_group(required=True)
    world_group.add_argument(
        "-w",
        "--world-directory",
        type=_change_world_arg_to_pathlib_path,
        help="Directory where single world is stored.",
    )
    world_group.add_argument(
        "-m",
        "--many-worlds",
        type=_change_many_worlds_arg_to_pathlib_path,
        help="Directory where one or more world directories are stored.",
    )

    parser.add_argument(
        "-s",
        "--save",
        type=_change_many_worlds_arg_to_pathlib_path,
        help=(
            "Directory to store extracted world data. "
            "Optional. If not provided, data will be printed to console. "
            "If provided, file will be created (or overwritten) using world's directory's name "
            "inside the --save directory."
        ),
    )

    parser.add_argument(
        "--mods-directory",
        type=_change_many_worlds_arg_to_pathlib_path,
        help="Directory to recursively crawl to discover mods. Optional.",
    )

    parser.add_argument(
        "--loaders-directory",
        type=_change_many_worlds_arg_to_pathlib_path,
        help="Directory to recursively crawl to discover modloaders. Optional.",
    )

    parser.add_argument(
        "--bundles-directory",
        type=_change_many_worlds_arg_to_pathlib_path,
        help=(
            "Directory where bundle directories will be stored. "
            "Optional. If not provided, bundle will not be created. "
            "If provided, directories and files will be created (or overwritten) using world's directory's name "
            "inside the --bundle-directory. These files will include notes about which mods and modloaders "
            "are included and which aren't."
        ),
    )
    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    if args.world_directory is not None:
        world_directories = [args.world_directory]
    elif args.many_worlds is not None:
        for dirpath, dirnames, filenames in os.walk(args.many_worlds):
            world_directories = [
                pathlib.Path(dirpath).joinpath(dir_name) for dir_name in dirnames
            ]
            break  # only want to work with first iteration

    known_mods = []
    if args.mods_directory:
        known_mods = crawl_mods(args.mods_directory)

    modloaders = []
    if args.loaders_directory:
        modloaders = crawl_modloaders(args.loaders_directory)

    for world_dir in world_directories:
        data = load_world(world_dir)
        if data is None:
            print(f"could not find level to extract in - {world_dir}")
            continue
        if args.save:
            save_data(data, args.save.joinpath(world_dir.name + ".json"))
        else:
            make_some_noise(data)
        if args.bundles_directory:
            make_bundle(
                world_data=data,
                known_mods=known_mods,
                known_modloaders=modloaders,
                bundles_directory=args.bundles_directory,
                bundle_name=world_dir.name,  # note: could also try `str(data["world_name"])` or some such
            )


if __name__ == "__main__":
    main()
