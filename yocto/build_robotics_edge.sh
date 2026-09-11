#!/bin/bash

MY_YOCTO="$PWD/robotics-edge"
BUILD_FOLDER="build"

echo "Yocto Project Setup"
cd ${MY_YOCTO}
echo $(pwd)
DISTRO=robotics-edge MACHINE=imx8mp-lpddr4-frdm source robotics-edge-setup.sh -b ${BUILD_FOLDER} -r jazzy

echo "Patch Yocto Project configuration"
if [ -f "conf/local.conf" ]; then
    cat << 'EOF' >> conf/local.conf

BB_NUMBER_THREADS = "8"
PARALLEL_MAKE = "-j 8"

FETCHCMD_wget = "/usr/bin/env wget -t 2 -T 30 --passive-ftp --user-agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'"

PREMIRRORS:prepend = "\
https://gitlab.freedesktop.org/.*/.*/-/releases/.*/downloads/.* https://downloads.yoctoproject.org/mirror/sources/ \n \
"
EOF
    echo "Configuration ajoutée à conf/local.conf avec succès."
else
    echo "Erreur : le fichier conf/local.conf est introuvable."
    exit 1
fi

echo "Patch pseudo-native package"
mkdir -p ../sources/meta-robotics-edge/recipes-devtools/pseudo
cat << 'EOF' > "../sources/meta-robotics-edge/recipes-devtools/pseudo/pseudo_git.bbappend"
# Upgrade pseudo to a version supporting openat2 and newer *at() syscalls.
# Required for modern host systems such as Ubuntu 24.04 / GNU tar 1.35.

SRCREV = "6c0d8c6b81ca7c2ef2b5a9a996605e1a51814442"
PV = "1.9.4"

# These patches were already integrated upstream before pseudo 1.9.4.
SRC_URI:remove = "file://0001-configure-Prune-PIE-flags.patch"
SRC_URI:remove = "file://glibc238.patch"
SRC_URI:remove = "file://older-glibc-symbols.patch"
EOF

echo "Patch jazzy branch "
cd ../sources/meta-robotics-edge/recipes-support/moveit-task-constructor
sed -i 's/SRCBRANCH = "jazzy"/SRCBRANCH = "ros2"/' \
  moveit-task-constructor-capabilities_0.1.4.bb \
  moveit-task-constructor-core_0.1.4.bb \
  moveit-task-constructor-demo_0.1.4.bb \
  moveit-task-constructor-msgs_0.1.4.bb \
  rviz-marker-tools_0.1.4.bb
cd ${MY_YOCTO}

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