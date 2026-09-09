#!/bin/bash

MY_YOCTO="$PWD/robotics-edge"
BUILD_FOLDER="build"

echo "Yocto Project Setup"
cd ${MY_YOCTO}
echo $(pwd)
DISTRO=robotics-edge MACHINE=imx8mp-lpddr4-frdm source robotics-edge-setup.sh -b ${BUILD_FOLDER} -r jazzy

echo "Build images"
source ./setup-environment ${BUILD_FOLDER} 
bitbake robotics-edge-image-full

read -r -p "Do you want to generate SD card image [y/N] " response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Generate SD card image"
    zstdcat robotics-edge-image-full-imx8mpfrdm.rootfs.wic.zst

    read -r -p "Do you want to flash SD card [y/N] " response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Flashing SD card image"
        sudo dd of=/dev/sdx bs=1M && sync
    fi
fi

read -r -p "Do you want to burn image (uuu) [y/N] " response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Burn image into SD card"
    uuu -b sd_all robotics-edge-image-full-imx8mpfrdm.rootfs.wic.zst
fi