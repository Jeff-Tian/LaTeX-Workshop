'''
This script fetch the latest list of packages and their descriptions
from CTAN at https://ctan.org/pkg and save the result as a json file.

The result is used to generate usepackage and documentclass
intellisense for LaTeX Workshop.
'''

from pathlib import Path
import json
from sys import argv
import requests

CHECK_IF_PKG_EXISTS = True
CTAN_SOURCE = 'https://ctan.org/json/2.0/packages'
TEXMF = '/usr/local/texlive/2019/texmf-dist'


def load_texmfbd(lsR, ctanDict):
    """
    Create a dictionnary from the ls-R database from the LaTeX installation

    :param lsR: The path to the TEXMF/ls-R
    :param ctanDict: A dictionnary built from the CTAN package list

    :return: a tuple (lsRdb, allfiles)
        - lsRdb is a dictionnary mapping for every package in ctanDict all the .sty, .cls, .def
          files listed under that dictionnary in lsR
        - allfiles is an array of all the .sty, .cls, .def files listed in lsR
    """
    lsRdb = {}
    pkg = None
    pkgfiles = []
    allfiles = []
    allpkgs = ctanDict.keys()
    with open(lsR) as fd:
        for line in fd:
            line = line.rstrip('\n')
            if line.startswith('./doc') or line.startswith('./source'):
                # Skip source and doc entries
                continue
            if line.endswith(':') and line.startswith('./'):
                # Enter a new package
                pkg = None
                for part in reversed(Path(line[0:-1]).parts):
                    if part in allpkgs:
                        pkg = part
                        break
                pkgfiles = []
            if pkg is None:
                continue
            if line != '':
                pkgfile = Path(line)
                if pkgfile.suffix in ['.sty', '.def', '.cls']:
                    pkgfiles.append(pkgfile.name)
                    allfiles.append(pkgfile.name)
            else:
                if len(pkgfiles) > 0:
                    if pkg not in lsRdb:
                        lsRdb[pkg] = []
                    lsRdb[pkg].extend(pkgfiles)
                pkg = None
    return (lsRdb, allfiles)


def package2sty(pkgname, lsRdb, allsty):
    """
    Find the main .sty file for a given package

    :param pkgname: the name of a package as registered on CTAN
    :param lsRdb: a dictionnary of the ls-R database

    :return a filename without the .sty extension or None
    """
    styname = pkgname + '.sty'
    if styname in allsty:
        return pkgname
    if pkgname in lsRdb:
        files = lsRdb[pkgname]
        if pkgname + '.sty' in files:
            return pkgname
        else:
            for f in files:
                if f.lower() == pkgname + '.sty':
                    return Path(f).stem
    return None


# def pkg_exists(pkgname, suffix, lsRdb):
#     """
#     Check if a file pkgname + suffix exists in the ls-R database

#     :param pkgname: Name of a package
#     :param suffix: The suffix to add to get a real file name
#     :param lsRdb: A dictionnary containing the ls-R database
#     """
#     if not CHECK_IF_PKG_EXISTS:
#         return True
#     if pkgname in lsRdb:
#         files = lsRdb[pkgname]
#         if pkgname + suffix in files:
#             return True
#     return False

def get_classes(all_lsR_files, ctanDict):
    """
    Get all the .cls files from the ls-R database and extract the corresponding details from ctanDict if the entry exists

    :param all_lsR_files: The list of all files listed in ls-R
    :param ctanDict: A dictionnary built from the CTAN package list
    """
    class_data = {}
    for c in all_lsR_files:
        if not c.endswith('.cls'):
            continue
        base = Path(c).stem
        detail = ''
        documentation = ''
        if base in ctanDict:
            detail = ctanDict[base]['detail']
            documentation = ctanDict[base]['documentation']
        class_data[base] = {}
        class_data[base]['command'] = base
        class_data[base]['detail'] = detail
        class_data[base]['documentation'] = documentation
    return class_data

def get_packages(lsRdb, ctanDict, allsty):
    """
    Get the package for which a .sty file exists

    :param lsRdb: A dictionnary containing the ls-R database
    :param ctanDict: A dictionnary built from the CTAN package list
    """
    package_data = {}
    for pkg in ctanDict:
        basefile = package2sty(pkg, lsRdb, allsty)
        if basefile is not None:
            package_data[pkg] = ctanDict[pkg].copy()
            package_data[pkg]['command'] = basefile
    return package_data

def add_extra_packages(packages, extra_packages):
    for pkg in extra_packages:
        if pkg not in packages.keys():
            packages[pkg] = extra_packages[pkg].copy()


def build_ctanDict(ctanList):
    ctanDict = {}
    for x in ctanList:
        ctanDict[x['key']] = {}
        ctanDict[x['key']]['command'] = x['key']
        ctanDict[x['key']]['documentation'] = 'https://ctan.org/pkg/' + x['key']
        ctanDict[x['key']]['detail'] = x['caption']
    return ctanDict

if __name__ == "__main__":
    if len(argv) == 2:
        TEXMF = argv[1]
    # fetch, iterate and adapt.
    ctanDict = build_ctanDict(json.loads(requests.get(CTAN_SOURCE).content))
    lsRdb, all_lsR_files = load_texmfbd(TEXMF + '/ls-R', ctanDict)

    package_data = get_packages(lsRdb, ctanDict, all_lsR_files)
    add_extra_packages(package_data, json.load(open('./extra-packagenames.json')))
    json.dump(package_data, open('../data/packagenames.json', 'w+', encoding='utf-8'),
              separators=(',', ': '), sort_keys=True, indent=2, ensure_ascii=False)

    class_data = get_classes(all_lsR_files, ctanDict)
    json.dump(class_data, open('../data/classnames.json', 'w+', encoding='utf-8'),
              separators=(',', ': '), sort_keys=True, indent=2, ensure_ascii=False)
