#!/bin/sh

BASE_VERSION="LF_v6.18.2_1.0.0"
MY_YOCTO="${PWD}/${BASE_VERSION}"

if [ ! -d "$MY_YOCTO" ]; then
    echo "create $MY_YOCTO"
    mkdir -p $MY_YOCTO
fi

echo "Init repo for image version $BASE_VERSION"
cd ${MY_YOCTO}

repo init \
    -u https://github.com/nxp-imx/imx-manifest \
    -b imx-linux-whinlatter \
    -m imx-6.18.2-1.0.0.xml

repo sync

#echo "Integrate FRDM-IMX8MPLUS layer into Yocto code base"
#cd ${MY_YOCTO}/sources
#git clone https://github.com/nxp-imx-support/meta-imx-frdm.git#

echo "Done"
