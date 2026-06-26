#!/usr/bin/env python3
"""Patch pmbootstrap blockdevice.py to re-init native chroot if deleted post-build."""
import os

p = os.path.join(os.environ['GITHUB_WORKSPACE'],
                 'pmbootstrap', 'pmb', 'install', 'blockdevice.py')

with open(p) as f:
    c = f.read()

# Add pmb.chroot import
c = c.replace('import pmb.helpers.mount',
              'import pmb.chroot\nimport pmb.helpers.mount')

# Add chroot re-init check before mkdir
c = c.replace(
    'pmb.chroot.user(["mkdir", "-p", "/home/pmos/rootfs"])',
    'if not Chroot.native().exists():\n'
    '    pmb.chroot.init(Chroot.native())\n\n'
    'pmb.chroot.user(["mkdir", "-p", "/home/pmos/rootfs"])')

with open(p, 'w') as f:
    f.write(c)

print("Patched blockdevice.py: chroot_native re-init added")
