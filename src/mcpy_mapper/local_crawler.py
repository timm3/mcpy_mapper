"""
Crawl through local files to better understand them.
"""

import io
import json
import os
import pathlib
import re
import tomllib
import zipfile
from dataclasses import dataclass


ERROR_LINE_REGEX = re.compile(r"line (\d+)")


@dataclass
class ModLoader:
    name: str  # todo: is this really needed?
    family: str  # forge, fabric, etc. -- todo: could probably afford to rename this
    version: str
    base_mc_version: str
    path: pathlib.Path | None  # if None, then not available


@dataclass
class Mod:
    name: str | None
    full_name: str | None
    possible_names: list[str]
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


def crawl_mods(directory: pathlib.Path) -> list[Mod]:
    """
    Walks `directory` and subdirectories looking for and categorizing mods.
    # All directories with "mods" in the name (case-insensitive) will be expected to have mods inside them.
    # This is to account for scenario where you've several mod directories for several different modloaders or minecraft versions.
    # If directory does not have "mods" in the name, it is assumed to be a mod.
    """
    ret: list[Mod] = []
    for dir_str, dirnames, filenames in os.walk(directory, followlinks=True):
        dirpath = pathlib.Path(dir_str)

        # add local jar files
        for filename in filenames:
            if filename.endswith(".jar"):
                ret.extend(inspect_mod_jar(pathlib.Path(dirpath, filename)))

        # process other directories
        for dirname in dirnames:
            ret.extend(crawl_mods(pathlib.Path(dirpath, dirname)))
    return ret


def _inspect_manifest(manifest: str) -> dict:
    data: dict[str, str | list[str] | None] = {
        "mod_version": None,
        "possible_names": [],
    }
    for line in manifest.splitlines():
        if line.startswith("Implementation-Version"):
            data["mod_version"] = line.split(":")[1].strip()
        if line.startswith("Specification-Title") or line.startswith(
            "Implementation-Title"
        ):
            data["possible_names"].append(line.split(":")[1].strip())  # type: ignore[union-attr]
    return data


def get_version_range(version_range: str) -> dict[str, str | None]:
    sans_bounds_indicators = version_range.strip("[])( ")
    bounds = sans_bounds_indicators.split(",")
    if len(bounds) != 2:
        if len(bounds) == 1:
            # the range is more of a point :P
            return {
                "minimum": bounds[0].strip() or None,
                "maximum": bounds[0].strip() or None,
            }
        # too many items!
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
        for dependency in _toml.get("dependencies", {}).get(mod["modId"], []):
            # todo: maybe do Mod instead of a simple dict?
            ret["dependencies"][dependency["modId"]] = dependency
            ret["dependencies"][dependency["modId"]]["versionRange"] = (
                get_version_range(dependency["versionRange"])
            )
        mods.append(ret)
    return mods


def _fix_invalid_multiline_string(toml: str, error_message: str) -> str:
    # todo: support joining together multiline strings that span more than two lines,
    #  but should that be handled here or by the caller?
    #  This function's name certainly implies it will handle the whole thing...
    error_line = int(re.search(ERROR_LINE_REGEX, error_message).group(1))  # type: ignore[union-attr]
    ret_lines: list[str] = []
    for idx, line in enumerate(toml.splitlines()):
        if idx == error_line:
            ret_lines[-1] = ret_lines[-1].rstrip() + " " + line
        else:
            ret_lines.append(line)
    return "\n".join(ret_lines)


def inspect_mod_jar(filepath: pathlib.Path) -> list[Mod]:
    possible_mod_versions: list[str] = []
    possible_names: list[str] = []

    def minimal_return():
        return [
            Mod(
                name=min(
                    possible_names or [""]
                ),  # note: reasonable assumption? can change later
                full_name="",
                possible_names=possible_names,
                path=filepath,
                modloader_type=None,
                modloader_version_range=None,
                dependencies=[],
                possible_mc_versions=[],
                possible_mod_versions=possible_mod_versions,
                mod_version_range=None,
            )
        ]

    with zipfile.ZipFile(filepath, "r") as jar:
        manifest_data = None
        try:
            manifest = io.BytesIO(jar.read(jar.getinfo("META-INF/MANIFEST.MF")))
            manifest_data = _inspect_manifest(manifest.getvalue().decode())
        except KeyError:
            print("no META-INF/MANIFEST.MF")
        if manifest_data and manifest_data.get("mod_version") is not None:
            possible_mod_versions.append(manifest_data["mod_version"])
        if manifest_data and manifest_data.get("possible_names"):
            possible_names.extend(manifest_data["possible_names"])

        try:
            mod_toml_bytes = io.BytesIO(jar.read(jar.getinfo("META-INF/mods.toml")))
        except KeyError:
            print("no META-INF/mods.toml")
            return minimal_return()

    mod_toml = None
    if mod_toml_bytes:
        toml_string = mod_toml_bytes.getvalue().decode().strip()
        try:
            mod_toml = tomllib.loads(toml_string)
        except tomllib.TOMLDecodeError as e:
            if "'\\n'" in str(e):
                # note: should probably do this multiple times or some such in case there are multiple multiline strings...
                toml_string = _fix_invalid_multiline_string(toml_string, str(e))
                mod_toml = tomllib.loads(toml_string)
    if not mod_toml:
        # note 2025-04-20: will this ever happen?
        return minimal_return()

    ret = []
    toml_data = _inspect_mods_toml(mod_toml)
    for data in toml_data:
        # todo: handle multi-mod mods better.
        #  Some mods like "curios" version 1.19.2-5.1.3.0
        #  incorrectly list their version in the mod declared
        #  in `toml_data` but have the correct value in their
        #  manifest data.
        #  The problem is... knowing when and what to include
        #  of these toml_data mod declarations for both
        #  `possible_names` and `possible_mod_versions`.
        possible_names.append(data["name"])
        if data["name"] in possible_names:
            possible_mod_versions.extend(data["possible_mod_versions"])
        mod = Mod(
            name=data["name"],
            full_name=data["full_name"],
            possible_names=possible_names,
            path=filepath,
            modloader_type=data["modloader_type"],
            modloader_version_range=data["modloader_version_range"],
            dependencies=data["dependencies"],
            possible_mc_versions=data["possible_mc_versions"],
            possible_mod_versions=possible_mod_versions,  # or should it be `data["possible_mod_versions"]`? I really wasn't expecting a single mod file to have multiple mods...
            mod_version_range=None,
        )
        ret.append(mod)

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

    return ret


def inspect_modloader_jar(filepath: pathlib.Path) -> ModLoader | None:
    with zipfile.ZipFile(filepath, "r") as jar:
        manifest = jar.read(jar.getinfo("META-INF/MANIFEST.MF"))

        is_forge = False
        for line in manifest.decode().splitlines():
            if "forge" in line.lower():
                # probably good enough :)
                is_forge = True
                break
        if not is_forge:
            return None  # todo: or should an empty ModLoader be returned?

        install_profile = json.loads(
            jar.read(jar.getinfo("install_profile.json")).decode()
        )
        top_level_version = json.loads(jar.read(jar.getinfo("version.json")).decode())

        return ModLoader(
            name=top_level_version["id"],
            family=install_profile["profile"],
            version=install_profile["version"],  # or...? top_level_version["id"]
            base_mc_version=top_level_version["inheritsFrom"],
            path=filepath,
        )


def crawl_modloaders(directory: pathlib.Path) -> list[ModLoader]:
    """
    Crawl through a directory to discover modloaders.
    """
    ret: list[ModLoader] = []
    for dir_str, dirnames, filenames in os.walk(directory, followlinks=True):
        dirpath = pathlib.Path(dir_str)

        # add local jar files
        for filename in filenames:
            if filename.endswith(".jar"):
                modloader = inspect_modloader_jar(pathlib.Path(dirpath, filename))
                if modloader:
                    ret.append(modloader)

        # process other directories
        for dirname in dirnames:
            ret.extend(crawl_modloaders(pathlib.Path(dirpath, dirname)))

    return ret
