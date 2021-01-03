# alpm-html

Generate a static site for browsing an Arch repo, styled like the main website.

Given a directory full of [Arch Linux](https://archlinux.org) packages, it will scan each and build a (in my opinion) decent looking HTML page.
Each file is almost fully standalone, with the exception of an "archrepo.css" file that is also placed in the output directory.
No images or javascript scripts are used, intentionally.

See the man page [alpm-html(1)](alpm-html.1.asciidoc) for usage details.

## Installing

It's not really meant to be installed anywhere else but an Arch Linux system. As such, I really recommend using the AUR package.
