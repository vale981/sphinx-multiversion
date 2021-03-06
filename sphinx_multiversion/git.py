# -*- coding: utf-8 -*-
import collections
import datetime
import tempfile
import subprocess
import re
import tarfile

GitRef = collections.namedtuple(
    "VersionRef",
    ["name", "commit", "source", "is_remote", "refname", "creatordate",],
)


def get_all_refs(gitroot):
    cmd = (
        "git",
        "for-each-ref",
        "--format",
        "%(objectname)\t%(refname)\t%(creatordate:iso)",
        "refs",
    )
    output = subprocess.check_output(cmd, cwd=gitroot).decode()
    for line in output.splitlines():
        is_remote = False
        fields = line.strip().split("\t")
        if len(fields) != 3:
            continue

        commit = fields[0]
        refname = fields[1]
        creatordate = datetime.datetime.strptime(
            fields[2], "%Y-%m-%d %H:%M:%S %z"
        )

        # Parse refname
        matchobj = re.match(
            r"^refs/(heads|tags|remotes/[^/]+)/(\S+)$", refname
        )
        if not matchobj:
            continue
        source = matchobj.group(1)
        name = matchobj.group(2)

        if source.startswith("remotes/"):
            is_remote = True

        yield GitRef(name, commit, source, is_remote, refname, creatordate)


def get_refs(gitroot, tag_whitelist, branch_whitelist, remote_whitelist):
    for ref in get_all_refs(gitroot):
        if ref.source == "tags":
            if tag_whitelist is None or not re.match(tag_whitelist, ref.name):
                continue
        elif ref.source == "heads":
            if branch_whitelist is None or not re.match(
                branch_whitelist, ref.name
            ):
                continue
        elif ref.is_remote and remote_whitelist is not None:
            remote_name = ref.source.partition("/")[2]
            if not re.match(remote_whitelist, remote_name):
                continue
            if branch_whitelist is None or not re.match(
                branch_whitelist, ref.name
            ):
                continue
        else:
            continue

        yield ref


def copy_tree(src, dst, reference, sourcepath="."):
    with tempfile.SpooledTemporaryFile() as fp:
        cmd = (
            "git",
            "archive",
            "--format",
            "tar",
            reference.commit,
            "--",
            sourcepath,
        )
        subprocess.check_call(cmd, stdout=fp)
        fp.seek(0)
        with tarfile.TarFile(fileobj=fp) as tarfp:
            tarfp.extractall(dst)
