IMAGE_INSTALL:remove = "packagegroup-security-tpm2 \
    packagegroup-security-parsec \
    swtpm \
    softhsm "

IMAGE_INSTALL:remove = "docker"

inherit ros_distro_${ROS_DISTRO}
inherit ${ROS_DISTRO_TYPE}_image

IMAGE_INSTALL:append = " \
    packagegroup-robotics-arm-demo \
    packagegroup-ros-base \
    packagegroup-ros-base-demo \
    packagegroup-ros-dev \
    packagegroup-ros-gstreamer \
    packagegroup-robotics-vslam-demo \
"

IMAGE_INSTALL:append = " git"

IMAGE_INSTALL:append = " dtc dtc-dev"

