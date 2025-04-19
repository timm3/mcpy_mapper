"""
Crawl through local files to better understand them.
"""

import io
import os
import pathlib
import zipfile
from dataclasses import dataclass

import tomllib


@dataclass
class Mod:
    name: str | None
    full_name: str | None
    path: pathlib.Path | None
    modloader_type: str | None
    modloader_version_range: (
        dict | None
    )  # {"minimum": str, "maximum": str} -- values are "inclusive"
    dependencies: list  # list[Mod]  -- needed to make bundles "complete"
    possible_mc_versions: list[str]
    possible_mod_versions: list[str]
    mod_version_range: (
        dict | None
    )  # {"minimum": str, "maximum": str} -- used only when Mod is a dependency-Mod


def crawl(directory: pathlib.Path) -> list[Mod]:
    """
    Walks `directory` and subdirectories looking for and categorizing mods.
    # All directories with "mods" in the name (case-insensitive) will be expected to have mods inside them.
    # This is to account for scenario where you've several mod directories for several different modloaders or minecraft versions.
    # If directory does not have "mods" in the name, it is assumed to be a mod.
    """
    ret = []
    for dir_str, dirnames, filenames in os.walk(directory, followlinks=True):
        dirpath = pathlib.Path(dir_str)

        # add local jar files
        for filename in filenames:
            if filename.endswith(".jar"):
                ret.append(inspect_jar(pathlib.Path(dirpath, filename)))

        # process other directories
        for dirname in dirnames:
            ret.extend(crawl(pathlib.Path(dirpath, dirname)))

    return ret


def _inspect_manifest(manifest: str) -> dict:
    data: dict[str, str | None] = {"mod_version": None}
    for line in manifest.splitlines():
        if line.startswith("Implementation-Version"):
            data["mod_version"] = line.split(":")[1].strip()
    return data


def get_version_range(version_range: str) -> dict[str, str | None]:
    sans_bounds_indicators = version_range.strip("[])( ")
    bounds = sans_bounds_indicators.split(",")
    if len(bounds) != 2:
        raise ValueError(
            "`version_range` must contain one comma to separate minimum and maximum versions like '[44,45.0.0)'"
        )
    return {
        "minimum": bounds[0].strip() or None,
        "maximum": bounds[1].strip() or None,
    }


def _inspect_mods_toml(_toml: dict) -> list[dict]:
    basic_info: dict[str, dict | list | str | None] = {
        "modloader_type": _toml["modLoader"],
        "modloader_version_range": get_version_range(_toml["loaderVersion"]),
        "possible_mc_versions": list(),
    }
    mods = []
    for mod in _toml["mods"]:
        ret = {
            "name": mod["modId"],
        }
        ret.update(basic_info)
        ret["possible_mod_versions"] = [mod["version"]]
        ret["full_name"] = mod["displayName"]

        ret["dependencies"] = {}
        for dependency in _toml["dependencies"].get(mod["modId"], []):
            ret["dependencies"][dependency["modId"]] = dependency
            ret["dependencies"][dependency["modId"]]["versionRange"] = (
                get_version_range(dependency["versionRange"])
            )
        mods.append(ret)
    return mods


def inspect_jar(filepath: pathlib.Path) -> Mod:
    name = filepath.name  # TODO: actually populate this correctly
    full_name = filepath.name  # TODO: actually populate this correctly
    path = filepath
    possible_mod_versions: list[str] = []  # TODO: actually populate this correctly
    possible_mc_versions: list[str] = []

    with zipfile.ZipFile(filepath, "r") as jar:
        manifest_data = None
        try:
            manifest = io.BytesIO(jar.read(jar.getinfo("META-INF/MANIFEST.MF")))
            manifest_data = _inspect_manifest(manifest.getvalue().decode())
        except KeyError:
            print("no META-INF/MANIFEST.MF")
        if manifest_data and manifest_data.get("mod_version") is not None:
            possible_mod_versions.append(manifest_data["mod_version"])

        try:
            mod_toml_bytes = io.BytesIO(jar.read(jar.getinfo("META-INF/mods.toml")))
        except KeyError:
            mod_toml_bytes = None
            mod_toml = None
            print("no META-INF/mods.toml")
        if mod_toml_bytes:
            mod_toml = tomllib.loads(mod_toml_bytes.getvalue().decode())
            print(mod_toml)
        if mod_toml:
            _inspect_mods_toml(mod_toml)

    ##
    # look at:
    # - pack.mcmeta
    # - META-INF/mods.toml
    # - META-INF/MANIFEST.MF
    ##
    # how to look at:
    #   - jar.read(jar.getinfo("META-INF/mods.toml"))
    ##
    # mod: backpacked-2.1.12-1.19.4.jar
    # where: "broken-mods"
    # helpful: META-INF/mods.toml
    #   - lists modloader type, loader version, modId, mod version, AND DEPENDENCIES like minimum forge version & other mods' versions
    ##
    # appleskin-forge-mc1.19.4-2.4.3.jar
    # - pack.mcmeta -> packing information for forge like package tool versions
    # - META-INF/mods.toml -> useful info but the mod version looks like an interpolation/templated string that wasn't replaced with the "correct" value
    # - META-INF/MANIFEST.MF -> has the mod's correct version stored as "Implementation-Version" (and Manifest-Version: 1.0)
    ##
    # Aquaculture-1.19.2-2.4.8.jar
    # - META-INF/mods.toml -> useful info but mod version is again a format/template string
    # - META-INF/MANIFEST.MF -> has the mod's correct version stored as "Implementation-Version" (and Manifest-Version: 1.0)
    ##
    # architectury-6.5.77-forge.jar
    # - META-INF/mods.toml -> useful info and version is populated correctly
    # - META-INF/MANIFEST.MF -> does not have mod's version
    ##

    return Mod(
        name=filepath.name,  # TODO: actually populate this correctly
        full_name=filepath.name,  # TODO: actually populate this correctly
        path=filepath,
        modloader_type=None,  # TODO: actually populate this correctly
        modloader_version_range=None,  # TODO: actually populate this correctly
        dependencies=[],  # TODO: actually populate this correctly
        possible_mc_versions=[],  # TODO: actually populate this correctly
        possible_mod_versions=[],  # TODO: actually populate this correctly
        mod_version_range=None,  # TODO: actually populate this correctly
    )


def main():
    crawl(pathlib.Path("/path/to/folder/of/mods"))


if __name__ == "__main__":
    main()
