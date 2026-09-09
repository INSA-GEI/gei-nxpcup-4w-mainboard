#!/bin/sh

MY_YOCTO="$PWD/yocto_i_mx_5_0"

if [ ! -d "$MY_YOCTO" ]; then
    echo "create $MY_YOCTO"
    mkdir -p $MY_YOCTO
fi

echo "init repo I.MX SW 2024 Q3 BSP"
cd ${MY_YOCTO}
repo init -u https://github.com/nxp-imx/imx-manifest -b imx-linux-scarthgap -m imx-6.6.36-2.1.0.xml
repo sync

echo "Integrate FRDM-IMX8MPLUS layer into Yocto code base"
cd ${MY_YOCTO}/sources
git clone https://github.com/nxp-imx-support/meta-imx-frdm.git
