#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.

# Generate a repository overview with per-package pages.

import datetime
import json
import os
import shutil
import sys

import pyalpm
from jinja2 import Template
from pycman import config, pkginfo

__program__ = "alpm-html"
__version__ = "0.8.1"

# The alpm database handle
handle = None


def optdepends_parse(dlist):
    arr = []
    for depend in dlist:
        splits = depend.split(":")
        if len(splits) > 1:
            desc = splits[1]
        else:
            desc = ""
        arr.append({"name": splits[0], "description": desc.strip()})
    return arr


def file_data(dlist):
    file_count = 0
    dir_count = 0
    arr = []
    # ('usr/share/pkgtools/newpkg/presets/pkgbuild.action', 812, 33188),
    for file in dlist:
        if file[0].endswith("/"):
            dir_count += 1
        else:
            file_count += 1
        arr.append({"name": file[0], "bytes": file[1], "mode": oct(file[2])})
    return {"file_count": file_count, "dir_count": dir_count, "files": arr}


def final_name(pkg_filename):
    """Given a package's file name, return the file name minus the trailing '.pkg.tar.xz'.
    Also handles gz and bz2 files.
    Appends '.html' as well."""
    return os.path.splitext(pkg_filename)[0][: -len(".pkg.tar")] + ".html"


def package_template(package, outfile, repo, template_file):
    te = Template(open(template_file).read())
    with open(outfile, "w") as f:
        f.write(te.render(pkg=package, repo_name=repo))


def pkg_to_dict(package, absolute_path):
    return {
        "name": package.name,
        "base": package.base,
        "version": package.version,
        "url": package.url,
        "licenses": package.licenses,
        "groups": package.groups,
        "provides": package.provides,
        "depends": package.depends,
        "optdepends": optdepends_parse(package.optdepends),
        "conflicts": package.conflicts,
        "replaces": package.replaces,
        "compressed_size": package.size,
        "installed_size": package.isize,
        "packager": package.packager,
        "architecture": package.arch,
        "build_date": datetime.datetime.utcfromtimestamp(package.builddate),
        "description": package.desc,
        "filename": package.filename,
        "files": file_data(package.files),
        "backup": package.backup,
        "scriptlet": package.has_scriptlet,
        "absolute_path": absolute_path,
        "html_path": final_name(os.path.basename(absolute_path)),
        "filename": os.path.basename(absolute_path),
    }


def process_package(absolute_path):
    global handle
    pkg = handle.load_pkg(absolute_path)
    return pkg_to_dict(pkg, absolute_path)


def main(argv):
    global handle
    retcode = 0
    parser = config.make_parser(
        prog=__program__,
        description="Generate a static site for browsing an Arch repo, styled like the main website.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    group = parser.add_argument_group("Generator options")
    group.add_argument(
        "-d",
        "--pkg-dir",
        metavar="<dir>",
        action="store",
        dest="pkg_dir",
        type=str,
        default=".",
        help="Path to the directory of packages",
    )
    group.add_argument(
        "-o",
        "--output",
        metavar="<dir>",
        action="store",
        dest="output",
        type=str,
        default="build",
        help="Directory to put resulting HTML files",
    )
    group.add_argument(
        "-n",
        "--name",
        metavar="<name>",
        action="store",
        dest="repo_name",
        type=str,
        default="unofficial",
        help="Repository name. Defaults to unofficial",
    )
    group.add_argument(
        "--url",
        metavar="<url>",
        action="store",
        dest="repo_url",
        type=str,
        help="The URL to use in the pacman configuration",
    )
    group.add_argument(
        "--key-id",
        metavar="<ID>",
        action="store",
        dest="key_id",
        type=str,
        help="GPG key ID that has been used to sign this repository",
    )
    group.add_argument(
        "--description",
        metavar="<text>",
        action="store",
        dest="description",
        type=str,
        help="The repository description",
    )
    group.add_argument(
        "--resources",
        metavar="<dir>",
        action="store",
        dest="res_dir",
        type=str,
        default=f"/usr/share/{__program__}",
        help="Where additional resources (templates, CSS) are in the system",
    )
    args = parser.parse_args(argv)

    handle = config.init_with_config_and_options(args)
    os.makedirs(args.output, mode=0o755, exist_ok=True)

    packages = []
    pkg_dir_list = os.listdir(args.pkg_dir)
    pkg_dir_list.sort()
    for filename in pkg_dir_list:
        if ".pkg.tar." in filename and not filename.endswith(".sig"):
            file = os.path.join(args.pkg_dir, filename)
            if args.verbose:
                print(file)
            data = process_package(file)
            packages.append(data)
            output_file = os.path.join(args.output, data["html_path"])
            package_template(
                data,
                outfile=output_file,
                repo=args.repo_name,
                template_file=os.path.join(args.res_dir, "package.html.j2"),
            )

    te = Template(open(os.path.join(args.res_dir, "index.html.j2")).read())
    with open(os.path.join(args.output, "index.html"), "w") as f:
        f.write(
            te.render(
                packages=packages,
                repo_name=args.repo_name,
                url=args.repo_url,
                repo_desc=args.description,
                key_id=args.key_id,
            )
        )

    shutil.copyfile(
        os.path.join(args.res_dir, "archrepo.css"),
        os.path.join(args.output, "archrepo.css"),
    )
    return retcode


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
