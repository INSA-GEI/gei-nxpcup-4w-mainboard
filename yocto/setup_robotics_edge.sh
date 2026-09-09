#!/bin/sh

MY_YOCTO="$PWD/robotics-edge"

if [ ! -d "$MY_YOCTO" ]; then
    echo "create $MY_YOCTO"
    mkdir -p $MY_YOCTO
fi

echo "init repo robotics-edge"
cd ${MY_YOCTO}
repo init \
    -u https://github.com/nxp-imx/imx-manifest.git \
    -b robotics-edge-walnascar \
    -m robotics-edge-1.0.0.xml
repo sync

#echo "Integrate FRDM-IMX8MPLUS layer into Yocto code base"
#cd ${MY_YOCTO}/sources
#git clone https://github.com/nxp-imx-support/meta-imx-frdm.git#

