#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path("pmbootstrap/pmb")

def patch_file(path: Path, transform, label: str):
    text = path.read_text()
    new = transform(text)
    if new != text:
        path.write_text(new)
        print(f"✓ Patched {path}: {label}")
        return True
    print(f"- No change {path}: {label}")
    return False

# 1) Asegurar que el chroot nativo instale losetup completo
config_init = ROOT / "config" / "__init__.py"
if config_init.exists():
    def add_losetup_to_native_packages(text: str) -> str:
        if '"losetup"' in text or "'losetup'" in text:
            return text

        # Caso típico: lista con util-linux, parted, cryptsetup, qemu-...
        text = text.replace('"util-linux",', '"util-linux",\n "losetup",')
        text = text.replace("'util-linux',", "'util-linux',\n 'losetup',")
        return text

    patch_file(config_init, add_losetup_to_native_packages, "add losetup to native packages")

# 2) Parche fuerte: todo losetup interno debe apuntar a /usr/sbin/losetup
losetup_py = ROOT / "install" / "losetup.py"
if losetup_py.exists():
    def force_usr_sbin_losetup(text: str) -> str:
        # Deshacer parche anterior incorrecto a /sbin/losetup
        text = text.replace('"/sbin/losetup"', '"/usr/sbin/losetup"')
        text = text.replace("'/sbin/losetup'", "'/usr/sbin/losetup'")

        # Convertir llamadas directas ["losetup", ...] a ["/usr/sbin/losetup", ...]
        text = text.replace('["losetup"', '["/usr/sbin/losetup"')
        text = text.replace("['losetup'", "['/usr/sbin/losetup'")

        # Si hay variable cmd = "losetup" o losetup_cmd
        text = re.sub(r'=\s*"losetup"', '= "/usr/sbin/losetup"', text)
        text = re.sub(r"=\s*'losetup'", "= '/usr/sbin/losetup'", text)

        return text

    patch_file(losetup_py, force_usr_sbin_losetup, "force /usr/sbin/losetup")

# 3) blockdevice.py: re-init chroot_native if deleted (simple, proven approach)
bd = ROOT / "install" / "blockdevice.py"
if bd.exists():
    with open(bd) as f:
        c = f.read()
    
    # Add pmb.chroot import if not present  
    c = c.replace('import pmb.helpers.mount',
                  'import pmb.chroot\nimport pmb.helpers.mount')
    
    # Re-init native chroot before mkdir (from earlier working patch)
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
    
    new_c = old.sub(replacer_blockdev, c)
    if new_c != c:
        with open(bd, 'w') as f:
            f.write(new_c)
        print(f"✓ Patched {bd}: chroot_native re-init before mkdir")
    else:
        print(f"- No change {bd}: already patched or structure changed")

print("=== grep losetup after patch ===")
for path in ROOT.rglob("*.py"):
    txt = path.read_text(errors="ignore")
    if "losetup" in txt or "/sbin/losetup" in txt or "/usr/sbin/losetup" in txt:
        print(path)
        for i, line in enumerate(txt.splitlines(), start=1):
            if "losetup" in line:
                print(f"  {i}: {line}")
