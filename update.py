#!/usr/bin/env python3

import subprocess
from pathlib import Path
import shutil
import re

# Files that should persist in the template directory
keep_files = [
    "include/liblvgl/lv_conf.h",
    "include/liblvgl/lv_conf.old.h",
    "include/liblvgl/llemu.h",
    "include/liblvgl/llemu.hpp",
    "include/liblvgl/font/lv_font.h",
    "src/liblvgl/display.c",
    "src/liblvgl/llemu.c",
    "src/liblvgl/llemu.cpp",
    "src/liblvgl/lv_fonts/pros_font_dejavu_mono_10.c",
    "src/liblvgl/lv_fonts/pros_font_dejavu_mono_18.c",
    "src/liblvgl/lv_fonts/pros_font_dejavu_mono_30.c",
    "src/liblvgl/lv_fonts/pros_font_dejavu_mono_40.c",
]


def clone(branch):
    if type(branch) != str:
        raise Exception("Parameter 'branch' should be a string!")

    sub_proc = subprocess.Popen(
        f"git clone -b {branch} https://github.com/lvgl/lvgl.git --recursive",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    sub_proc.wait()


def clean_template_dir():
    Path("temp").mkdir(exist_ok=True)

    for file in keep_files:
        output = Path(f"temp/{file}")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, output)

    shutil.rmtree("include/liblvgl")
    shutil.rmtree("src/liblvgl")

    for file in keep_files:
        output = Path(file)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f"temp/{file}", file)

    shutil.rmtree("temp")


def copy_lvgl_files():
    lvgl_src = Path("lvgl/src").resolve()
    header_files = list(lvgl_src.rglob("**/*.h"))
    source_files = list(lvgl_src.rglob("**/*.c"))
    files = header_files + source_files

    for file in files:
        if file in header_files:
            new_loc = Path(f"include/liblvgl/{file.relative_to(lvgl_src)}")
        elif file in source_files:
            new_loc = Path(f"src/liblvgl/{file.relative_to(lvgl_src)}")

        new_loc.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, new_loc)
        fix_includes(new_loc)

    Path("include/liblvgl/lvgl.h").unlink(missing_ok=True)
    shutil.copy("lvgl/lvgl.h", "include/liblvgl/lvgl.h")
    fix_includes("include/liblvgl/lvgl.h")

    shutil.rmtree("lvgl/")


def fix_includes(file_path):
    def resolve_include_path(match):
        file = Path(file_path)
        include_path = match.group(1)
        resolved_path = file.parent.joinpath(include_path).resolve()

        source_dir = Path.cwd().joinpath("src/")
        include_dir = Path.cwd().joinpath("include/")

        if resolved_path.is_relative_to(source_dir):
            relative_path = resolved_path.relative_to(source_dir)
        elif resolved_path.is_relative_to(include_dir):
            relative_path = resolved_path.relative_to(include_dir)
        else:
            print(
                f'[Warning]: File "{file}" includes file "{include_path}",'
                + " which is outside of the src or include directory."
                + " Manual editing may be required."
            )
            relative_path = include_path

        return f'#include "{relative_path}"'

    with open(file_path) as file:
        data = file.read()
        data = re.sub(r"#include \"((?:\.\./)+.*\.h)\"", resolve_include_path, data)
        data = re.sub(r"#include \"(src/|lvgl/)", '#include "liblvgl/', data)
        data = re.sub(
            r"(?<!LV_LVGL_H_INCLUDE_SIMPLE\n)(?:^[ \t]*(#include \"lvgl.h\")$)",
            '#include "liblvgl/lvgl.h"',
            data,
            flags=re.M,
        )

    with open(file_path, "w") as file:
        file.write(data)


if __name__ == "__main__":
    clone("release/v8.4")
    clean_template_dir()
    copy_lvgl_files()
