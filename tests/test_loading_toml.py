import pytest


def test_loading_journeymap_5_9_5():
    # note: 2025-04-14: this has not been tested yet :)
    from mcpy_mapper.local_crawler import _inspect_mods_toml

    # setup
    data = {  # a dict from `tomllib.loads()`
        "modLoader": "javafml",
        "loaderVersion": "[44,)",
        "issueTrackerURL": "https://github.com/TeamJM/journeymap/issues",
        "license": "All rights reserved",
        "mods": [
            {
                "modId": "journeymap",
                "version": "5.9.5",
                "displayName": "Journeymap",
                "updateJSONURL": "https://forge.curseupdate.com/32274/journeymap",
                "displayURL": "http://journeymap.info",
                "logoFile": "journeymap.png",
                "credits": "Techbrew, Mysticdrew, gdude",
                "authors": "Techbrew, Mysticdrew",
                "description": "JourneyMap: Real-time map in-game or in a web browser as you explore. JourneyMap API: v1.19.4-1.9-SNAPSHOT. Built: 2023-04-03-11:22:53.\n",
            }
        ],
        "dependencies": {
            "journeymap": [
                {"modId": "forge", "mandatory": True, "versionRange": "[44.0.0,)"}
            ]
        },
    }
    expected_result = dict(
        name="journeymap",
        full_name="Journeymap",
        # path=None,
        modloader_type="javafml",  # or should it test that it's "forge"?
        modloader_version_range={"minimum": 44, "maximum": None},
        dependencies={
            "forge": {
                "modId": "forge",
                "mandatory": True,
                "versionRange": {"minimum": "44.0.0", "maximum": None},
            }
        },
        possible_mc_versions=None,
        possible_mod_versions=["5.9.5"],
        mod_version_range=None,
    )

    # test
    result = _inspect_mods_toml(data)
    assert (
        result == expected_result
    )  # TODO: replace this with something that would actually compare the nested dictionaries

    # teardown
