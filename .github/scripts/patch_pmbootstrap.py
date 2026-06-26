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

        # Si hay variable cmd = "losetup"
        text = re.sub(r'=\s*"losetup"', '= "/usr/sbin/losetup"', text)
        text = re.sub(r"=\s*'losetup'", "= '/usr/sbin/losetup'", text)

        return text

    patch_file(losetup_py, force_usr_sbin_losetup, "force /usr/sbin/losetup")