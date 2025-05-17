import pathlib
import shutil

from packaging.version import (
    Version,
    Infinity,
    NegativeInfinity,
)  # it really bothers me that I can't use the top-level namespace

from . import local_crawler


def _get_higher_lower_bound(version1: str | None, version2: str | None) -> str | None:
    """
    Assumes semantic versioning.
    """
    if version1 is None:
        return version2
    if version2 is None:
        return version1

    v1 = Version(version1.strip())
    v2 = Version(version2.strip())
    if v1 < v2:
        return version2.strip()
    if v1 > v2:
        return version1.strip()
    if len(version1) > len(version2):
        return version1.strip()
    return version2.strip()


def _get_lower_upper_bound(version1: str | None, version2: str | None) -> str | None:
    """
    Assumes semantic versioning.
    """
    if version1 is None:
        return version2
    if version2 is None:
        return version1

    v1 = Version(version1.strip())
    v2 = Version(version2.strip())

    if v1 < v2:
        return version1.strip()
    if v1 > v2:
        return version2.strip()
    return version1.strip()


def find_mod(
    desired_mod: dict,
    known_mods: list[local_crawler.Mod],
) -> local_crawler.Mod | None:
    for mod in known_mods:
        if (
            (desired_mod["name"].lower() == mod.name.lower())
            or (desired_mod["name"].lower() in [_.lower() for _ in mod.possible_names])
        ) and (desired_mod["version"] in mod.possible_mod_versions):
            return mod


def _is_dependency_already_listed(mod_list: list[dict], dependency: dict) -> bool:
    mod_id = dependency["modId"]

    if dependency["versionRange"]["minimum"]:
        minimum_version = Version(dependency["versionRange"]["minimum"])
    else:
        minimum_version = NegativeInfinity

    if dependency["versionRange"]["maximum"]:
        maximum_version = Version(dependency["versionRange"]["maximum"])
    else:
        maximum_version = Infinity

    for mod in mod_list:
        if mod["name"] == mod_id:
            mod_version = Version(mod["version"])
            if (mod_version >= minimum_version) and (mod_version <= maximum_version):
                return True
    return False


def locate_mods(
    mod_list: list[dict],
    known_mods: list[local_crawler.Mod],
) -> tuple[list[local_crawler.Mod], list[dict]]:
    not_mods = ["forge", "minecraft"]
    available_mods = []
    unavailable_mods = []
    dependencies = []
    for base_mod in mod_list:
        mod = find_mod(base_mod, known_mods)
        if mod is not None:
            available_mods.append(mod)
            mod_dependencies = [
                data
                for name, data in mod.dependencies.items()
                if name not in not_mods
                and not _is_dependency_already_listed(mod_list, data)
            ]
            dependencies.extend(mod_dependencies)
        else:
            # todo: eventually support grabbing mods from network / nexusmods
            unavailable_mods.append(base_mod)
    for dependency in dependencies:
        dep_mod = find_mod(dependency, known_mods)
        if dep_mod is not None:
            available_mods.append(dep_mod)
        else:
            unavailable_mods.append(dependency)
    return available_mods, unavailable_mods


def ensure_bundle_directory(
    bundles_directory: pathlib.Path,
    bundle_name: str,  # todo: or should this just be the name of the world or something?
    rewrite_existing: bool = False,
) -> pathlib.Path:
    bundles_directory.mkdir(
        parents=True, exist_ok=True
    )  # todo: should the `mode` be specified?
    bundle_dir = bundles_directory / bundle_name
    if bundle_dir.exists() and not rewrite_existing:
        raise IsADirectoryError(f"bundle directory already exists -- {bundle_dir}")
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return bundle_dir


def add_mods(
    bundle_dir: pathlib.Path,
    available_mods: list[local_crawler.Mod],
) -> None:
    mods_dir = bundle_dir.joinpath("mods")
    mods_dir.mkdir(parents=True, exist_ok=True)

    for mod in available_mods:
        shutil.copy(mod.path, mods_dir)


def pick_modloader(
    engine_info: dict,
    known_modloaders: list[local_crawler.ModLoader],
) -> local_crawler.ModLoader:
    for loader in known_modloaders:
        if (engine_info["mod_type"] == loader.family) and (
            engine_info["mod_version_name"] == loader.version
        ):
            return loader
    # couldn't find it, so recommend one
    return local_crawler.ModLoader(
        name=engine_info["mod_type"],
        family="",
        version=engine_info["mod_version_name"],
        base_mc_version=engine_info["mc_version_name"],
        path=None,
    )


def add_modloader(
    bundle_dir: pathlib.Path,
    engine_info: dict,
    known_modloaders: list[local_crawler.ModLoader],
) -> local_crawler.ModLoader:
    modloader = pick_modloader(engine_info, known_modloaders)
    if modloader.path:
        shutil.copy(modloader.path, bundle_dir)
    return modloader


def add_notes(
    bundle_dir: pathlib.Path,
    world_name: str,
    available_mods: list[local_crawler.Mod],
    unavailable_mods: list[dict],
    loader_added: local_crawler.ModLoader,
) -> None:
    with open(bundle_dir / "notes.txt", "w+") as notes_file:
        notes_file.write(f"world: {world_name}\n")
        if loader_added.path:
            notes_file.write(f"loader added: {loader_added}\n")
        else:
            notes_file.write(f"loader needed: {loader_added}\n")
        notes_file.write("mods_missing:\n")
        for missing in unavailable_mods:
            notes_file.write(f"- {missing}\n")
        notes_file.write("mods_included:\n")
        for included in available_mods:
            notes_file.write(f"- {included}\n")


def make_bundle(
    world_data: dict,
    known_mods: list[local_crawler.Mod],
    known_modloaders: list[local_crawler.ModLoader],
    bundles_directory: pathlib.Path,
    bundle_name: str,  # todo: or should this just be the name of the world or something?
) -> pathlib.Path | None:
    bundle_dir = ensure_bundle_directory(
        bundles_directory, bundle_name, rewrite_existing=True
    )

    available_mods, unavailable_mods = locate_mods(world_data["mod_list"], known_mods)
    add_mods(bundle_dir, available_mods)

    loader_added = add_modloader(
        bundle_dir, world_data["engine_info"], known_modloaders
    )

    add_notes(
        bundle_dir,
        world_data["world_name"],
        available_mods,
        unavailable_mods,
        loader_added,
    )

    return bundle_dir
