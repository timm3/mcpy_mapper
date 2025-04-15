# McPy Mapper
A suite of python tools for mapping out the modloaders & mods you need for your Java Minecraft worlds.

Not everyone is meticulous when it comes to documenting and managing their mods, or maybe some files corrupted, or whatever the case may be.
This tool aims to simplify the process of setting things up so you can play your worlds/saves again without breaking them.

# Project Requirements
- python ~= 3.12
  - while 3.12 may not be the minimum version required by imported libraries or the code itself, it is being developed on 3.12
  - this project uses the `tomllib` library which became a standard library in 3.11 but older python can pip install `toml` instead
- poetry >= 2.1.2

# Known Issues
- does not _yet_ support the `fabric` mod engine/loader
- there is no "build" for the library; you must use the scripts directly
- there are no automated tests
- the NBT file format version (your `level.dat` file is an NBT format) is stored as `mc_version` in the `engine_info` of data extracted about the world

# Goals
_in approximate order of importance_

- [x] ability to extract modloader version and list of mods (and their versions)
- [ ] force line-endings for the project
  - via git attributes? though this may be problematic if a need arises for different line-endings in different files...
- [ ] automated tests
- [ ] tox to run tests and validation like code formatting & linters
- [ ] pre-commit hooks for linters and automated code formatting
- [ ] ability to gather and prepare a "mod bundle" with both the mods and the appropriate modloader 
   1. ability to crawl through a directory looking for specific versions of mods and modloaders 
      1. to reduce or even avoid network usage
   2. ability to retrieve mods and modloaders from web
   3. ideally, one would be able to do this for more than one world at a time
      1. where possible, "reuse" a "mod bundle" if two worlds have the same requirements 
- [ ] print out what's going on as the tools do their thing
   1. with a flag/option to control verbosity
- [ ] support the `fabric` modloader and mods

# How to Use
For all scripts/tools, you can call them with `-h` or `--help` to get a description of command-line arguments, flags, and options.

## print out the modloader version and list of mods
Let's say you just want to know the modloader and mods needed for a world.

Simply pass `--world_directory` (or `-w` for short) argument to `main.py`.
This argument is the path to the minecraft world's directory (aka, "folder").
The directory typically (always?) is the name of the world and has a `level.dat` file inside it along with some other directories like `playerdata` or `advancements`.

If your saves are in the usual place on Windows, 
your Windows user account is named "bob", 
and your world's name is "SuperFunLand",
you'd use something like this,
```shell
python3.12 main.py --world_directory C:\Users\bob\AppData\Roaming\.minecraft\saves\SuperFunLand
```

Results will be printed to console.
If your world doesn't have any mods, you'll at least learn which version of minecraft is appropriate!
```json lines
{
  "engine_info": {
    "mc_data_version": "2584",
    "mc_version": "19133",
    "mc_version_name": "1.16.4",
    "mod_data_version": null,
    "mod_player_data_version": null,
    "mod_type": null,
    "mod_version": null,
    "mod_version_name": null
  },
  "mod_list": [],
  "world_name": "SuperFunLand"
}
```

Or, if it was using forge modloader and some mods, you might see something like this,
```json lines
{
  "engine_info": {
    "mc_data_version": "3120",
    "mc_version": "19133",
    "mc_version_name": "1.19.2",
    "mod_data_version": null,
    "mod_player_data_version": null,
    "mod_type": "forge",
    "mod_version": null,
    "mod_version_name": "43.2.8"
  },
  "mod_list": [
    {
      "name": "hukacraft",
      "version": "0.0.8",
      "version_is_weird": false
    },
    {
      "name": "sparkycraft",
      "version": "1.0.0",
      "version_is_weird": false
    },
  ],
  "world_name": "SuperFunLand"
}
```

## print out modloader and mod list for multiple worlds
This is very similar to what you'd do for one world, but you use `--many_worlds` (or `-m` for short)
and pass it the path to the directory that holds the worlds.

Making the same assumptions as before (using Windows, username is bob, etc.),
but having worlds named "SuperFunLand", "BeepBoop", and "Emerald City",
you'd use something like this
```shell
python3.12 main.py -m C:\Users\bob\AppData\Roaming\.minecraft\saves
```
and get results resembling those below
```json lines
SuperFunLand || 1.16.4
{
  "engine_info": {
    "mc_data_version": "2584",
    "mc_version": "19133",
    "mc_version_name": "1.16.4",
    "mod_data_version": null,
    "mod_player_data_version": null,
    "mod_type": null,
    "mod_version": null,
    "mod_version_name": null
  },
  "mod_list": [],
  "world_name": "SuperFunLand"
}
BeepBoop || 1.21.5
{
  "engine_info": {
    "mc_data_version": "4325",
    "mc_version": "19133",
    "mc_version_name": "1.21.5",
    "mod_data_version": null,
    "mod_player_data_version": null,
    "mod_type": null,
    "mod_version": null,
    "mod_version_name": null
  },
  "mod_list": [],
  "world_name": "BeepBoop"
}
Emerald City || 1.19.2
{
  "engine_info": {
    "mc_data_version": "3120",
    "mc_version": "19133",
    "mc_version_name": "1.19.2",
    "mod_data_version": null,
    "mod_player_data_version": null,
    "mod_type": "forge",
    "mod_version": null,
    "mod_version_name": "43.2.8"
  },
  "mod_list": [
    {
      "name": "hukacraft",
      "version": "0.0.8",
      "version_is_weird": false
    },
    {
      "name": "sparkycraft",
      "version": "1.0.0",
      "version_is_weird": false
    },
  ],
  "world_name": "Emerald City"
}
```

## save the extracted data
Use the `--save` or `-s` option, providing a path to a directory (folder) in which the data should be saved.
For each world, a JSON file will be created with the information that normally gets printed to your console / terminal.

This command will extract data from the SuperFunLand world and put it in a file named `SuperFunLand.json` inside the `mc_world_info` folder on bob's desktop.
```shell
python3.12 main.py -w C:\Users\bob\AppData\Roaming\.minecraft\saves\SuperFunLand -s C:\Users\bob\Desktop\mc_world_info
```

If you use `--many-worlds` instead of `--world-directory`, then a separate file will be generated for and named after each world found.
