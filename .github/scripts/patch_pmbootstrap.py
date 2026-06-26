#!/usr/bin/env python3
"""Patch pmbootstrap source files for CI robustness."""
import os, re

ws = os.environ['GITHUB_WORKSPACE']
pmb_root = os.path.join(ws, 'pmbootstrap')

# --- Fix 1: blockdevice.py - re-init chroot_native if deleted post-build ---
bd = os.path.join(pmb_root, 'pmb', 'install', 'blockdevice.py')
with open(bd) as f:
    c = f.read()

c = c.replace('import pmb.helpers.mount',
              'import pmb.chroot\nimport pmb.helpers.mount')

old = re.compile(r'^(\s+)# Create empty image files\s*\n\s+pmb\.chroot\.user\(\["mkdir",\s*"-p",\s*"/home/pmos/rootfs"\]\)',
                 re.MULTILINE)

def replacer_blockdev(m):
    ws = m.group(1)
    body_ws = ws + '    '
    return (
        f'{ws}# Re-init native chroot if pmbootstrap deleted it\n'
        f'{ws}if not Chroot.native().exists():\n'
        f'{body_ws}pmb.chroot.init(Chroot.native())\n'
        f'\n'
        f'{ws}# Create empty image files\n'
        f'{ws}pmb.chroot.user(["mkdir", "-p", "/home/pmos/rootfs"])'
    )

c = old.sub(replacer_blockdev, c)
with open(bd, 'w') as f:
    f.write(c)
print("✓ Patched blockdevice.py: chroot_native re-init")

# --- Fix 2: losetup.py - use /sbin/losetup (util-linux, not busybox) ---
# Only patch pmb.chroot.root calls (inside Alpine native chroot, where
# busybox /bin/losetup shadows util-linux /sbin/losetup).
# Do NOT patch pmb.helpers.run.root calls (Ubuntu host already has full losetup).
lp = os.path.join(pmb_root, 'pmb', 'install', 'losetup.py')
with open(lp) as f:
    c = f.read()

# Patch pmb.chroot.root calls (inside Alpine native chroot)
c = c.replace('pmb.chroot.root(["losetup"',
              'pmb.chroot.root(["/sbin/losetup"')
# Also patch losetup_cmd variable definition in mount()
c = c.replace('["losetup", "-f", "-P", img_path]',
              '["/sbin/losetup", "-f", "-P", img_path]')

with open(lp, 'w') as f:
    f.write(c)
print("✓ Patched losetup.py: /sbin/losetup in chroot calls (Alpine util-linux)")

# --- Fix 3: config/__init__.py - add "losetup" package explicitly to install_native_packages ---
cp = os.path.join(pmb_root, 'pmb', 'config', '__init__.py')
with open(cp) as f:
    c = f.read()

# Add "losetup" package after "util-linux" in install_native_packages
if '"losetup"' not in c:
    c = c.replace('"util-linux", "parted"',
                  '"util-linux", "losetup", "parted"')
    with open(cp, 'w') as f:
        f.write(c)
    print("✓ Patched config/__init__.py: losetup package added to install_native_packages")
else:
    print("  (config/__init__.py already has losetup in install_native_packages ✓)")
