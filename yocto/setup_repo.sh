#!/bin/bash

echo "Setup repo"
mkdir -p ~/bin

read -r -p "Do you want to install essential packages [y/N] " response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Install required packages"
    sudo apt install build-essential chrpath cpio debianutils diffstat file gawk gcc git iputils-ping libacl1 liblz4-tool locales python3 python3-git python3-jinja2 python3-pexpect python3-pip python3-subunit socat texinfo unzip wget xz-utils zstd
fi

if [ ! -f "$HOME/bin/repo" ]; then
    curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
    chmod a+x ~/bin/repo
fi

# 1. Vérifier et ajouter la ligne dans ~/.bashrc si elle est absente
if ! grep -q '\$HOME/bin' "$HOME/.bashrc" && ! grep -q '~/bin' "$HOME/.bashrc"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    echo "ajout de $HOME/bin dans .bashrc" 
fi

# 2. Exporter dans la session en cours si ce n'est pas déjà dans le PATH
case ":$PATH:" in
    *:"$HOME/bin":*) ;;
    *) export PATH="$HOME/bin:$PATH" ;;
esac