#!/usr/bin/env bash
# Build an independent UEFI diagnostic disk using the matching ULTRA-LinuX kernel.
set -euo pipefail
if [[ $# != 4 && ${5-} != --shared-esp ]] || [[ $# -gt 5 ]]; then
    echo "Usage: $0 bzImage mounted-ultra-root instrumented-nvidia.ko new-image-directory [--shared-esp]" >&2
    exit 2
fi
kernel=$(realpath "$1")
reference=$(realpath "$2")
module=$(realpath "$3")
output=$(realpath -m "$4")
release=7.3.0-rc7-pc-g32c52ec87d62
version=615.78.08
drivers="$reference/usr/lib/modules/$release/kernel/drivers/video"
[[ -r $kernel && -r $module && -d $drivers && ! -e $output ]]
[[ $(modinfo -F version "$module") == "$version" ]]
for file in "$module" "$drivers"/nvidia{,-modeset,-drm}.ko; do
    [[ $(modinfo -F vermagic "$file") == "$release "* ]]
    [[ $(modinfo -F version "$file") == "$version" ]]
done
grep -aq BMO_GSP_INIT_OK_END "$module"
file -b /usr/bin/busybox | grep -q 'statically linked'
mkdir "$output"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
root="$work/root"
mkdir -p "$root"/{dev,proc,sys,capture,sistema/usr/lib/firmware}
install -Dm755 /usr/bin/busybox "$root/bin/busybox"
for app in sh mount umount sleep grep cat dmesg insmod sync mv poweroff; do
    ln -s busybox "$root/bin/$app"
done
install -m644 "$module" "$root/nvidia.ko"
install -m644 "$drivers"/nvidia{-modeset,-drm}.ko "$root/"
# Only the firmware of this board family is needed by this initramfs.
for firmware in gsp_ga10x.bin ucodes_ga10x.bin; do
    path="sistema/usr/lib/firmware/nvidia/$version/$firmware"
    install -Dm644 "$reference/${path#sistema/}" "$root/$path"
done
ln -s /sistema/usr/lib "$root/lib"
capture_dir=
partition_name=BMO-GSP-CAPTURE
volume_id='BMO-X2 OpenRM 615 capture volume v1'
label=GSPDIAG
if [[ ${5-} == --shared-esp ]]; then
    capture_dir=/BMO-X2/GSP-DIAG
    partition_name=
    volume_id=$(cat /proc/sys/kernel/random/uuid)
    label=BMO
fi
printf "capture_dir='%s'\npartition_name='%s'\nvolume_id='%s'\n" \
    "$capture_dir" "$partition_name" "$volume_id" > "$root/gsp-volume"
cat > "$root/init" <<'INIT'
#!/bin/sh
export PATH=/bin
set -eu
mount -t devtmpfs devtmpfs /dev
mount -t proc proc /proc
mount -t sysfs sysfs /sys
. /gsp-volume
destination=/capture$capture_dir
show() {
    echo "$*"
    if [ -c /dev/tty0 ]; then echo "$*" >/dev/tty0 || :; fi
}
show "ULTRA-LinuX / Diagnostico GSP de BMO-X2"
volume=
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    for uevent in /sys/class/block/*/uevent; do
        grep -qx 'DEVTYPE=partition' "$uevent" || continue
        if [ -n "$partition_name" ]; then
            grep -Fxq "PARTNAME=$partition_name" "$uevent" || continue
        fi
        name=${uevent%/uevent}
        device=/dev/${name##*/}
        mount -o ro,nodev,nosuid,noexec -t vfat "$device" /capture || continue
        if grep -Fxq "$volume_id" "$destination/GSPDIAG.ID"; then
            volume=$device
            umount /capture
            break 2
        fi
        umount /capture
    done
    sleep 1
done
result=GSP_NO_GPU
pci=/sys/bus/pci/devices/0000:29:00.0
if [ -r "$pci/vendor" ] && [ "$(cat "$pci/vendor")" = 0x10de ] &&
   [ "$(cat "$pci/device")" = 0x2504 ] &&
   [ "$(cat "$pci/subsystem_vendor")" = 0x1462 ] &&
   [ "$(cat "$pci/subsystem_device")" = 0x397d ]; then
    result=GSP_MODULE_LOAD_FAILED
    if insmod /nvidia.ko && insmod /nvidia-modeset.ko &&
       insmod /nvidia-drm.ko modeset=1 fbdev=0; then
        result=GSP_INIT_NOT_CAPTURED
        for attempt in 1 2 3 4 5; do
            if dmesg | grep -q BMO_GSP_INIT_OK_END=; then
                result=GSP_INIT_CAPTURED
                break
            fi
            sleep 1
        done
    fi
fi
if [ -n "$volume" ] && mount -o nodev,nosuid,noexec -t vfat "$volume" /capture; then
    if grep -Fxq "$volume_id" "$destination/GSPDIAG.ID" &&
       { printf 'BMO_GSP_CAPTURE_STATUS=%s\n' "$result"; dmesg; } > "$destination/GSPINIT.TMP" &&
       mv "$destination/GSPINIT.TMP" "$destination/GSPINIT.TXT" && sync && umount /capture; then
        show "$result / registro guardado en GSPINIT.TXT"
    else
        show "$result / no se pudo guardar el registro"
    fi
else
    show "$result / medio de captura no encontrado"
fi
show "Puedes apagar y volver a Windows."
while :; do sleep 60; done
INIT
chmod 0755 "$root/init"
mkdir -p "$work/esp/EFI/BOOT"
printf 'search --no-floppy --file --set=root %s/GSPDIAG.ID\nlinux %s/VMLINUX\ninitrd %s/GSPINIT.GZ\nboot\n' \
    "$capture_dir" "$capture_dir" "$capture_dir" > "$work/grub.cfg"
grub-mkstandalone -O x86_64-efi --modules='part_gpt fat search search_fs_file linux' \
    -o "$work/esp/EFI/BOOT/BOOTX64.EFI" "boot/grub/grub.cfg=$work/grub.cfg"
payload="$work/esp$capture_dir"
mkdir -p "$payload"
install -m644 "$kernel" "$payload/VMLINUX"
(cd "$root"; find . -print0 | cpio --null -o -H newc --owner=0:0 --quiet | gzip -1) > "$payload/GSPINIT.GZ"
printf '%s\n' "$volume_id" > "$payload/GSPDIAG.ID"
image="$output/BMO-GSP-DIAG.img"
truncate -s 256M "$image"
printf 'label: gpt\nstart=2048,size=520192,type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B,name="BMO-GSP-CAPTURE"\n' |
    sfdisk --quiet "$image"
mkfs.fat -F 32 --offset=2048 -n "$label" "$image" 260096 >/dev/null
mcopy -s -i "$image@@1048576" "$work/esp/"* ::/
(cd "$output"; sha256sum BMO-GSP-DIAG.img > SHA256SUMS)
