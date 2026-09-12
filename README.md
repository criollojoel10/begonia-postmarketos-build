# begonia-postmarketos-build

Compila postmarketOS edge para Xiaomi Redmi Note 8 Pro (xiaomi-begonia) en GitHub Actions. Sin infraestructura local: el build corre en el runner, los artefactos se bajan como GitHub Artifacts.

## Flujos

| workflow | kernel | drivers dongle |
|---|---|---|
| `console_vanilla.yaml` | stock pmaports (6.16.x) | no |
| `final.yaml` | snapshot GCC junio (`kernel-hist-state/`) | si (USB-ethernet / WiFi Realtek-MT76 / serial USB) |

`final.yaml` añade `CONFIG_USB_NET_*`, `CONFIG_RTL8XXXU`, `CONFIG_MT76*`, `CONFIG_USB_SERIAL_*` a la config del kernel y fuerza rebuild (`pmbootstrap build linux-postmarketos-mediatek-mt6785 --force`).

## Uso

1. Página del repo → **Actions** → workflow deseado → **Run workflow**.
2. Parámetros: `ui` (console/phosh/weston/plasma-mobile), `cross` (true), `pmaports_branch` (main).
3. Al terminar, descargar el artefacto `pmos-begonia-<ui>-cross-<cross>`: contiene `boot.img`, `initramfs`, `vmlinuz`, `xiaomi-begonia.img`.

## Flasheo (fastboot)

El begonia se flashea por fastboot. Su LK (Little Kernel) verifica particiones; sin vbmeta correcto el dispositivo vuelve a fastboot en vez de bootear.

```
fastboot flash userdata xiaomi-begonia.img   # rootfs (subparticiones pmOS_boot/pmOS_root)
fastboot flash boot boot.img
fastboot flash vbmeta vbmeta.img             # verificación de boot desactivada (flags=2)
fastboot reboot
```

### vbmeta

`vbmeta.img` es una imagen AVB con `--flags 2` (verification disabled). Se genera con `avbtool` (paquete Alpine `android-tools-avbtool`):

```
avbtool make_vbmeta_image --flags 2 --padding_size 2048 --output /vbmeta.img
```

El vbmeta generado manualmente antes tenía `flags=0` (verificación activada) y LK rechazaba el boot → bootloop a fastboot. Con `flags=2` el dispositivo bootea.

## Comprobación

USB networking (RNDIS) levanta `172.16.42.1` en el dispositivo. Este host queda en `172.16.42.2/24`:

```
ssh joel@172.16.42.1
```

- kernel: `uname -r` → `6.16.4-postmarketos-mediatek-mt6785`
- rootfs montada: `lsblk` muestra `loop0p1 /boot` y `loop0p2 /`
- drivers dongle: `lsmod | grep -E 'ax88179|rtl8152|mt76|pl2303|ftdi_sio|cp210x'`

## Estado del hardware (wiki pmOS)

USB networking, storage, SD, pantalla, touch, NFC y FDE funcionan. WiFi/BT/GPS/modem/audio/cámara del SoC no funcionan con mainline; la idea de los drivers dongle es dar red vía adaptadores USB (hub USB-C).