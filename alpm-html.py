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
from collections import defaultdict
import logging

import pyalpm
from jinja2 import Template
from pycman import config, pkginfo
import inflect
try:
    import daiquiri
    DAIQUIRI_LOGS = True
except ModuleNotFoundError:
    DAIQUIRI_LOGS = False
try:
    import htmlmin
    HTML_MIN = True
except ModuleNotFoundError:
    HTML_MIN = False

__program__ = "alpm-html"
__version__ = "0.9.2"
if DAIQUIRI_LOGS:
    logger = daiquiri.getLogger(__program__)
else:
    logger = logging.getLogger(__program__)

inflection = inflect.engine()
args = None
official_repos = [
    "core",
    "community",
    "community-testing",
    "extra",
    "kde-unstable",
    "multilib",
    "multilib-testing",
    "testing"
]
cached_packages = dict()
sibling_packages = []


def dependency_link(package_name):
    """Given the name of a package, return a useful link target if one can be
    found."""

    siblings = list(filter(lambda pkg: (pkg.name == package_name), sibling_packages))
    if len(siblings) > 0:
        link = package_html_path(siblings[0])
    elif package_name in cached_packages:
        sync_pkg = cached_packages[package_name]
        link = f"https://archlinux.org/packages/{sync_pkg.db.name}/{sync_pkg.arch}/{sync_pkg.name}/"
    else:
        link = None

    logger.debug(f"Found link to dependency {package_name} at link {link}")
    return link


def optdepends_parse(dlist):
    arr = []
    for depend in dlist:
        splits = depend.split(":")
        if len(splits) > 1:
            desc = splits[1]
        else:
            desc = ""
        name = splits[0]
        arr.append({"name": name, "description": desc.strip(), "link": dependency_link(name)})
    return arr


def depends_search(dependencies):
    details = []
    for dependency in dependencies:
        details.append({"name": dependency, "link": dependency_link(dependency)})
    return details


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


def package_html_path(package):
    """Given the path to a package, return the file name minus the trailing
    '.pkg.tar.xz'. (Also handling gz and bz2 compressed files.)
    Appends '.html' as well."""
    return os.path.splitext(os.path.basename(package.filename))[0][: -len(".pkg.tar")] + ".html"


def minify_html(html_text):
    if HTML_MIN:
        logger.debug("Minifying HTML")
        return htmlmin.minify(html_text)
    else:
        return html_text


def package_template(package, outfile, repo, template_file):
    logger.info(f"Generating template for {package['name']} into {outfile}")
    te = Template(open(template_file).read())
    with open(outfile, "w") as f:
        html_text = te.render(pkg=package, repo_name=repo, strings=label_strings(package))
        f.write(minify_html(html_text))


def pkg_to_dict(package, absolute_path):
    global args
    return {
        "name": package.name,
        "base": package.base,
        "version": package.version,
        "url": package.url,
        "licenses": package.licenses,
        "groups": package.groups,
        "provides": package.provides,
        "depends": depends_search(package.depends),
        "optdepends": optdepends_parse(package.optdepends),
        "conflicts": package.conflicts,
        "replaces": package.replaces,
        "compressed_size": package.size,
        "installed_size": package.isize,
        "packager": package.packager,
        "architecture": package.arch,
        "build_date": datetime.datetime.utcfromtimestamp(package.builddate),
        "description": package.desc,
        "files": file_data(package.files),
        "backup": package.backup,
        "scriptlet": package.has_scriptlet,
        "absolute_path": absolute_path,
        "filename": os.path.basename(absolute_path),
        "html_path": package_html_path(package),
        "repo_name": args.repo_name
    }


def label_strings(package):
    return {
        "licenses": inflection.plural("License", len(package['licenses'])),
        "groups": inflection.plural("Group", len(package['groups']))
    }


def main(argv):
    global HTML_MIN
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
    group.add_argument(
        "--html-min",
        action="store_true",
        help="Minify the generated HTML",
    )
    global args
    args = parser.parse_args(argv)

    # Set up logging
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    if DAIQUIRI_LOGS:
        daiquiri.setup(level=log_level)
    else:
        logging.basicConfig(level=log_level)

    if args.html_min and not HTML_MIN:
        logger.error("Can not minify HTML without the htmlmin library installed!")
        return 1
    HTML_MIN = args.html_min

    handle = config.init_with_config_and_options(args)
    os.makedirs(args.output, mode=0o755, exist_ok=True)

    for db in handle.get_syncdbs():
        if db.name.lower() in official_repos:
            for package in db.pkgcache:
                cached_packages[package.name] = package

    packages = []
    pkg_dir_list = os.listdir(args.pkg_dir)
    pkg_dir_list.sort()
    for filename in pkg_dir_list:
        if ".pkg.tar." in filename and not filename.endswith(".sig"):
            file = os.path.join(args.pkg_dir, filename)
            logger.debug(f"Loading package {file=}")
            sibling_packages.append(handle.load_pkg(file))

    for package in sibling_packages:
        data = pkg_to_dict(package, package.filename)
        packages.append(data)
        output_file = os.path.join(args.output, package_html_path(package))
        package_template(
            data,
            outfile=output_file,
            repo=args.repo_name,
            template_file=os.path.join(args.res_dir, "package.html.j2"),
        )

    te = Template(open(os.path.join(args.res_dir, "index.html.j2")).read())
    index_page = os.path.join(args.output, "index.html")
    logger.info(f"Writing index template to {index_page}")
    with open(index_page, "w") as f:
        html_text = te.render(
            packages=packages,
            repo_name=args.repo_name,
            url=args.repo_url,
            repo_desc=args.description,
            key_id=args.key_id,
        )
        f.write(minify_html(html_text))

    shutil.copyfile(
        os.path.join(args.res_dir, "archrepo.css"),
        os.path.join(args.output, "archrepo.css"),
    )
    return retcode


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
