#!/bin/sh

echo "Setup repo"
mkdir -p ~/bin

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