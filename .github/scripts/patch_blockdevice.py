#!/usr/bin/env python3
"""Patch pmbootstrap blockdevice.py to re-init native chroot if deleted post-build."""
import os, re

p = os.path.join(os.environ['GITHUB_WORKSPACE'],
                 'pmbootstrap', 'pmb', 'install', 'blockdevice.py')

with open(p) as f:
    c = f.read()

# Add pmb.chroot import (right before import pmb.helpers.mount)
c = c.replace('import pmb.helpers.mount',
              'import pmb.chroot\nimport pmb.helpers.mount')

# Add chroot re-init check before mkdir.
# Match the full indented line to preserve context.
old = re.compile(r'^(\s+)# Create empty image files\s*\n\s+pmb\.chroot\.user\(\["mkdir",\s*"-p",\s*"/home/pmos/rootfs"\]\)',
                 re.MULTILINE)

def replacer(m):
    ws = m.group(1)  # leading whitespace of the comment
    body_ws = ws + '    '
    return (
        f'{ws}# Re-init native chroot if pmbootstrap deleted it\n'
        f'{ws}if not Chroot.native().exists():\n'
        f'{body_ws}pmb.chroot.init(Chroot.native())\n'
        f'\n'
        f'{ws}# Create empty image files\n'
        f'{ws}pmb.chroot.user(["mkdir", "-p", "/home/pmos/rootfs"])'
    )

c = old.sub(replacer, c)

with open(p, 'w') as f:
    f.write(c)

print("Patched blockdevice.py: chroot_native re-init added")
