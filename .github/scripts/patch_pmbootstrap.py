#!/usr/bin/env python3
from pathlib import Path
import re, os

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

# 3) Parche defensivo en blockdevice.py: si chroot_native desaparece, reinit
blockdevice_py = ROOT / "install" / "blockdevice.py"
if blockdevice_py.exists():
    def patch_blockdevice(text: str) -> str:
        if "AUTO_FIX_CHROOT_NATIVE_PMOS_BEGONIA" in text:
            return text

        marker = "def create_and_mount_image"
        if marker not in text:
            return text

        # Inserta utilidades mínimas dentro del archivo sin romper si cambia upstream.
        injection = '''
# AUTO_FIX_CHROOT_NATIVE_PMOS_BEGONIA
def _ensure_native_chroot_exists(args):
    import os
    work = getattr(args, "work", None)
    if not work:
        return
    chroot_native = os.path.join(work, "chroot_native")
    if not os.path.isdir(chroot_native):
        import pmb.build.init
        pmb.build.init.init(args)
'''
        text = injection + "\n" + text

        # Antes de crear/montar imagen, intenta asegurar chroot.
        text = text.replace(
            "def create_and_mount_image",
            "def create_and_mount_image"
        )

        # Inserción conservadora después de la primera línea def create_and_mount_image(...):
        lines = text.splitlines()
        out = []
        inserted = False
        inside_target_def = False

        for line in lines:
            out.append(line)
            if line.startswith("def create_and_mount_image"):
                inside_target_def = True
                continue
            if inside_target_def and not inserted and line.strip().startswith('"""'):
                # No insertar dentro del docstring todavía
                continue
            if inside_target_def and not inserted and line.startswith(" ") and not line.strip().startswith('"""'):
                out.append("    _ensure_native_chroot_exists(args)")
                inserted = True
                inside_target_def = False

        return "\n".join(out) + "\n"

    patch_file(blockdevice_py, patch_blockdevice, "defensive chroot_native re-init")

print("=== grep losetup after patch ===")
for path in ROOT.rglob("*.py"):
    txt = path.read_text(errors="ignore")
    if "losetup" in txt or "/sbin/losetup" in txt or "/usr/sbin/losetup" in txt:
        print(path)
        for i, line in enumerate(txt.splitlines(), start=1):
            if "losetup" in line:
                print(f"  {i}: {line}")
