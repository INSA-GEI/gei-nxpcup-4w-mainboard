#!/bin/bash

SCRIPT_PATH="$(dirname "$0")"
BASE_VERSION="LF_v6.18.2_1.0.0"
MY_YOCTO="${PWD}/${BASE_VERSION}"
BUILD_FOLDER="build"

echo "Yocto Project Setup ( ${BASE_VERSION} )"
cd ${MY_YOCTO}
echo $(pwd)
MACHINE=imx8mp-lpddr4-frdm DISTRO=fsl-imx-xwayland source ./imx-setup-release.sh -b ${BUILD_FOLDER}

echo "Patch Yocto Project configuration"
cp ${SCRIPT_PATH}/local.conf ${MY_YOCTO}/${BUILD_FOLDER}/conf/local.conf

echo "Patch pseudo-native package"
mkdir -p ../sources/meta-imx/meta-imx-bsp/recipes-devtools/pseudo
cat << 'EOF' > "../sources/meta-imx/meta-imx-bsp/recipes-devtools/pseudo/pseudo_git.bbappend"
# Upgrade pseudo to a version supporting openat2 and newer *at() syscalls.
# Required for modern host systems such as Ubuntu 24.04 / GNU tar 1.35.

SRCREV = "6c0d8c6b81ca7c2ef2b5a9a996605e1a51814442"
PV = "1.9.4"

# These patches were already integrated upstream before pseudo 1.9.4.
SRC_URI:remove = "file://0001-configure-Prune-PIE-flags.patch"
SRC_URI:remove = "file://glibc238.patch"
SRC_URI:remove = "file://older-glibc-symbols.patch"
EOF

cd ${MY_YOCTO}

echo "Build images"
source ./setup-environment ${BUILD_FOLDER} 
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
    uuu -b sd_all imximage-full-imx8mpfrdm.rootfs.wic.zst
fi