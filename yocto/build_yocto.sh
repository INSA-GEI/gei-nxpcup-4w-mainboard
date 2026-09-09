#!/bin/bash

MY_YOCTO="$PWD/yocto_i_mx_5_0"

echo "Yocto Project Setup"
cd ${MY_YOCTO}
echo $(pwd)
MACHINE=imx8mpfrdm DISTRO=fsl-imx-xwayland source sources/meta-imx-frdm/tools/imx-frdm-setup.sh -b frdm-imx8mp

echo "Build images"
bitbake imx-image-full

read -r -p "Do you want to generate SD card image [y/N] " response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Generate SD card image"
    zstdcat imx-image-full-imx8mpfrdm.rootfs.wic.zst

    read -r -p "Do you want to flash SD card [y/N] " response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Flashing SD card image"
        sudo dd of=/dev/sdx bs=1M && sync
    fi
fi

read -r -p "Do you want to burn image (uuu) [y/N] " response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Burn image into SD card"
    uuu -b sd_all imx-image-full-imx8mpfrdm.rootfs.wic.zst
fi