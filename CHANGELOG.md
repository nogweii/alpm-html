# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] - 2020-12-29
### Added
- Dependencies now link to the arch website or sibling packages in this repo when found.
  Requested by [eschwartz](https://bbs.archlinux.org/profile.php?id=84187)
- Optional support for minifying HTML using the [htmlmin](https://archlinux.org/packages/community/any/python-htmlmin/) library

### Changed
- Package detail pages link to the index page
- External links have an indicator, derived from Wikipedia
- Verbose and debug logs can now be optionally colored using the [daiquri](https://archlinux.org/packages/community/any/python-daiquiri/) library
- The "License" and "Group" labels will now be pluralized only if necessary, using the [inflect](https://archlinux.org/packages/community/any/python-inflect/) library

## [0.9.2] - 2020-12-24
### Fixed
- HTML validation warnings and errors

## [0.9.1] - 2020-12-23
### Added
- PKGBUILD for AUR

### Changed
- index template includes a link for the GPG key ID, if it was mentioned

### Fixed
- Copyright symbol in footer renders correctly now that the document declares
  UTF-8 charset.

## [0.9.0] - 2020-12-03
### Added
- Licensed under the GPLv3
- Man page added
- CHANGELOG added

### Fixed
- Python's list sort method returns `None` which is not iterable

## [0.8.0] - 2020-11-27
### Added
- First release!
