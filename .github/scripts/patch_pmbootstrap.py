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

# --- Fix 2: losetup.py - use /usr/bin/losetup (util-linux, not busybox) ---
# Only patch pmb.chroot.root calls (inside Alpine native chroot).
# Do NOT patch pmb.helpers.run.root calls (Ubuntu host, losetup already works).
lp = os.path.join(pmb_root, 'pmb', 'install', 'losetup.py')
with open(lp) as f:
    c = f.read()

# Only target chroot-side losetup calls and the losetup_cmd variable
c = c.replace('pmb.chroot.root(["losetup"',
              'pmb.chroot.root(["/usr/bin/losetup"')
# Also patch the losetup_cmd variable definition in mount()
c = c.replace('["losetup", "-f", "-P", img_path]',
              '["/usr/bin/losetup", "-f", "-P", img_path]')

with open(lp, 'w') as f:
    f.write(c)
print("✓ Patched losetup.py: /usr/bin/losetup in chroot calls only")

# Verify no host-side calls were accidentally patched
with open(lp) as f:
    c = f.read()
if '/usr/bin/losetup' in c and 'pmb.helpers.run.root(["/usr/bin/losetup"' not in c:
    print("  (Host-side pmb.helpers.run.root calls left untouched ✓)")
